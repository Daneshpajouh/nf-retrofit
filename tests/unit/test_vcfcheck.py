import pytest

from nf_legacy_testkit.vcfcheck import compare_vcf, minimal


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
