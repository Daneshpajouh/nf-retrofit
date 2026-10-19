"""Command line: known-answer data, checks against it, lint summaries and run logs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .lint import lint_file_to_markdown
from .runlog import expand, summarise, write_manifest
from .simulate import simulate_germline
from .transcripts import compare_quant, simulate_transcripts
from .vcfcheck import compare_vcf


def _named_counts(arg: str) -> dict[str, int]:
    return {k: int(v) for k, v in (item.split("=") for item in arg.split(",") if item)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nf-legacy-testkit")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("transcripts", help="synthetic transcriptome and reads with known counts")
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--counts", required=True, type=_named_counts, help="e.g. tx_a=400,tx_b=800")
    p.add_argument("--seed", type=int, default=7)

    p = sub.add_parser("check-quant", help="compare a Salmon quant.sf with expected.json")
    p.add_argument("quant_sf", type=Path)
    p.add_argument("expected", type=Path)
    p.add_argument("--tolerance", type=float, default=0.02)

    p = sub.add_parser("germline", help="reads from a reference with known het and hom SNVs")
    p.add_argument("--reference", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--snvs-per-contig", type=int, default=20)
    p.add_argument("--depth", type=float, default=30.0)
    p.add_argument("--seed", type=int, default=20261019)

    p = sub.add_parser("check-vcf", help="compare called SNVs with a truth VCF")
    p.add_argument("calls", type=Path)
    p.add_argument("truth", type=Path)

    p = sub.add_parser("lint-report", help="markdown summary of `nextflow lint` output")
    p.add_argument("lint_output", type=Path)
    p.add_argument("--title", required=True)

    p = sub.add_parser("manifest", help="write a run manifest before a run")
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--pipeline-dir", required=True, type=Path)
    p.add_argument("--container", default=None)
    p.add_argument("--param", action="append", default=[], help="key=value, repeatable")
    p.add_argument("inputs", nargs="*", help="files, globs or {a,b} patterns")

    p = sub.add_parser("summarise", help="write a run summary after a run")
    p.add_argument("--trace", required=True, type=Path)
    p.add_argument("--outdir", required=True, type=Path)
    p.add_argument("--exit-code", required=True, type=int)
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)

    args = parser.parse_args(argv)

    if args.command == "transcripts":
        print(json.dumps(simulate_transcripts(args.out, args.counts, seed=args.seed), indent=2))
        return 0
    if args.command == "check-quant":
        problems = compare_quant(args.quant_sf, json.loads(args.expected.read_text()), args.tolerance)
        for line in problems:
            print(line, file=sys.stderr)
        print("PASS" if not problems else f"FAIL: {len(problems)} transcripts off")
        return 1 if problems else 0
    if args.command == "germline":
        print(json.dumps(simulate_germline(args.reference, args.out, args.snvs_per_contig, depth=args.depth, seed=args.seed)))
        return 0
    if args.command == "check-vcf":
        result = compare_vcf(args.calls, args.truth)
        print(json.dumps(result, indent=2))
        return 0 if not result["missed"] else 1
    if args.command == "lint-report":
        print(lint_file_to_markdown(args.lint_output, args.title), end="")
        return 0
    if args.command == "manifest":
        params = dict(item.split("=", 1) for item in args.param)
        write_manifest(args.out, expand(args.inputs), params, args.pipeline_dir, args.container)
        return 0
    summary = summarise(args.trace, args.outdir, args.exit_code, args.manifest, args.out)
    print(f"{summary['status']}: {summary['tasks']} tasks, {len(summary['failed_tasks'])} failed, "
          f"{summary['duration_s']} s")
    return 0 if summary["status"] == "OK" else 1
