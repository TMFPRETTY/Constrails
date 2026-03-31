PYTHON ?= .venv/bin/python
PYTEST ?= $(PYTHON) -m pytest

.PHONY: test test-all doctor init-db serve version

test:
	$(PYTEST) -q tests

test-all:
	PYTHONPATH=src $(PYTEST) -q tests

doctor:
	PYTHONPATH=src $(PYTHON) -m constrail.cli doctor

init-db:
	PYTHONPATH=src $(PYTHON) -m constrail.cli init-db

serve:
	PYTHONPATH=src $(PYTHON) -m constrail.cli serve --host 127.0.0.1 --port 8011

version:
	PYTHONPATH=src $(PYTHON) -m constrail.cli version
