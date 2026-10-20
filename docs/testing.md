# Testing

Four layers, from seconds to minutes. Numbers are from runs on 2026-10-19 on an arm64 Mac (Nextflow 26.10.2, nf-test 0.9.5, Python 3.13) unless marked CI.

## 1. Unit tests (pytest, no Nextflow)

`make unit`: 41 tests in 0.99 s. They cover the kit's own code against hand-checked fixtures in `tests/data`: allele trimming before VCF comparison (`CCTC>CC` is `CCT>C`), lowercase bases and blank lines in a VCF, `check-vcf` exit status with and without `--fail-on-extra`, Salmon counts within and outside a 2% tolerance and NaN, duplicate or unexpected rows, parsing real `nextflow lint` output, trace summaries with a failed task, a retry, two tasks sharing a tag (also with one task's retry landing after the other finished) and a missing trace, glob and `{1,2}` expansion and a malformed `--param` in the manifest, and the read simulators (seeded output is identical between runs, truth alleles match the reference, a contig too short for a variant is skipped, no 31-mer is shared between synthetic transcripts).

## 2. Static checks (`nextflow lint`)

`make lint-reports` writes `docs/lint/<pipeline>.txt` (raw) and `.md` (counted). Nextflow 26.10.2 found nothing in rnaseq-nf v2.4 and 3 errors and 5 warnings in CalliNGS-NF; CI regenerates the reports with the pinned 26.10.2 and fails if they change; moving the pin to a newer release shows what that release rejects as a diff.

## 3. Known-answer pipeline tests (nf-test)

rnaseq-nf runs on `tests/data/rnaseq_known`: four synthetic transcripts with no shared 31-mer, so every fragment has one correct origin and Salmon's expected NumReads equals the number of fragments drawn from each transcript.

```
$ make nf-test
  Test 'four unique transcripts, 4,000 fragments' PASSED (15.7s)
  Test '-stub-run falls through to the real scripts (no stub blocks)' PASSED (13.1s)
SUCCESS: Executed 2 tests in 28.8s
```

Salmon returned 400, 800, 1,600 and 1,200 reads, the drawn numbers exactly, with a 100% mapping rate. The test reads `quant.sf` from the task directory because rnaseq-nf does not publish it.

For variant callers, `nf-retrofit germline` writes paired reads from a FASTA reference (contigs of 1,000 bases or fewer get no variants and no reads) with a known set of heterozygous and homozygous SNVs and a truth VCF, and `nf-retrofit check-vcf calls.vcf truth.vcf` compares the PASS calls after trimming padded alleles. Trimming does not left-align an indel in a repeat, so normalise both VCFs first with `bcftools norm -f ref.fa -m -both`.

By default `check-vcf` fails only when a truth allele is missed; extra calls are counted (`extra`) but pass. Strict mode, `check-vcf --fail-on-extra calls.vcf truth.vcf`, also fails when any PASS call carries an allele the truth VCF lacks, whether at a true site (`1:200 A>G,T` against a truth of `A>G`) or at a new one, and lists each one under `extra_alleles`. Both modes compare only calls whose FILTER is `PASS` or `.`, and skip the `*`, `<*>` and `<NON_REF>` alleles. Neither compares genotype unless asked: with `--compare-genotypes`, a heterozygous call of a homozygous truth variant is listed under `genotype_mismatches` (`1:200 A>G called 0/1, truth 1/1`) and fails the check, while it still counts as found; `--phased` also compares phase.

## 4. Whole-pipeline runs with logs

`scripts/run_with_logs.sh` (see `docs/logging.md`) runs a pipeline unchanged with `conf/test.config`: at most one CPU and 2 GB per task, `pipefail` in every task shell, and `--platform linux/amd64` for images that have no arm64 build.

## What did not run here

CalliNGS-NF did not run on this Mac. Nextflow 26.10.2 rejects it (`phase` operator, top-level statements), and the Homebrew launcher would not pin an older Nextflow. The `callings-nf` CI step runs `tests/nf-test/callings-nf/bundled_data.nf.test` with the official launcher, Java 17 and `NXF_VER=22.04.5`, because the `phase` operator in `modules.nf` already fails on 22.10.8, 23.10.1 and 24.04.4 (checked in containers with Java 17), and nf-test 0.9.5 runs on 22.04.5. In that GitHub Actions step the pipeline ran end to end on its bundled data and produced its VCF, and the test passed. It still does not run on current Nextflow.
