from nf_legacy_testkit.lint import parse_lint, to_markdown


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
