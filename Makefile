export PYTHONPATH := python:${PYTHONPATH}

DESTDIR := ""
PREFIX := ${HOME}/.local

.PHONY: default
default: build

help:
	@echo "build          Build the code"
	@echo "test           Run the tests"
	@echo "install        Install the code"
	@echo "clean          Remove transient files from the checkout"

.PHONY: build
build:
	./setup.py build
	./setup.py check

.PHONY: install
install: build
	./setup.py install --root ${DESTDIR} --prefix ${PREFIX}

.PHONY: clean
clean:
	find python -type f -name \*.pyc -delete
	rm -rf dist
	./setup.py clean --all

.PHONY: test
test: devel
	scripts/test-plano
