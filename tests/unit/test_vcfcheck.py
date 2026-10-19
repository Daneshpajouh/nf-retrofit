import pytest

from nf_retrofit.vcfcheck import compare_vcf, minimal


@pytest.mark.parametrize(
    ("pos", "ref", "alt", "expected"),
    [
        (100, "CCTC", "CC", (100, "CCT", "C")),  # deletion written with a trailing base
        (324851, "AACCACCAC", "AACCACCACCAC", (324851, "A", "AACC")),  # insertion in a repeat
        (35726, "CA", "CAA", (35726, "C", "CA")),
        (10, "ATG", "ACG", (11, "T", "C")),  # SNV padded on both sides
        (5, "G", "T", (5, "G", "T")),
    ],
)
def test_minimal_form_of_padded_alleles(pos, ref, alt, expected):
    assert minimal(pos, ref, alt) == expected


def test_padding_and_symbolic_alleles_do_not_hide_a_match(data_dir):
    result = compare_vcf(data_dir / "calls_padded.vcf", data_dir / "truth_three.vcf")
    # the LowQual call at 1:300 is not PASS, so it counts as missed
    assert result["found"] == 2
    assert result["missed"] == ["1:300 T>C"]
    assert result["extra"] == 0


def test_strict_mode_passes_when_every_pass_allele_is_in_the_truth_set(data_dir):
    # the LowQual call at 1:400 is not in the truth set, but only PASS calls are compared
    result = compare_vcf(
        data_dir / "calls_strict_pass.vcf", data_dir / "truth_three.vcf", strict=True
    )
    assert result["found"] == 3
    assert result["missed"] == []
    assert result["extra_alleles"] == []


def test_strict_mode_lists_extra_alleles_at_true_and_new_sites(data_dir):
    result = compare_vcf(
        data_dir / "calls_strict_extra.vcf", data_dir / "truth_three.vcf", strict=True
    )
    assert result["found"] == 3
    assert result["extra"] == 2
    assert result["extra_alleles"] == ["1:200 A>T", "2:50 C>G"]


def test_default_result_has_no_extra_allele_list(data_dir):
    result = compare_vcf(data_dir / "calls_strict_extra.vcf", data_dir / "truth_three.vcf")
    assert "extra_alleles" not in result


HEADER = "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"


def test_lowercase_alleles_match_the_truth_set(tmp_path, data_dir):
    # the VCF spec makes REF and ALT bases case-insensitive
    calls = tmp_path / "lower.vcf"
    calls.write_text(
        HEADER + "1\t100\t.\tcct\tc\t.\tPASS\t.\n1\t200\t.\ta\tg,<*>\t.\tPASS\t.\n"
        "1\t300\t.\tT\tc\t.\tPASS\t.\n"
    )
    result = compare_vcf(calls, data_dir / "truth_three.vcf")
    assert result["found"] == 3
    assert result["missed"] == []


def test_blank_line_at_the_end_of_a_hand_edited_vcf_is_skipped(tmp_path, data_dir):
    truth = tmp_path / "truth.vcf"
    truth.write_text((data_dir / "truth_three.vcf").read_text() + "\n")
    result = compare_vcf(data_dir / "calls_strict_pass.vcf", truth)
    assert result["truth"] == 3
    assert result["missed"] == []
