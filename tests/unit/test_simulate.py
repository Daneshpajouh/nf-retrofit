import gzip
import random

from nf_legacy_testkit.simulate import Variant, apply, pick_variants, read_fasta, simulate_germline


def _toy_reference(tmp_path, length=12_000):
    rng = random.Random(7)
    path = tmp_path / "toy.fa"
    path.write_text(">chrT\n" + "".join(rng.choice("ACGT") for _ in range(length)) + "\n")
    return path


def test_apply_handles_neighbouring_snv_and_deletion():
    variants = [Variant("1", 3, "C", "T", "snv", "het"), Variant("1", 5, "GGT", "G", "indel", "het")]
    assert apply("AACCGGTT", "1", variants) == "AATCGT"


def test_placed_alleles_match_the_reference(tmp_path):
    ref = read_fasta(_toy_reference(tmp_path))
    variants = pick_variants(ref, random.Random(1), {"chrT": 6}, {"chrT": 3}, germline_per_kb=0.0)
    assert len(variants) == 9
    for v in variants:
        assert ref[v.contig][v.pos - 1 : v.pos - 1 + len(v.ref)] == v.ref


def test_same_seed_gives_identical_reads(tmp_path):
    ref = _toy_reference(tmp_path)
    simulate_germline(ref, tmp_path / "a", snvs_per_contig=4, depth=3, seed=11)
    simulate_germline(ref, tmp_path / "b", snvs_per_contig=4, depth=3, seed=11)
    read = lambda p: gzip.open(p, "rt").read()  # noqa: E731
    assert read(tmp_path / "a" / "sample_chrT_R1.fastq.gz") == read(tmp_path / "b" / "sample_chrT_R1.fastq.gz")


def test_homozygous_sites_have_no_reference_reads_and_het_sites_have_both(tmp_path):
    ref_path = _toy_reference(tmp_path, length=20_000)
    simulate_germline(ref_path, tmp_path / "g", snvs_per_contig=8, depth=40, seed=3)
    seq = read_fasta(ref_path)["chrT"]
    rc = str.maketrans("ACGT", "TGCA")
    reads = []
    for mate in ("R1", "R2"):
        with gzip.open(tmp_path / "g" / f"sample_chrT_{mate}.fastq.gz", "rt") as fq:
            reads += [line.strip() for k, line in enumerate(fq) if k % 4 == 1]

    def count(kmer):
        return sum(kmer in r or kmer.translate(rc)[::-1] in r for r in reads)

    zygosities = set()
    for line in (tmp_path / "g" / "truth.vcf").read_text().splitlines():
        if line.startswith("#"):
            continue
        _chrom, pos, _id, ref, alt, _q, _f, info = line.split("\t")
        i = int(pos) - 1
        n_alt = count(seq[i - 12 : i] + alt + seq[i + 1 : i + 13])
        n_ref = count(seq[i - 12 : i + 13])
        zyg = info.split("ZYG=")[1]
        zygosities.add(zyg)
        assert n_alt > 0
        assert (n_ref == 0) if zyg == "hom" else (n_ref > 0)
    assert zygosities == {"het", "hom"}
