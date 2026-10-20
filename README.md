# nf-retrofit

Tests, profiles, known-answer data and run logging for an existing Nextflow pipeline that has none, added from outside: the pipeline is a pinned git submodule and is never edited. Everything this kit adds lives in its own files.

Two published pipelines are the worked examples:

| Pipeline | Pinned at | Licence | Why |
|---|---|---|---|
| [nextflow-io/rnaseq-nf](https://github.com/nextflow-io/rnaseq-nf) | tag v2.4, bad0c70 | Apache-2.0 | the Nextflow project's own RNA-seq example (FastQC, Salmon, MultiQC), copied into many tutorials; CI only checks that a run exits 0 |
| [CRG-CNAG/CalliNGS-NF](https://github.com/CRG-CNAG/CalliNGS-NF) | master, 9e7ebf0 (2021-08-25) | MPL-2.0 | GATK RNA-seq variant calling, one of the example pipelines in the 2017 Nextflow paper (Di Tommaso et al., Nature Biotechnology 35:316); one end-to-end CI run, no other tests. Its only tag, v1.0.0, is DSL1 and cannot run on any Nextflow from 22.12 on |

On the known-answer set (4,000 read pairs from four synthetic transcripts with no shared 31-mer), Salmon in rnaseq-nf returned 400, 800, 1,600 and 1,200 reads, the numbers drawn, with a 100% mapping rate. The pipeline's own CI checks only that the run exits 0.

## What it adds

- `conf/test.config` and `conf/slurm.config`: overlays applied with `-c`. The test overlay caps each task at one CPU and 2 GB, turns on `pipefail` in task shells and pulls amd64 images on arm64 hosts. The Slurm overlay turns queue, account, wall time and resource caps into parameters.
- `tests/nf-test/`: pipeline tests with known answers. The `-stub-run` test documents a gap: rnaseq-nf has no stub blocks, so `-stub-run` runs the real tools.
- `docs/lint/`: what `nextflow lint` 26.10.2 rejects in each pipeline, raw and counted.
- `nf-retrofit`, a small Python package: synthetic transcriptomes with known read counts, reads from any reference with known SNVs, checks of Salmon output and of VCFs against a truth set, lint summaries, and the run manifest and summary.
- `scripts/run_with_logs.sh`: a manifest before the run, logs and trace during, a summary after (`docs/logging.md`).
- `docs/findings/`: one short report per pipeline, written to be offered to its maintainers.

## Quick start

Needs Python 3.11 or later. CI runs the unit tests on Python 3.11 and 3.13, on Ubuntu and macOS.

```
git clone --recurse-submodules https://github.com/Daneshpajouh/nf-retrofit.git
cd nf-retrofit
python3 -m venv .venv && . .venv/bin/activate
python3 -m pip install -e '.[dev]'
make unit
```

```
41 passed in 0.99s
```

```
make nf-test        # needs Docker, Nextflow and nf-test
```

```
  Test 'four unique transcripts, 4,000 fragments' PASSED (15.7s)
  Test '-stub-run falls through to the real scripts (no stub blocks)' PASSED (13.1s)
SUCCESS: Executed 2 tests in 28.8s
```

`make nf-test` runs the rnaseq-nf tests; the output above is from an arm64 Mac. The CalliNGS-NF test needs Nextflow 22.04.5, so it runs in GitHub Actions, where the pipeline ran end to end on its bundled data and produced its VCF. It does not run on current Nextflow (see Findings below).

A logged run of rnaseq-nf on the known-answer data:

```
scripts/run_with_logs.sh runs/rnaseq_known examples/rnaseq-nf -profile docker -c conf/test.config \
    --reads "$PWD/tests/data/rnaseq_known/synthetic_{1,2}.fq.gz" \
    --transcriptome $PWD/tests/data/rnaseq_known/transcriptome.fa
```

```
[SUCCESS] completed=4 failed=0 cached=0
OK: 4 tasks, 0 failed, 25.3 s
```

## Findings so far

rnaseq-nf: Salmon's output is never published to `--outdir`; a relative `--transcriptome` path fails; CI checks only the exit status; no stub blocks; the image is amd64 only. CalliNGS-NF: it does not run on Nextflow 26.10.2 (top-level statements, duplicate input names, the removed `phase` operator), and the docker profile's user mapping is set outside the `docker` scope and ignored. It does run end to end on Nextflow 22.04.5: in GitHub Actions, `tests/nf-test/callings-nf` runs the pipeline on its bundled data, and the run finishes and produces its VCF. Details and line numbers in `docs/findings/`.

## Known limits

- `check-vcf` matches on site and allele. By default, extra calls are counted but do not fail the check; `--fail-on-extra` (strict mode) fails it when any PASS call has an allele the truth VCF lacks and lists those alleles. Genotype is compared only with `--compare-genotypes`, in either mode: it reads GT from the first sample column, lists each matched allele whose GT differs under `genotype_mismatches` and each match where either file has no usable GT (none, `./.`, or two records for the same allele that disagree) under `genotype_unknown`, apart from missed and extra calls, and fails the check on either. Phase is ignored unless `--phased` is added, and then compared only where both files give a phased GT. A multi-allelic record is read per allele as `bcftools norm -m -both` would split it.
- The published image is useful only for the Python CLI: it has no Docker client and none of `conf/`, `tests/` or `scripts/`.

## Layout

```
conf/                 test and Slurm overlays
docs/                 testing.md, logging.md, findings/, lint/
examples/             the two pipelines, as pinned submodules
scripts/              run_with_logs.sh
src/nf_retrofit simulators, checks, lint summary, run log
tests/unit            pytest
tests/nf-test         nf-test pipeline tests
tests/data            fixtures and the rnaseq-nf known-answer set
Dockerfile            Python package, Nextflow 24.04.4 and nf-test 0.9.5
```

The image is built in CI and pushed to `ghcr.io` by `.github/workflows/release.yml` when a `v*` tag is pushed.

MIT licence. The two example pipelines keep their own licences.
