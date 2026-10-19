"""Paired-end reads from a reference with a known set of variants.

Variants are placed by a seeded generator away from contig ends, N runs and each
other, applied to haplotype sequences, and reads are drawn from the haplotypes with a
uniform substitution error. Positions in truth VCFs are 1-based reference coordinates.
"""

from __future__ import annotations

import gzip
import json
import random
from dataclasses import dataclass
from pathlib import Path

BASES = "ACGT"
COMPLEMENT = str.maketrans("ACGTN", "TGCAN")


@dataclass(frozen=True)
class Variant:
    contig: str
    pos: int  # 1-based, reference coordinates
    ref: str
    alt: str
    kind: str  # "snv" or "indel"
    origin: str  # "somatic", "germline", "het" or "hom"


def read_fasta(path: str | Path) -> dict[str, str]:
    seqs: dict[str, list[str]] = {}
    name = None
    with Path(path).open(encoding="ascii") as handle:
        for line in handle:
            if line.startswith(">"):
                name = line[1:].split()[0]
                seqs[name] = []
            elif name is not None:
                seqs[name].append(line.strip().upper())
    return {k: "".join(v) for k, v in seqs.items()}


def pick_variants(
    ref: dict[str, str],
    rng: random.Random,
    snvs: dict[str, int],
    indels: dict[str, int],
    germline_per_kb: float,
    margin: int = 500,
    spacing: int = 400,
) -> list[Variant]:
    variants: list[Variant] = []
    for contig, seq in ref.items():
        taken: list[int] = []

        def free(pos: int, seq: str = seq, taken: list[int] = taken) -> bool:
            window = seq[pos - 6 : pos + 6]
            return (
                margin <= pos < len(seq) - margin
                and "N" not in window
                and all(abs(pos - t) >= spacing for t in taken)
            )

        def draw(seq: str = seq, free=free) -> int:
            for _ in range(10_000):
                pos = rng.randrange(margin, len(seq) - margin)
                if free(pos):
                    return pos
            raise RuntimeError("could not place a variant; lower the counts or spacing")

        n_germ = int(len(seq) / 1000 * germline_per_kb)
        plan = (
            [("placed", "snv")] * snvs.get(contig, 0)
            + [("placed", "indel")] * indels.get(contig, 0)
            + [("germline", "snv")] * n_germ
        )
        for origin, kind in plan:
            i = draw()
            taken.append(i)
            ref_base = seq[i]
            if kind == "snv":
                alt = rng.choice([b for b in BASES if b != ref_base])
                variants.append(Variant(contig, i + 1, ref_base, alt, kind, origin))
            elif rng.random() < 0.5:  # deletion of 1 to 3 bases after the anchor base
                length = rng.randint(1, 3)
                variants.append(
                    Variant(contig, i + 1, seq[i : i + 1 + length], ref_base, kind, origin)
                )
            else:  # insertion of 1 to 3 bases after the anchor base
                ins = "".join(rng.choice(BASES) for _ in range(rng.randint(1, 3)))
                variants.append(Variant(contig, i + 1, ref_base, ref_base + ins, kind, origin))
    return sorted(variants, key=lambda v: (v.contig, v.pos))


def apply(seq: str, contig: str, variants: list[Variant]) -> str:
    out = seq
    for v in sorted((v for v in variants if v.contig == contig), key=lambda v: -v.pos):
        i = v.pos - 1
        assert out[i : i + len(v.ref)] == v.ref, (v, out[i : i + len(v.ref)])
        out = out[:i] + v.alt + out[i + len(v.ref) :]
    return out


def _mutate_read(read: str, rng: random.Random, error_rate: float) -> str:
    chars = list(read)
    for k, base in enumerate(chars):
        if base != "N" and rng.random() < error_rate:
            chars[k] = rng.choice([b for b in BASES if b != base])
    return "".join(chars)


def write_pairs(
    haplotypes: list[tuple[str, float]],
    n_pairs: int,
    out_prefix: Path,
    rng: random.Random,
    read_length: int = 150,
    insert_mean: int = 350,
    insert_sd: int = 30,
    error_rate: float = 0.001,
) -> tuple[Path, Path]:
    weights = [w for _, w in haplotypes]
    r1_path = out_prefix.with_name(out_prefix.name + "_R1.fastq.gz")
    r2_path = out_prefix.with_name(out_prefix.name + "_R2.fastq.gz")
    qual = "I" * read_length
    with (
        gzip.open(r1_path, "wt", compresslevel=3) as r1,
        gzip.open(r2_path, "wt", compresslevel=3) as r2,
    ):
        for n in range(n_pairs):
            seq = rng.choices([h for h, _ in haplotypes], weights=weights)[0]
            insert = max(read_length + 10, int(rng.gauss(insert_mean, insert_sd)))
            start = rng.randrange(0, len(seq) - insert)
            fragment = seq[start : start + insert]
            if "N" in fragment:
                continue
            if rng.random() < 0.5:
                fragment = fragment.translate(COMPLEMENT)[::-1]
            a = _mutate_read(fragment[:read_length], rng, error_rate)
            b = _mutate_read(fragment[-read_length:].translate(COMPLEMENT)[::-1], rng, error_rate)
            name = f"{out_prefix.name}:{n}"
            r1.write(f"@{name}/1\n{a}\n+\n{qual}\n")
            r2.write(f"@{name}/2\n{b}\n+\n{qual}\n")
    return r1_path, r2_path


def write_vcf(path: Path, variants: list[Variant], ref: dict[str, str]) -> None:
    with path.open("w", encoding="ascii") as out:
        out.write("##fileformat=VCFv4.2\n")
        out.write('##INFO=<ID=TYPE,Number=1,Type=String,Description="SNV or INDEL">\n')
        out.write(
            "##INFO=<ID=ZYG,Number=1,Type=String,"
            'Description="het or hom, for simulated germline variants">\n'
        )
        for contig, seq in ref.items():
            out.write(f"##contig=<ID={contig},length={len(seq)}>\n")
        out.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
        for v in variants:
            zyg = f";ZYG={v.origin}" if v.origin in ("het", "hom") else ""
            out.write(
                f"{v.contig}\t{v.pos}\t.\t{v.ref}\t{v.alt}\t.\tPASS\tTYPE={v.kind.upper()}{zyg}\n"
            )


def simulate_germline(
    fasta: str | Path,
    out_dir: str | Path,
    snvs_per_contig: int = 20,
    hom_fraction: float = 0.3,
    depth: float = 30.0,
    seed: int = 20261019,
    sample: str = "sample",
    read_length: int = 100,
) -> dict[str, object]:
    """One diploid sample with known SNVs: heterozygous on haplotype A only, homozygous on both."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    ref = read_fasta(fasta)
    placed = pick_variants(ref, rng, {c: snvs_per_contig for c in ref}, {}, germline_per_kb=0.0)
    hom = {v for v in placed if rng.random() < hom_fraction}
    hap_a = {c: apply(s, c, placed) for c, s in ref.items()}
    hap_b = {c: apply(s, c, [v for v in placed if v in hom]) for c, s in ref.items()}
    total = sum(len(s) for s in ref.values())
    files = []
    for contig, seq in ref.items():
        n_pairs = int(depth * len(seq) / (2 * read_length))
        r1, r2 = write_pairs(
            [(hap_a[contig], 0.5), (hap_b[contig], 0.5)],
            n_pairs,
            out / f"{sample}_{contig}",
            rng,
            read_length,
        )
        files.append([r1.name, r2.name])
    truth = [
        Variant(v.contig, v.pos, v.ref, v.alt, v.kind, "hom" if v in hom else "het") for v in placed
    ]
    write_vcf(out / "truth.vcf", truth, ref)
    summary = {
        "seed": seed,
        "reference_bases": total,
        "snvs": len(truth),
        "homozygous": len(hom),
        "depth": depth,
        "fastq": files,
    }
    (out / "truth.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary
