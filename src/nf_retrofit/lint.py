"""Summarise `nextflow lint` output: counts per message and every file:line it names."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

LINE = re.compile(r"^(Error|Warn)\s+(\S+?):(\d+):(\d+): (.+)$")


def parse_lint(text: str) -> list[dict[str, object]]:
    """Findings in `nextflow lint` output.

    Text with no findings and no completion line is refused: a Java crash or a missing
    `nextflow` leaves exactly that, and it must not read as a clean run.
    """
    findings = []
    for raw in text.splitlines():
        match = LINE.match(raw)
        if match:
            level, path, line, col, message = match.groups()
            findings.append(
                {
                    "level": level,
                    "file": path,
                    "line": int(line),
                    "col": int(col),
                    "message": message,
                }
            )
    if not findings and "Nextflow linting complete" not in text:
        raise ValueError(
            "no findings and no 'Nextflow linting complete' line: not a finished lint run"
        )
    return findings


def to_markdown(findings: list[dict[str, object]], title: str) -> str:
    errors = sum(f["level"] == "Error" for f in findings)
    warns = len(findings) - errors
    out = [f"# {title}", "", f"{errors} errors, {warns} warnings.", ""]
    if not findings:
        return "\n".join(out)
    by_message = Counter((f["level"], f["message"]) for f in findings)
    out += ["| Level | Count | Message |", "|---|---:|---|"]
    out += [f"| {lvl} | {n} | {msg} |" for (lvl, msg), n in by_message.most_common()]
    out += ["", "| Level | Location | Message |", "|---|---|---|"]
    out += [f"| {f['level']} | `{f['file']}:{f['line']}` | {f['message']} |" for f in findings]
    return "\n".join(out) + "\n"


def lint_file_to_markdown(path: str | Path, title: str, exit_code: int | None = None) -> str:
    findings = parse_lint(Path(path).read_text(encoding="utf-8"))
    errors = sum(f["level"] == "Error" for f in findings)
    # lint exits 1 if it reported errors and 0 if not; anything else means it did not finish
    if exit_code is not None and exit_code != (1 if errors else 0):
        raise ValueError(f"nextflow lint exited {exit_code} with {errors} errors in its output")
    return to_markdown(findings, title)
