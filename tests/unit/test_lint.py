import pytest

from nf_retrofit.lint import lint_file_to_markdown, parse_lint, to_markdown


def test_reads_level_location_and_message_from_real_lint_output(data_dir):
    findings = parse_lint((data_dir / "lint_two_errors.txt").read_text())
    assert [(f["level"], f["file"], f["line"]) for f in findings] == [
        ("Error", "examples/callings-nf/main.nf", 41),
        ("Warn", "examples/callings-nf/main.nf", 72),
    ]
    assert findings[0]["message"].startswith("Statements cannot be mixed")


def test_clean_lint_reports_zero_counts():
    text = to_markdown(parse_lint("Linting Nextflow code..\nNextflow linting complete!\n"), "rnaseq-nf")
    assert "0 errors, 0 warnings." in text


def test_output_of_a_crashed_or_missing_lint_is_not_a_clean_run(data_dir):
    with pytest.raises(ValueError, match="finished"):
        parse_lint((data_dir / "lint_crash.txt").read_text())
    # what dash on the CI runner prints when nextflow is not on PATH
    with pytest.raises(ValueError, match="finished"):
        parse_lint("/bin/sh: 1: nextflow: not found\n")


def test_lint_exit_status_must_agree_with_the_errors_it_printed(data_dir):
    # lint exits 1 when it reports errors; 137 means it was killed partway through
    assert "1 errors, 1 warnings." in lint_file_to_markdown(data_dir / "lint_two_errors.txt", "CalliNGS-NF", 1)
    with pytest.raises(ValueError, match="exited 137"):
        lint_file_to_markdown(data_dir / "lint_two_errors.txt", "CalliNGS-NF", 137)
