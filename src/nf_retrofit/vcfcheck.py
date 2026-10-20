"""Compare called variants with a truth VCF after trimming shared flanking bases.

Callers write the same variant with different padding (CCTC>CC and CCT>C are one
deletion), so alleles are reduced to their minimal form before matching. Trimming does
not left-align an indel in a repeat, so normalise both VCFs first with
`bcftools norm -f ref.fa -m -both`.
"""

from __future__ import annotations

import gzip
import re
from pathlib import Path


def _open(path: Path):
    return gzip.open(path, "rt") if path.suffix == ".gz" else path.open(encoding="utf-8")


def minimal(pos: int, ref: str, alt: str) -> tuple[int, str, str]:
    while len(ref) > 1 and len(alt) > 1 and ref[-1] == alt[-1]:
        ref, alt = ref[:-1], alt[:-1]
    while len(ref) > 1 and len(alt) > 1 and ref[0] == alt[0]:
        ref, alt, pos = ref[1:], alt[1:], pos + 1
    return pos, ref, alt


Key = tuple[str, int, str, str]
# GT allele codes in the order written, and whether the GT is phased.
Genotype = tuple[tuple[str, ...], bool]


def _genotype(fields: list[str], alt_index: int) -> Genotype | None:
    """GT of the first sample for one ALT allele, or None when there is no genotype.

    No GT field, an empty or cut-off value and an all-missing GT (`.`, `./.`) give None.
    Other ALT alleles read as 0, as `bcftools norm -m -both` writes them when it
    splits a record.
    """
    if len(fields) < 10:
        return None
    keys, values = fields[8].split(":"), fields[9].split(":")
    if "GT" not in keys or keys.index("GT") >= len(values):
        return None
    gt = values[keys.index("GT")]
    if not gt.strip("./|"):
        return None
    codes = tuple(
        c if c in ("0", ".") else "1" if c == str(alt_index) else "0" for c in re.split("[/|]", gt)
    )
    return codes, "|" in gt and "/" not in gt


def _same(called: Genotype, truth: Genotype, phased: bool) -> bool:
    # Phase is compared only when asked and when both sides are phased.
    if phased and called[1] and truth[1]:
        return called[0] == truth[0]
    return sorted(called[0]) == sorted(truth[0])


def _show(gt: Genotype) -> str:
    return ("|" if gt[1] else "/").join(gt[0])


def _records(path: str | Path, pass_only: bool):
    with _open(Path(path)) as handle:
        for line in handle:
            if line.startswith("#") or not line.strip():
                continue
            fields = line.rstrip("\r\n").split("\t")
            chrom, pos, _id, ref, alts, _qual, filt = fields[:7]
            if pass_only and filt not in ("PASS", "."):
                continue
            for index, alt in enumerate(alts.split(","), start=1):
                if alt in ("*", "<*>", "<NON_REF>"):
                    continue
                # bases are case-insensitive in VCF; symbolic alleles such as <DEL> are not
                alt = alt if alt.startswith("<") else alt.upper()
                key = (chrom, *minimal(int(pos), ref.upper(), alt))
                yield key, _genotype(fields, index)


def read_variants(path: str | Path, pass_only: bool = True) -> set[Key]:
    return {key for key, _gt in _records(path, pass_only)}


def _written_alike(a: Genotype | None, b: Genotype | None) -> bool:
    # 0/1 and 1/0 are one unphased genotype; a phased GT keeps its order
    if a is None or b is None:
        return a is b
    if a[1] != b[1]:
        return False
    return a[0] == b[0] if a[1] else sorted(a[0]) == sorted(b[0])


def read_genotypes(path: str | Path, pass_only: bool = True) -> dict[Key, Genotype | None]:
    """GT per site and allele. A site and allele listed twice with different GTs gives
    None, since the file does not say which one holds."""
    genotypes: dict[Key, Genotype | None] = {}
    for key, gt in _records(path, pass_only):
        genotypes[key] = gt if key not in genotypes or _written_alike(genotypes[key], gt) else None
    return genotypes


def _label(variants: set[Key]) -> list[str]:
    return sorted(f"{c}:{p} {r}>{a}" for c, p, r, a in variants)


def compare_vcf(
    calls: str | Path,
    truth: str | Path,
    strict: bool = False,
    genotypes: bool = False,
    phased: bool = False,
) -> dict[str, object]:
    """Site and allele match of PASS calls; genotype only when asked.

    With `strict`, the result also lists each called allele the truth set lacks
    (`extra_alleles`), so a caller can fail on it. With `genotypes`, each matched
    allele's GT is compared too: a different GT is listed under `genotype_mismatches`,
    and a match where either file has no GT under `genotype_unknown`, apart from the
    missed and extra calls. Phase counts only with `phased`.
    """
    called, expected = read_variants(calls), read_variants(truth)
    found = called & expected
    result: dict[str, object] = {
        "truth": len(expected),
        "called": len(called),
        "found": len(found),
        "missed": _label(expected - called),
        "extra": len(called - expected),
    }
    if strict:
        result["extra_alleles"] = _label(called - expected)
    if genotypes:
        called_gt, truth_gt = read_genotypes(calls), read_genotypes(truth)
        mismatches, unknown = [], []
        for k in sorted(found):
            c, g = called_gt[k], truth_gt[k]
            if c is None or g is None:
                unknown.append(_label({k})[0])
            elif not _same(c, g, phased):
                mismatches.append(f"{_label({k})[0]} called {_show(c)}, truth {_show(g)}")
        result["genotype_mismatches"] = mismatches
        result["genotype_unknown"] = unknown
    return result
