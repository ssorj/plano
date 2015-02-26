.PHONY: default help build install test clean dist devel

DESTDIR := ""
PREFIX := /usr/local

default: devel

help:
	@echo "build          Build the code"
	@echo "install        Install the code"
	@echo "test           Test the code"
	@echo "clean          Remove transient files from the checkout"
	@echo "dist           Create a release artifact"
	@echo "devel          Clean, build, install, and test for"
	@echo "               this development session [default]"

build:
	./setup.py build

install: build
	./setup.py install --prefix ${DESTDIR}${PREFIX}

test: install
	./setup.py check

clean:
	find python -type f -name \*.pyc -delete
	./setup.py clean --all
	rm -rf install
	rm -rf dist

dist:
	./setup.py sdist

devel: PREFIX := install
devel: clean test
