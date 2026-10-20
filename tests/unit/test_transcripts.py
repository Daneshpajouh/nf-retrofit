import gzip
import json
import random
from itertools import combinations
from types import SimpleNamespace

from nf_retrofit import transcripts
from nf_retrofit.transcripts import compare_quant, simulate_transcripts

COMPLEMENT = str.maketrans("ACGT", "TGCA")


def _read_fasta(path):
    seqs, name = {}, None
    for line in path.read_text().splitlines():
        if line.startswith(">"):
            name = line[1:]
            seqs[name] = ""
        else:
            seqs[name] += line
    return seqs


def _shared_31mers(a, b):
    """31-mers of `a` found in `b` on either strand; Salmon indexes both."""
    kmers_b = {b[i : i + 31] for i in range(len(b) - 30)}
    kmers_b |= {k.translate(COMPLEMENT)[::-1] for k in kmers_b}
    return {a[i : i + 31] for i in range(len(a) - 30)} & kmers_b


def test_quant_within_two_percent_passes_and_a_swap_fails(data_dir):
    expected = json.loads((data_dir / "expected_counts.json").read_text())
    # tx_c is 1606 against 1600 (0.4%) and tx_d 1194 against 1200 (0.5%)
    assert compare_quant(data_dir / "quant_close.sf", expected) == []
    swapped = {**expected, "tx_a": {"num_reads": 800}, "tx_b": {"num_reads": 400}}
    assert compare_quant(data_dir / "quant_close.sf", swapped) == [
        "tx_a: NumReads 400.0, expected 800",
        "tx_b: NumReads 800.0, expected 400",
    ]


def test_fastq_holds_exactly_the_requested_fragments(tmp_path):
    expected = simulate_transcripts(tmp_path, {"tx_a": 30, "tx_b": 70}, length=600)
    names = {}
    for mate in ("1", "2"):
        with gzip.open(tmp_path / f"synthetic_{mate}.fq.gz", "rt") as fq:
            lines = fq.read().splitlines()
        names[mate] = [h[1:].rsplit("/", 1)[0] for h in lines[0::4]]
        assert {len(seq) for seq in lines[1::4]} == {75}
    assert names["1"] == names["2"]
    # read names carry the transcript each fragment was drawn from
    assert sum(".part_tx_a:" in n for n in names["1"]) == 30
    assert sum(".part_tx_b:" in n for n in names["1"]) == 70
    assert expected["tx_b"]["tpm"] == 700000.0


def test_no_31mer_is_shared_between_committed_transcripts(data_dir):
    seqs = _read_fasta(data_dir / "rnaseq_known" / "transcriptome.fa")
    assert sorted(seqs) == ["tx_a", "tx_b", "tx_c", "tx_d"]
    for a, b in combinations(seqs.values(), 2):
        assert not _shared_31mers(a, b)


class _PolyAThenPolyT(random.Random):
    """Draws tx_a as poly-A and tx_b as poly-T, then random bases.

    Every 31-mer of poly-T is the reverse complement of poly-A's, so a fragment from
    either could come from both transcripts.
    """

    def __init__(self, seed):
        super().__init__(seed)
        self.scripted = iter("A" * 600 + "T" * 600)

    def choice(self, seq):
        return next(self.scripted, None) or super().choice(seq)


def test_a_set_sharing_a_31mer_on_the_other_strand_is_redrawn(tmp_path, monkeypatch):
    monkeypatch.setattr(transcripts, "random", SimpleNamespace(Random=_PolyAThenPolyT))
    simulate_transcripts(tmp_path, {"tx_a": 1, "tx_b": 1}, length=600)
    seqs = _read_fasta(tmp_path / "transcriptome.fa")
    assert seqs["tx_a"] != "A" * 600
    assert not _shared_31mers(seqs["tx_a"], seqs["tx_b"])


def _quant(tmp_path, rows):
    path = tmp_path / "quant.sf"
    lines = ["Name\tLength\tEffectiveLength\tTPM\tNumReads"]
    lines += [f"{name}\t1500\t1251.000\t0\t{reads}" for name, reads in rows]
    path.write_text("\n".join(lines) + "\n")
    return path


def test_nan_count_fails(tmp_path, data_dir):
    expected = json.loads((data_dir / "expected_counts.json").read_text())
    quant = _quant(tmp_path, [("tx_a", "nan"), ("tx_b", 800), ("tx_c", 1600), ("tx_d", 1200)])
    assert compare_quant(quant, expected) == ["tx_a: NumReads nan is not a count"]


def test_duplicate_and_unexpected_transcripts_fail(tmp_path, data_dir):
    expected = json.loads((data_dir / "expected_counts.json").read_text())
    rows = [("tx_a", 9), ("tx_a", 400), ("tx_b", 800), ("tx_c", 1600), ("tx_d", 1200)]
    quant = _quant(tmp_path, [*rows, ("tx_x", 0)])
    assert compare_quant(quant, expected) == [
        "tx_a: listed twice in quant.sf",
        "tx_x: in quant.sf but not in the expected counts",
    ]
