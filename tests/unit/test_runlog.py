import json

from nf_legacy_testkit.runlog import _duration_ms, summarise, write_manifest


def test_failed_task_marks_the_run_failed(tmp_path, data_dir):
    inp = tmp_path / "samples.csv"
    inp.write_text("sample,fastq_1,fastq_2\n")
    manifest = tmp_path / "manifest.json"
    write_manifest(manifest, [inp], {"profile": "test"}, tmp_path, None)
    # digest from `shasum -a 256` on the same 23 bytes
    assert json.loads(manifest.read_text())["inputs"][0]["sha256"] == (
        "edef0d20e348c82bf5a26e76b8ab8c32e1ec317a75221ff3a3aa481e299444a6"
    )
    out_dir = tmp_path / "results"
    out_dir.mkdir()
    (out_dir / "multiqc_report.html").write_text("<html></html>\n")
    summary = summarise(data_dir / "trace_one_failed.tsv", out_dir, 0, manifest, tmp_path / "summary.json")
    assert summary["status"] == "FAILED"
    assert summary["failed_tasks"] == [{"name": "RNASEQ:QUANT (ggal_gut)", "status": "FAILED", "exit": "127"}]
    assert [r["process"] for r in summary["resources"]] == ["RNASEQ:INDEX", "RNASEQ:QUANT"]
    assert summary["outputs"][0]["path"] == "multiqc_report.html"


def test_durations_in_nextflow_trace_format():
    assert _duration_ms("219ms") == 219
    assert _duration_ms("1m 4s") == 64_000
    assert _duration_ms("-") is None


def test_read_pair_glob_expands_to_both_files(tmp_path):
    from nf_legacy_testkit.runlog import expand

    for name in ("s1_1.fq.gz", "s1_2.fq.gz", "s1_3.fq.gz"):
        (tmp_path / name).write_text("@r\nA\n+\nI\n")
    found = expand([str(tmp_path / "s1_{1,2}.fq.gz"), str(tmp_path / "missing.fa"), "results"])
    assert [p.name for p in found] == ["s1_1.fq.gz", "s1_2.fq.gz"]
