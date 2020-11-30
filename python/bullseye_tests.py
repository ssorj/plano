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

from plano import *

_test_project_dir = get_absolute_path("test-project")

class _test_project(working_dir):
    def __enter__(self):
        dir = super(_test_project, self).__enter__()
        copy(_test_project_dir, ".", inside=False)
        return dir

def _invoke(*args):
    command = PlanoCommand()
    command.main(["--verbose", "-f", join(_test_project_dir, "Planofile")] + list(args))

def open_test_session(session):
    if session.verbose:
        enable_logging(level="debug")

def test_target_build(session):
    with _test_project():
        _invoke("build")
        _invoke("build", "--prefix", "/usr/local")

def test_target_test(session):
    with _test_project():
        _invoke("test")
        _invoke("test", "--verbose")
        _invoke("test", "--list")
        _invoke("test", "--include", "test_hello", "--list")

def test_target_install(session):
    with _test_project():
        _invoke("build", "--prefix", "build")
        _invoke("install")
        _invoke("install", "--dest-dir", "staging")

def test_target_clean(session):
    with _test_project():
        _invoke("clean")
        _invoke("build")
        _invoke("clean")

def test_target_env(session):
    with _test_project():
        _invoke("env")

def test_target_modules(session):
    with _test_project():
        try:
            _invoke("modules", "--remote", "--recursive")
            assert False
        except PlanoException:
            pass
