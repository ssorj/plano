#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

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
test:
	scripts/test-plano
#	python3 scripts/test-plano

.PHONY: big-test
big-test: test test-centos test-fedora test-ubuntu

.PHONY: test-centos
test-centos:
	sudo docker build -f scripts/test-centos.dockerfile -t plano-test-centos .
	sudo docker run plano-test-centos

.PHONY: test-fedora
test-fedora:
	sudo docker build -f scripts/test-fedora.dockerfile -t plano-test-fedora .
	sudo docker run plano-test-fedora

.PHONY: test-ubuntu
test-ubuntu:
	sudo docker build -f scripts/test-ubuntu.dockerfile -t plano-test-ubuntu .
	sudo docker run plano-test-ubuntu

.PHONY: update-%
update-%:
	curl "https://raw.githubusercontent.com/ssorj/$*/master/python/$*.py" -o python/$*.py
