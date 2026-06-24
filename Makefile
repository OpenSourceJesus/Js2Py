PYTHON ?= python3
# CURDIR is reliable with spaces; lastword(MAKEFILE_LIST) breaks on "Web Browser/..."
ROOT := $(CURDIR)

export PYTHONPATH := $(ROOT)

.PHONY: help test test-simple test-es6 test-es7 test-language test-all

help:
	@echo "Js2Py test targets:"
	@echo "  make test          Run quick integration tests (default)"
	@echo "  make test-simple   Run simple_test.py (ES5 + ES6 smoke tests)"
	@echo "  make test-es6      Run tests/test_es6.py"
	@echo "  make test-es7      Run tests/test_es7.py"
	@echo "  make test-language Run ES5.1 language suite (tests/run.py, slow)"
	@echo "  make test-all      Run quick tests and the language suite"

test: test-simple test-es6 test-es7
	@:

test-simple:
	PYTHONPATH="$(ROOT)" $(PYTHON) "$(ROOT)/simple_test.py"

test-es6:
	PYTHONPATH="$(ROOT)" $(PYTHON) "$(ROOT)/tests/test_es6.py"

test-es7:
	PYTHONPATH="$(ROOT)" $(PYTHON) "$(ROOT)/tests/test_es7.py"

test-language:
	@test -f "$(ROOT)/tests/node_failed.txt" || touch "$(ROOT)/tests/node_failed.txt"
	cd "$(ROOT)/tests" && PYTHONPATH="$(ROOT)" $(PYTHON) run.py

test-all: test test-language
