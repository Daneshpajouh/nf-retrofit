import json

import pytest

from nf_retrofit.cli import main


@pytest.mark.parametrize(
    ("calls", "flags", "status"),
    [
        ("calls_strict_pass.vcf", [], 0),
        ("calls_strict_pass.vcf", ["--fail-on-extra"], 0),
        ("calls_strict_extra.vcf", [], 0),  # default: extra calls are counted, not failed
        ("calls_strict_extra.vcf", ["--fail-on-extra"], 1),
        ("calls_padded.vcf", ["--fail-on-extra"], 1),  # a missed call still fails
    ],
)
def test_check_vcf_exit_status(data_dir, capsys, calls, flags, status):
    assert (
        main(["check-vcf", str(data_dir / calls), str(data_dir / "truth_three.vcf"), *flags])
        == status
    )
    result = json.loads(capsys.readouterr().out)
    assert ("extra_alleles" in result) == bool(flags)


def test_check_vcf_strict_output_names_the_extra_alleles(data_dir, capsys):
    main(
        [
            "check-vcf",
            str(data_dir / "calls_strict_extra.vcf"),
            str(data_dir / "truth_three.vcf"),
            "--fail-on-extra",
        ]
    )
    assert json.loads(capsys.readouterr().out)["extra_alleles"] == ["1:200 A>T", "2:50 C>G"]


@pytest.mark.parametrize(
    ("flags", "status"),
    [
        ([], 0),  # same alleles, so the default check passes
        (["--fail-on-extra"], 0),
        (["--compare-genotypes"], 1),
        (["--compare-genotypes", "--fail-on-extra"], 1),
    ],
)
def test_check_vcf_genotype_option_exit_status(data_dir, capsys, flags, status):
    calls, truth = str(data_dir / "calls_gt.vcf"), str(data_dir / "truth_gt.vcf")
    assert main(["check-vcf", calls, truth, *flags]) == status
    result = json.loads(capsys.readouterr().out)
    assert ("genotype_mismatches" in result) == ("--compare-genotypes" in flags)


def test_check_vcf_phased_needs_the_genotype_option(data_dir, capsys):
    calls, truth = str(data_dir / "calls_gt.vcf"), str(data_dir / "truth_gt.vcf")
    assert main(["check-vcf", calls, truth, "--phased"]) == 2
    assert "--phased needs --compare-genotypes" in capsys.readouterr().err
