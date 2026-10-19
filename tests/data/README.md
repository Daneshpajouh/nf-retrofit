# Test fixtures

All files are synthetic and small.

`rnaseq_known/` is the known-answer set for rnaseq-nf, made with
`nf-legacy-testkit transcripts --counts tx_a=400,tx_b=800,tx_c=1600,tx_d=1200 --seed 7`:
four random 1,500-base transcripts that share no 31-mer, and 4,000 read pairs (2 x 75 bases,
inserts around 250) drawn in those numbers. `expected.json` holds the counts and TPMs
(100,000, 200,000, 400,000 and 300,000).

| File | What it exercises |
|---|---|
| `calls_padded.vcf`, `truth_three.vcf` | a deletion written with an extra trailing base, a symbolic `<*>` allele, a non-PASS call |
| `quant_close.sf`, `expected_counts.json` | Salmon counts 0.4% and 0.5% off the expected values |
| `lint_two_errors.txt` | two entries cut from the real `nextflow lint` output for CalliNGS-NF |
| `trace_one_failed.tsv` | a Nextflow trace with one COMPLETED task and one FAILED with exit 127 |
