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

from bullseye import *

_test_project_dir = get_absolute_path("test-project")
_result_file = "build/result.json"

class _test_project(working_dir):
    def __enter__(self):
        dir = super(_test_project, self).__enter__()
        copy(_test_project_dir, ".", inside=False)
        return dir

def _invoke(*args):
    PlanoCommand().main(["--verbose", "-f", join(_test_project_dir, "Planofile")] + list(args))

def open_test_session(session):
    if session.verbose:
        enable_logging(level="debug")

def test_project_env(session):
    project.name = "alphabet"

    with project_env():
        assert "ALPHABET_HOME" in ENV, ENV

def test_configure_file(session):
    with working_dir():
        input_file = write("zeta-file", "X@replace-me@X")
        output_file = configure_file(input_file, "zeta-file", {"replace-me": "Y"})
        output = read(output_file)
        assert output == "XYX", output

def test_command_build(session):
    with _test_project():
        _invoke("build")

        result = read_json(_result_file)
        assert result["built"], result

        assert is_file("build/bin/chucker")
        assert is_file("build/bin/chucker-test")
        assert is_file("build/chucker/python/chucker.py")
        assert is_file("build/chucker/python/chucker_tests.py")

        result = read("build/bin/chucker").strip()
        assert result.endswith(".local/lib/chucker"), result

        result = read_json("build/build.json")
        assert result["prefix"].endswith(".local"), result

        _invoke("build", "--clean", "--prefix", "/usr/local")

        result = read("build/bin/chucker").strip()
        assert result == "/usr/local/lib/chucker", result

        result = read_json("build/build.json")
        assert result["prefix"] == ("/usr/local"), result

def test_command_test(session):
    with _test_project():
        _invoke("test")

        result = read_json(_result_file)
        assert result["tested"], result

        _invoke("test", "--verbose")
        _invoke("test", "--list")
        _invoke("test", "--include", "test_hello")
        _invoke("test", "--clean")

def test_command_install(session):
    with _test_project():
        _invoke("install", "--staging-dir", "staging")

        result = read_json(_result_file)
        assert result["installed"], result

        assert is_dir("staging"), list_dir()

    with _test_project():
        assert not exists("build"), list_dir()

        _invoke("build", "--prefix", "/opt/local")
        _invoke("install", "--staging-dir", "staging")

        assert is_dir("staging/opt/local"), list_dir("staging")

def test_command_clean(session):
    with _test_project():
        _invoke("build")

        assert is_dir("build")

        _invoke("clean")

        assert not is_dir("build")

def test_command_env(session):
    with _test_project():
        _invoke("env")
        _invoke("env", "--undo")

def test_command_modules(session):
    with _test_project():
        try:
            _invoke("modules", "--remote", "--recursive")
            assert False
        except PlanoException:
            pass

def test_command_generate(session):
    with _test_project():
        _invoke("generate", "README.md")

        assert exists("README.md"), list_dir()

        _invoke("generate", "--stdout", "LICENSE.txt")

        assert not exists("LICENSE.txt"), list_dir()

        _invoke("generate", "all")

        assert exists(".gitignore"), list_dir()
        assert exists("LICENSE.txt"), list_dir()
        assert exists("VERSION.txt"), list_dir()

        try:
            _invoke("generate", "no-such-file")
            assert False
        except SystemExit:
            pass
