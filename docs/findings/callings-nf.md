# CalliNGS-NF: findings

Pinned at master commit 9e7ebf0 (2021-08-25). The only tag, v1.0.0, is DSL1 (`file genome from genome_file` at `main.nf:71`), which Nextflow removed in 22.12, so it cannot run at all; master is the DSL2 rewrite. Checked with Nextflow 26.10.2 on 2026-10-19. Written to be offered to the maintainers as an issue.

## It does not run on current Nextflow

With the default parser the script fails to compile: `log.info` sits at the top level of `main.nf:41`, and `RNASEQ_GATK_SPLITNCIGAR` and the next process each declare two inputs named `index` (`modules.nf:159` and `161`, `189` and `191`). `nextflow lint` reports 3 errors and 5 warnings (`docs/lint/callings-nf.md`).

With the legacy parser (`NXF_SYNTAX_PARSER=v1`) the run gets further and stops before any task: `Unknown method invocation 'phase' on channel type` at `modules.nf:371`, in `group_per_sample`. `phase` has been removed; `join` on the sample key can replace it here, because both channels carry the sample ID first.

The pipeline's CI installs whatever `get.nextflow.io` serves, without a version pin, so a CI run today would hit both errors. Pinning `NXF_VER` in CI, and fixing the three items above, would keep the pipeline runnable.

## The docker profile's user mapping is ignored

The `docker` profile sets `runOptions = '-u $(id -u):$(id -g)'` (`nextflow.config:14`) at the top level instead of `docker.runOptions`. Nextflow reads it as an unrelated setting, so containers run as root and leave root-owned files in `work/` on Linux hosts.

## Duplicate input names

Two processes take both the genome index and a BAM index as `path index` (`modules.nf:159` and `161`, `189` and `191`). Neither script refers to `$index`, and the legacy parser accepts the duplicate, so it has no visible effect today; the strict parser rejects it. Renaming them (`genome_index`, `bam_index`) clears the error without changing behaviour.

## What this kit could not run here

The full pipeline did not run on this Mac. Pinning an older Nextflow with `NXF_VER=24.04.4` failed with the Homebrew launcher before starting. CI runs `tests/nf-test/callings-nf/bundled_data.nf.test` on ubuntu-latest with the official launcher, Java 17, `NXF_VER=24.04.4` and the legacy parser.
