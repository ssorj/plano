export PYTHONPATH := $(shell python3 scripts/python-path install):${PYTHONPATH}

DESTDIR := ""
PREFIX := ${HOME}/.local

.PHONY: default
default: devel

help:
	@echo "build          Build the code"
	@echo "test           Run the tests"
	@echo "install        Install the code"
	@echo "clean          Remove transient files from the checkout"
	@echo "devel          Clean, build, install, and smoke test inside"
	@echo "               this checkout [default]"

.PHONY: build
build:
	./setup.py build

.PHONY: install
install: build
	./setup.py install --prefix ${DESTDIR}${PREFIX}

.PHONY: clean
clean:
	find python -type f -name \*.pyc -delete
	./setup.py clean --all
	rm -rf install

.PHONY: devel
devel: PREFIX := ${PWD}/install
devel: clean install
	./setup.py check

.PHONY: test
test: devel
	scripts/test-plano
