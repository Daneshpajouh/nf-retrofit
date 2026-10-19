# Testing

Four layers, from seconds to minutes. Numbers are from runs on 2026-10-19 on an arm64 Mac (Nextflow 26.10.2, nf-test 0.9.5, Python 3.13) unless marked CI.

## 1. Unit tests (pytest, no Nextflow)

`make unit`: 22 tests in 1.18 s. They cover the kit's own code against hand-checked fixtures in `tests/data`: allele trimming before VCF comparison (`CCTC>CC` is `CCT>C`), Salmon counts within and outside a 2% tolerance, parsing real `nextflow lint` output, trace summaries with a failed task, glob and `{1,2}` expansion in the manifest, and the read simulators (seeded output is identical between runs, truth alleles match the reference, no 31-mer is shared between synthetic transcripts).

## 2. Static checks (`nextflow lint`)

`make lint-reports` writes `docs/lint/<pipeline>.txt` (raw) and `.md` (counted). Nextflow 26.10.2 found nothing in rnaseq-nf v2.4 and 3 errors and 5 warnings in CalliNGS-NF; CI regenerates the reports and fails if they change, so a new Nextflow release that rejects more code shows up as a diff.

## 3. Known-answer pipeline tests (nf-test)

rnaseq-nf runs on `tests/data/rnaseq_known`: four synthetic transcripts with no shared 31-mer, so every fragment has one correct origin and Salmon's expected NumReads equals the number of fragments drawn from each transcript.

```
$ make nf-test
  Test 'four unique transcripts, 4,000 fragments' PASSED (15.7s)
  Test '-stub-run falls through to the real scripts (no stub blocks)' PASSED (13.1s)
SUCCESS: Executed 2 tests in 28.8s
```

Salmon returned 400, 800, 1,600 and 1,200 reads, the drawn numbers exactly, with a 100% mapping rate. The test reads `quant.sf` from the task directory because rnaseq-nf does not publish it.

For variant callers, `nf-retrofit germline` writes paired reads from any reference with a known set of heterozygous and homozygous SNVs and a truth VCF, and `nf-retrofit check-vcf calls.vcf truth.vcf` compares the PASS calls after trimming padded alleles. Trimming does not left-align an indel in a repeat, so normalise both VCFs first with `bcftools norm -f ref.fa -m -both`.

## 4. Whole-pipeline runs with logs

`scripts/run_with_logs.sh` (see `docs/logging.md`) runs a pipeline unchanged with `conf/test.config`: at most one CPU and 2 GB per task, `pipefail` in every task shell, and `--platform linux/amd64` for images that have no arm64 build.

## What did not run here

CalliNGS-NF did not run on this Mac. Nextflow 26.10.2 rejects it (`phase` operator, top-level statements), and the Homebrew launcher would not pin an older Nextflow. The `callings-nf` CI step runs `tests/nf-test/callings-nf/bundled_data.nf.test` with the official launcher, Java 17 and `NXF_VER=22.04.5`, because the `phase` operator in `modules.nf` already fails on 22.10.8, 23.10.1 and 24.04.4 (checked in containers with Java 17), and nf-test 0.9.5 runs on 22.04.5. Its result is in CI, not here.
