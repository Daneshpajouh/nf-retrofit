"""Run manifest written before a pipeline run, and a summary written after it.

The manifest pins what went in (input files with SHA-256, parameters, the pipeline
commit, the container, the start time). The summary reads Nextflow's trace file and
records what came out (status, duration, failed and retried tasks, per-process
resources, output files with SHA-256).
"""

from __future__ import annotations

import csv
import glob
import hashlib
import json
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_commit(repo: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip()


def tool_version(cmd: list[str]) -> str | None:
    try:
        out = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    text = (out.stdout or out.stderr).strip().splitlines()
    return " ".join(line.strip() for line in text if line.strip())[:200] or None


def expand(patterns: list[str]) -> list[Path]:
    """Expand Nextflow-style inputs (globs and one level of {a,b} braces) to existing files."""
    files: list[Path] = []
    for pattern in patterns:
        head, brace, tail = pattern.partition("{")
        options, _, rest = tail.partition("}") if brace else ("", "", "")
        variants = [head + opt + rest for opt in options.split(",")] if brace else [pattern]
        for variant in variants:
            files += [Path(m) for m in sorted(glob.glob(variant)) if Path(m).is_file()]
    return files


def write_manifest(
    out: Path, inputs: list[Path], params: dict[str, str], pipeline_dir: Path, container: str | None
) -> dict[str, object]:
    manifest = {
        "started_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "host": {"system": platform.system(), "machine": platform.machine()},
        "nextflow": tool_version(["nextflow", "-version"]),
        "pipeline_dir": str(pipeline_dir),
        "pipeline_commit": git_commit(pipeline_dir),
        "container": container,
        "params": params,
        "inputs": [
            {"path": str(p), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in inputs
        ],
    }
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _duration_ms(text: str) -> float | None:
    """Parse Nextflow's human durations such as '1.2s', '350ms', '1m 4s'."""
    if text in ("", "-"):
        return None
    total = 0.0
    for part in text.split():
        for unit, factor in (
            ("ms", 1),
            ("s", 1000),
            ("m", 60_000),
            ("h", 3_600_000),
            ("d", 86_400_000),
        ):
            if part.endswith(unit) and part[: -len(unit)].replace(".", "", 1).isdigit():
                total += float(part[: -len(unit)]) * factor
                break
        else:
            return None
    return total


def summarise(
    trace: Path, out_dir: Path, exit_code: int, manifest: Path, out: Path
) -> dict[str, object]:
    """Judge each task by its last attempt.

    Nextflow writes one trace row per attempt, under the same name and a new task_id, so a
    task killed for memory and then retried has a FAILED row before its COMPLETED one.
    With the trace's `attempt` column, a first attempt always starts a new task, so two
    tasks that share a tag stay apart; without it, rows that share a name are one task.
    Realtime and peak memory still count every attempt, since a killed attempt used them.
    A missing trace fails the run: nothing shows that any task ran.
    """
    rows = (
        list(csv.DictReader(trace.open(encoding="utf-8"), delimiter="\t")) if trace.exists() else []
    )
    tasks: list[tuple[str, list[dict[str, str]]]] = []
    latest: dict[str, list[dict[str, str]]] = {}
    for r in sorted(rows, key=lambda r: int(r.get("task_id") or 0)):
        name = r.get("name", "")
        if name not in latest or r.get("attempt") == "1":
            latest[name] = []
            tasks.append((name, latest[name]))
        latest[name].append(r)
    failed = [a[-1] for _, a in tasks if a[-1].get("status") not in ("COMPLETED", "CACHED")]
    retried = [
        {"name": name, "attempts": len(a), "exits": [r.get("exit") for r in a]}
        for name, a in tasks
        if len(a) > 1
    ]
    processes: dict[str, dict[str, object]] = {}
    for task_name, task_attempts in tasks:
        name = task_name.split(" (")[0]
        entry = processes.setdefault(
            name, {"tasks": 0, "realtime_ms": 0.0, "peak_rss": [], "statuses": set()}
        )
        entry["tasks"] += 1
        entry["statuses"].add(task_attempts[-1].get("status", ""))
        for r in task_attempts:
            entry["realtime_ms"] += _duration_ms(r.get("realtime", "")) or 0.0
            if r.get("peak_rss") not in (None, "", "-"):
                entry["peak_rss"].append(r["peak_rss"])
    resource_table = [
        {
            "process": name,
            "tasks": e["tasks"],
            "realtime_s": round(e["realtime_ms"] / 1000, 3),
            "peak_rss": e["peak_rss"],
            "statuses": sorted(e["statuses"]),
        }
        for name, e in sorted(processes.items())
    ]
    started = json.loads(manifest.read_text(encoding="utf-8"))["started_utc"]
    finished = datetime.now(UTC)
    outputs = sorted(p for p in out_dir.rglob("*") if p.is_file()) if out_dir.exists() else []
    summary = {
        "status": "OK" if exit_code == 0 and not failed and trace.exists() else "FAILED",
        "exit_code": exit_code,
        "trace_found": trace.exists(),
        "started_utc": started,
        "finished_utc": finished.isoformat(timespec="seconds"),
        "duration_s": round((finished - datetime.fromisoformat(started)).total_seconds(), 1),
        "tasks": len(tasks),
        "failed_tasks": [
            {"name": r.get("name"), "status": r.get("status"), "exit": r.get("exit")}
            for r in failed
        ],
        "retried_tasks": retried,
        "resources": resource_table,
        "outputs": [
            {"path": str(p.relative_to(out_dir)), "bytes": p.stat().st_size, "sha256": sha256(p)}
            for p in outputs
        ],
    }
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary
