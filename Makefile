PYTHON ?= python3
NF_TEST ?= nf-test

.PHONY: test unit nf-test lint-reports

test: unit nf-test

unit:
	PYTHONPATH=src $(PYTHON) -m pytest -q

nf-test:
	$(NF_TEST) test tests/nf-test/rnaseq-nf

lint-reports:
	for p in rnaseq-nf callings-nf; do \
	  nextflow lint examples/$$p > docs/lint/$$p.txt 2>&1 || true; \
	  PYTHONPATH=src $(PYTHON) -m nf_retrofit lint-report docs/lint/$$p.txt --title "nextflow lint: $$p" > docs/lint/$$p.md; \
	done
