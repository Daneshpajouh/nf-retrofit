"""Compare called variants with a truth VCF after trimming shared flanking bases.

Callers write the same variant with different padding (CCTC>CC and CCT>C are one
deletion), so alleles are reduced to their minimal form before matching. Trimming does
not left-align an indel in a repeat, so normalise both VCFs first with
`bcftools norm -f ref.fa -m -both`.
"""

from __future__ import annotations

import gzip
from pathlib import Path


def _open(path: Path):
    return gzip.open(path, "rt") if path.suffix == ".gz" else path.open(encoding="utf-8")


def minimal(pos: int, ref: str, alt: str) -> tuple[int, str, str]:
    while len(ref) > 1 and len(alt) > 1 and ref[-1] == alt[-1]:
        ref, alt = ref[:-1], alt[:-1]
    while len(ref) > 1 and len(alt) > 1 and ref[0] == alt[0]:
        ref, alt, pos = ref[1:], alt[1:], pos + 1
    return pos, ref, alt


def read_variants(path: str | Path, pass_only: bool = True) -> set[tuple[str, int, str, str]]:
    variants = set()
    with _open(Path(path)) as handle:
        for line in handle:
            if line.startswith("#") or not line.strip():
                continue
            chrom, pos, _id, ref, alts, _qual, filt = line.split("\t")[:7]
            if pass_only and filt not in ("PASS", "."):
                continue
            for alt in alts.split(","):
                if alt in ("*", "<*>", "<NON_REF>"):
                    continue
                # bases are case-insensitive in VCF; symbolic alleles such as <DEL> are not
                alt = alt if alt.startswith("<") else alt.upper()
                variants.add((chrom, *minimal(int(pos), ref.upper(), alt)))
    return variants


def _label(variants: set[tuple[str, int, str, str]]) -> list[str]:
    return sorted(f"{c}:{p} {r}>{a}" for c, p, r, a in variants)


def compare_vcf(calls: str | Path, truth: str | Path, strict: bool = False) -> dict[str, object]:
    """Site and allele match of PASS calls; genotype is never compared.

    With `strict`, the result also lists each called allele the truth set lacks
    (`extra_alleles`), so a caller can fail on it.
    """
    called, expected = read_variants(calls), read_variants(truth)
    found = called & expected
    result = {
        "truth": len(expected),
        "called": len(called),
        "found": len(found),
        "missed": _label(expected - called),
        "extra": len(called - expected),
    }
    if strict:
        result["extra_alleles"] = _label(called - expected)
    return result
