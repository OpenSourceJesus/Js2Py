PYTHON ?= python3
# CURDIR is reliable with spaces; lastword(MAKEFILE_LIST) breaks on "Web Browser/..."
ROOT := $(CURDIR)

export PYTHONPATH := $(ROOT)

.PHONY: help test test-simple test-es-all test-es6 test-es7 test-es8 test-es9 test-es10 test-es11 test-es12 test-es13 test-es14 test-es15 test-es16 test-language test-all

help:
	@echo "Js2Py test targets:"
	@echo "  make test          Run quick integration tests (default)"
	@echo "  make test-simple   Run simple_test.py (ES5 + ES6 smoke tests)"
	@echo "  make test-es_      Run all tests/test_es*.py tests"
	@echo "  make test-es6      Run tests/test_es6.py"
	@echo "  make test-es7      Run tests/test_es7.py"
	@echo "  make test-es8      Run tests/test_es8.py"
	@echo "  make test-es9      Run tests/test_es9.py"
	@echo "  make test-es10     Run tests/test_es10.py"
	@echo "  make test-es11     Run tests/test_es11.py"
	@echo "  make test-es12     Run tests/test_es12.py"
	@echo "  make test-es13     Run tests/test_es13.py"
	@echo "  make test-es14     Run tests/test_es14.py"
	@echo "  make test-es15     Run tests/test_es15.py"
	@echo "  make test-es16     Run tests/test_es16.py"
	@echo "  make test-language Run ES5.1 language suite (tests/run.py, slow)"
	@echo "  make test-all      Run quick tests and the language suite"

test: test-simple test-es_
	@:

test-simple:
	PYTHONPATH="$(ROOT)" $(PYTHON) "$(ROOT)/simple_test.py"

test-es_: test-es6 test-es7 test-es8 test-es9 test-es10 test-es11 test-es12 test-es13 test-es14 test-es15 test-es16

test-es6:
	PYTHONPATH="$(ROOT)" $(PYTHON) "$(ROOT)/tests/test_es6.py"

test-es7:
	PYTHONPATH="$(ROOT)" $(PYTHON) "$(ROOT)/tests/test_es7.py"

test-es8:
	PYTHONPATH="$(ROOT)" $(PYTHON) "$(ROOT)/tests/test_es8.py"

test-es9:
	PYTHONPATH="$(ROOT)" $(PYTHON) "$(ROOT)/tests/test_es9.py"

test-es10:
	PYTHONPATH="$(ROOT)" $(PYTHON) "$(ROOT)/tests/test_es10.py"

test-es11:
	PYTHONPATH="$(ROOT)" $(PYTHON) "$(ROOT)/tests/test_es11.py"

test-es12:
	PYTHONPATH="$(ROOT)" $(PYTHON) "$(ROOT)/tests/test_es12.py"

test-es13:
	PYTHONPATH="$(ROOT)" $(PYTHON) "$(ROOT)/tests/test_es13.py"

test-es14:
	PYTHONPATH="$(ROOT)" $(PYTHON) "$(ROOT)/tests/test_es14.py"

test-es15:
	PYTHONPATH="$(ROOT)" $(PYTHON) "$(ROOT)/tests/test_es15.py"

test-es16:
	PYTHONPATH="$(ROOT)" $(PYTHON) "$(ROOT)/tests/test_es16.py"

test-language:
	@test -f "$(ROOT)/tests/node_failed.txt" || touch "$(ROOT)/tests/node_failed.txt"
	cd "$(ROOT)/tests" && PYTHONPATH="$(ROOT)" $(PYTHON) run.py

test-all: test test-language
