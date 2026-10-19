# Run logging

`scripts/run_with_logs.sh <run_dir> <pipeline_dir> [nextflow args]` wraps one `nextflow run` and leaves everything about the run in `<run_dir>`:

| File | Written | Content |
|---|---|---|
| `manifest.json` | before the run | start time (UTC), host, Nextflow version, pipeline directory and git commit, container, arguments, every input file with size and SHA-256 |
| `nextflow.log`, `console.txt` | during | Nextflow's own log and the console output |
| `trace.tsv`, `report.html`, `timeline.html` | during | per-task status, exit code, times, CPU and peak memory |
| `summary.json` | after | status, exit code, duration, failed and retried tasks, a per-process resource table, every output file with size and SHA-256 |

Arguments that name files, globs or `{1,2}` pairs are expanded and hashed, so the manifest records the read files behind `--reads 'sample_{1,2}.fq.gz'`. Set `OUTDIR_PARAM` when the pipeline's output parameter is not `outdir` (CalliNGS-NF uses `results`). The summary's status is `FAILED` if Nextflow exits non-zero or the last attempt of any task ended other than COMPLETED or CACHED. A task that succeeds on retry counts once and is listed under `retried_tasks` with the exit code of each attempt.

## Example: rnaseq-nf on the known-answer data

Run on 2026-10-19 (Nextflow 26.10.2, docker profile under amd64 emulation, arm64 Mac):

```
$ scripts/run_with_logs.sh runs/rnaseq_known examples/rnaseq-nf -profile docker -c conf/test.config \
    --reads "$PWD/tests/data/rnaseq_known/synthetic_{1,2}.fq.gz" \
    --transcriptome $PWD/tests/data/rnaseq_known/transcriptome.fa
[SUCCESS] completed=4 failed=0 cached=0
OK: 4 tasks, 0 failed, 25.3 s
```

`manifest.json`, trimmed:

```json
{
  "started_utc": "2026-10-19T19:19:09+00:00",
  "nextflow": "N E X T F L O W version 26.10.2 build 0 ...",
  "pipeline_commit": "bad0c709877f5091b27db3a7f38118424e242e3c",
  "inputs": [
    {"path": ".../conf/test.config", "bytes": 395, "sha256": "7a65fcb5f561..."},
    {"path": ".../synthetic_1.fq.gz", "bytes": 55946, "sha256": "fb587f1cd61b..."},
    {"path": ".../synthetic_2.fq.gz", "bytes": 55852, "sha256": "11ee85241bf2..."},
    {"path": ".../transcriptome.fa", "bytes": 6124, "sha256": "9fc698139af3..."}
  ]
}
```

`trace.tsv`, four columns of it:

```
name                          status     realtime  peak_rss
RNASEQ:INDEX (transcriptome)  COMPLETED  712ms     47.4 MB
RNASEQ:QUANT (synthetic)      COMPLETED  1.2s      219.6 MB
RNASEQ:FASTQC (synthetic)     COMPLETED  8.9s      272 MB
MULTIQC                       COMPLETED  4.1s      126.9 MB
```

`summary.json`, trimmed: status `OK`, 25.3 s, 4 tasks, no failed tasks, and five output files: two FastQC HTML reports, their two zip archives and `multiqc_report.html` (4,763,598 bytes). The FastQC zips hash differently on every run because they carry timestamps; the HTML reports hash the same.

## Example: a run that fails before any task

The same command with a relative `--transcriptome` path:

```
[ERROR] ERROR ~ Error executing process > 'RNASEQ:INDEX'
Caused by:
  Not a valid path value: 'tests/data/rnaseq_known/transcriptome.fa'
FAILED: 0 tasks, 0 failed, 5.2 s
```

`summary.json` records `"status": "FAILED"`, `"exit_code": 1` and an empty task list; `console.txt` holds the cause. See "A relative transcriptome path fails" in `docs/findings/rnaseq-nf.md`.
