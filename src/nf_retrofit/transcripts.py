"""Known-answer data for transcript quantification.

Transcripts are random sequences, and the simulator redraws any set in which two share
a 31-mer on either strand, so each fragment has one true origin and the expected read
count per transcript is the number of fragments drawn from it. With equal lengths,
expected TPM is 10^6 times each transcript's share of fragments.
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

from .simulate import COMPLEMENT, write_pairs

K = 31  # Salmon's default k-mer length


def simulate_transcripts(
    out_dir: str | Path,
    counts: dict[str, int],
    length: int = 1500,
    seed: int = 7,
    sample: str = "synthetic",
) -> dict[str, object]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    while True:
        seqs = {name: "".join(rng.choice("ACGT") for _ in range(length)) for name in counts}
        if not _share_a_kmer(list(seqs.values())):
            break
    with (out / "transcriptome.fa").open("w", encoding="ascii") as fasta:
        for name, seq in seqs.items():
            fasta.write(f">{name}\n")
            for i in range(0, len(seq), 60):
                fasta.write(seq[i : i + 60] + "\n")
    # one FASTQ pair per sample, fragments from each transcript in the stated numbers
    prefix = out / sample
    r1 = prefix.with_name(f"{sample}_1.fq.gz")
    r2 = prefix.with_name(f"{sample}_2.fq.gz")
    parts = []
    for name, n in counts.items():
        part = out / f".part_{name}"
        write_pairs([(seqs[name], 1.0)], n, part, rng, read_length=75, insert_mean=250, insert_sd=20)
        parts.append(part)
    _concat([p.with_name(p.name + "_R1.fastq.gz") for p in parts], r1)
    _concat([p.with_name(p.name + "_R2.fastq.gz") for p in parts], r2)
    total = sum(counts.values())
    expected = {
        name: {"num_reads": n, "tpm": round(1e6 * n / total, 1), "length": length} for name, n in counts.items()
    }
    (out / "expected.json").write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    return expected


def _share_a_kmer(seqs: list[str]) -> bool:
    owner: dict[str, int] = {}
    for n, seq in enumerate(seqs):
        for strand in (seq, seq.translate(COMPLEMENT)[::-1]):
            for i in range(len(strand) - K + 1):
                if owner.setdefault(strand[i : i + K], n) != n:
                    return True
    return False


def _concat(parts: list[Path], target: Path) -> None:
    with target.open("wb") as out:
        for part in parts:
            out.write(part.read_bytes())
            part.unlink()


def compare_quant(quant_sf: str | Path, expected: dict[str, dict[str, float]], tolerance: float = 0.02) -> list[str]:
    """Return one line per transcript whose NumReads is off by more than `tolerance` (relative)."""
    rows = {r["Name"]: r for r in csv.DictReader(Path(quant_sf).open(encoding="utf-8"), delimiter="\t")}
    problems = []
    for name, exp in expected.items():
        if name not in rows:
            problems.append(f"{name}: missing from quant.sf")
            continue
        got = float(rows[name]["NumReads"])
        want = exp["num_reads"]
        if abs(got - want) > tolerance * want:
            problems.append(f"{name}: NumReads {got:.1f}, expected {want}")
    return problems
