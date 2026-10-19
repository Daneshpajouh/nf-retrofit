import gzip
import json

from nf_retrofit.transcripts import compare_quant, simulate_transcripts


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
    with gzip.open(tmp_path / "synthetic_1.fq.gz", "rt") as fq:
        records = sum(1 for line in fq if line.startswith("@"))
    assert records == 100
    assert expected["tx_b"]["tpm"] == 700000.0


def test_no_31mer_is_shared_between_transcripts(tmp_path):
    simulate_transcripts(tmp_path, {"tx_a": 1, "tx_b": 1, "tx_c": 1})
    seqs, name = {}, None
    for line in (tmp_path / "transcriptome.fa").read_text().splitlines():
        if line.startswith(">"):
            name = line[1:]
            seqs[name] = ""
        else:
            seqs[name] += line
    kmers = [{s[i : i + 31] for i in range(len(s) - 30)} for s in seqs.values()]
    assert not (kmers[0] & kmers[1] or kmers[0] & kmers[2] or kmers[1] & kmers[2])
