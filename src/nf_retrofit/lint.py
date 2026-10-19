"""Summarise `nextflow lint` output: counts per message and every file:line it names."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

LINE = re.compile(r"^(Error|Warn)\s+(\S+?):(\d+):(\d+): (.+)$")


def parse_lint(text: str) -> list[dict[str, object]]:
    findings = []
    for raw in text.splitlines():
        match = LINE.match(raw)
        if match:
            level, path, line, col, message = match.groups()
            findings.append({"level": level, "file": path, "line": int(line), "col": int(col), "message": message})
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


def lint_file_to_markdown(path: str | Path, title: str) -> str:
    return to_markdown(parse_lint(Path(path).read_text(encoding="utf-8")), title)
