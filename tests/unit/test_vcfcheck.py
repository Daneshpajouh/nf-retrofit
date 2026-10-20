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


def test_default_comparison_ignores_genotype(data_dir):
    # 1:200 is 0/1 in the calls and 1/1 in the truth set: same allele, wrong zygosity
    result = compare_vcf(data_dir / "calls_gt.vcf", data_dir / "truth_gt.vcf")
    assert (result["found"], result["missed"], result["extra"]) == (3, [], 0)
    assert "genotype_mismatches" not in result


@pytest.mark.parametrize("strict", [False, True])
def test_genotype_mismatch_is_reported_apart_from_missed_and_extra_calls(data_dir, strict):
    result = compare_vcf(
        data_dir / "calls_gt.vcf", data_dir / "truth_gt.vcf", strict=strict, genotypes=True
    )
    assert (result["found"], result["missed"], result["extra"]) == (3, [], 0)
    assert result["genotype_mismatches"] == ["1:200 A>G called 0/1, truth 1/1"]
    assert result["genotype_unknown"] == []
    assert result.get("extra_alleles", []) == []


def test_phase_is_compared_only_when_asked(data_dir):
    # 1:300 is 1|0 in the calls and 0|1 in the truth set
    result = compare_vcf(
        data_dir / "calls_gt.vcf", data_dir / "truth_gt.vcf", genotypes=True, phased=True
    )
    assert result["genotype_mismatches"] == [
        "1:200 A>G called 0/1, truth 1/1",
        "1:300 T>C called 1|0, truth 0|1",
    ]


def test_a_truth_set_without_genotypes_leaves_every_match_unknown(data_dir):
    result = compare_vcf(data_dir / "calls_gt.vcf", data_dir / "truth_three.vcf", genotypes=True)
    assert result["genotype_mismatches"] == []
    assert result["genotype_unknown"] == ["1:100 CCT>C", "1:200 A>G", "1:300 T>C"]


def test_multiallelic_genotype_is_read_per_allele_as_after_a_split(tmp_path):
    # bcftools norm -m -both splits 1/2 into 0/1 for each allele
    header = "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS\n"
    calls = tmp_path / "calls.vcf"
    calls.write_text(header + "1\t200\t.\tA\tG,T\t40\tPASS\t.\tGT\t1/2\n")
    truth = tmp_path / "truth.vcf"
    truth.write_text(
        header + "1\t200\t.\tA\tG\t.\tPASS\t.\tGT\t0/1\n1\t200\t.\tA\tT\t.\tPASS\t.\tGT\t1/0\n"
    )
    result = compare_vcf(calls, truth, genotypes=True)
    assert result["found"] == 2
    assert result["genotype_mismatches"] == []


GT_HEADER = "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS\n"


@pytest.mark.parametrize("gt", [".", "./.", ".|.", ""])
def test_a_missing_genotype_is_unknown_not_a_mismatch(tmp_path, gt):
    calls, truth = tmp_path / "calls.vcf", tmp_path / "truth.vcf"
    calls.write_text(GT_HEADER + f"1\t200\t.\tA\tG\t40\tPASS\t.\tGT:DP\t{gt}:9\n")
    truth.write_text(GT_HEADER + "1\t200\t.\tA\tG\t.\tPASS\t.\tGT\t1/1\n")
    result = compare_vcf(calls, truth, genotypes=True)
    assert result["genotype_mismatches"] == []
    assert result["genotype_unknown"] == ["1:200 A>G"]


def test_a_site_listed_twice_with_different_genotypes_is_unknown(tmp_path):
    # CCTC>CC and CCT>C trim to the same deletion
    calls, truth = tmp_path / "calls.vcf", tmp_path / "truth.vcf"
    calls.write_text(
        GT_HEADER
        + "1\t100\t.\tCCTC\tCC\t50\tPASS\t.\tGT\t0/1\n1\t100\t.\tCCT\tC\t50\tPASS\t.\tGT\t1/1\n"
    )
    truth.write_text(GT_HEADER + "1\t100\t.\tCCT\tC\t.\tPASS\t.\tGT\t1/1\n")
    result = compare_vcf(calls, truth, genotypes=True)
    assert result["genotype_unknown"] == ["1:100 CCT>C"]


def test_phase_is_not_compared_against_an_unphased_genotype(tmp_path):
    calls, truth = tmp_path / "calls.vcf", tmp_path / "truth.vcf"
    calls.write_text(GT_HEADER + "1\t200\t.\tA\tG\t40\tPASS\t.\tGT\t1|0\n")
    truth.write_text(GT_HEADER + "1\t200\t.\tA\tG\t.\tPASS\t.\tGT\t0/1\n")
    result = compare_vcf(calls, truth, genotypes=True, phased=True)
    assert result["genotype_mismatches"] == []
