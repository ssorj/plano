export PYTHONPATH := $(shell scripts/gen-python3-path install):${PYTHONPATH}

DESTDIR := ""
PREFIX := ${HOME}/.local

.PHONY: default
default: devel

help:
	@echo "build          Build the code"
	@echo "install        Install the code"
	@echo "clean          Remove transient files from the checkout"
	@echo "devel          Clean, build, install, and test inside"
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
	scripts/test-plano
	./setup.py check
