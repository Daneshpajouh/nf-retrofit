PYTHON ?= python3
NF_TEST ?= nf-test

.PHONY: test unit nf-test lint-reports

test: unit nf-test

unit:
	PYTHONPATH=src $(PYTHON) -m pytest -q

nf-test:
	$(NF_TEST) test tests/nf-test/rnaseq-nf

# lint exits 1 when it finds errors, so its status is kept and checked by lint-report
lint-reports:
	set -e; for p in rnaseq-nf callings-nf; do \
	  status=0; nextflow lint examples/$$p > docs/lint/$$p.txt 2>&1 || status=$$?; \
	  PYTHONPATH=src $(PYTHON) -m nf_retrofit lint-report docs/lint/$$p.txt --title "nextflow lint: $$p" \
	    --exit-code $$status > docs/lint/$$p.md; \
	done
