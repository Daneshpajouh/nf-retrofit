# rnaseq-nf: findings

Pinned at tag v2.4 (commit bad0c70). Checked with Nextflow 26.10.2 on 2026-10-19, docker profile under amd64 emulation on an arm64 Mac. Written to be offered to the maintainers as an issue.

## Salmon output is not published

`FASTQC` and `MULTIQC` declare `publishDir params.outdir`; `INDEX` and `QUANT` do not (`modules/quant/main.nf`, `modules/index/main.nf`). A run on this kit's known-answer data finished with exit 0 and an output directory holding only the FastQC reports and `multiqc_report.html`; `quant.sf` existed only under `work/`. Anyone cleaning `work/` after a run loses the quantification. Fix: add `publishDir "${params.outdir}/quant", mode: 'copy'` to `QUANT`.

## A relative transcriptome path fails

`--transcriptome tests/data/rnaseq_known/transcriptome.fa` stops `INDEX` before it starts with `Not a valid path value: 'tests/data/rnaseq_known/transcriptome.fa'`; the same file given as an absolute path works. `main.nf` passes the parameter string straight to the `path` input of `INDEX`. Wrapping it in `file(params.transcriptome, checkIfExists: true)` accepts both forms and fails early on a missing file.

## CI checks the exit status only

`.github/workflows/build.yml` runs `nextflow run . -profile docker` (and again with `wave`) and passes if the run exits 0. No step reads an output. The known-answer test in this kit (`tests/nf-test/rnaseq-nf/known_counts.nf.test`) asserts Salmon's NumReads for four unique transcripts: 400, 800, 1,600 and 1,200, all recovered exactly, with a 100% mapping rate.

## No stub blocks

None of the four processes defines `stub:`, so `-stub-run` runs the real scripts. A dry run therefore needs the container and real input files.

## Container is amd64 only

`docker pull docker.io/nextflow/rnaseq-nf:v1.3.1` on an arm64 host fails with `no matching manifest for linux/arm64/v8`. It runs with `--platform linux/amd64` under emulation; `conf/test.config` sets that. The FastQC step took 15.4 s of task time on 4,000 read pairs this way.

## Lint

`nextflow lint` 26.10.2 reports nothing (`docs/lint/rnaseq-nf.md`). Of the two examples this is the one that parses under the strict syntax today.
