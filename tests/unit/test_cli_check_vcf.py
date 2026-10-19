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
