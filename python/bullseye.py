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

import sys as _sys

from plano import *

class _Project:
    def __init__(self):
        self.name = None
        self.source_dir = "python"
        self.extra_source_dirs = []
        self.build_dir = "build"
        self.test_modules = []

project = _Project()

@target(args=[Argument("prefix", help="The base path for installed files")])
def build(prefix=join(get_home_dir(), ".local")):
    assert project.name

    write_json(join(project.build_dir, "build.json"), {"prefix": prefix})

    default_home = join(prefix, "lib", project.name)

    for path in find("bin", "*.in"):
        configure_file(path, join(project.build_dir, path[:-3]), {"default_home": default_home})

    for path in find("bin"):
        if path.endswith(".in"):
            continue

        copy(path, join(project.build_dir, path), inside=False, symlinks=False)

    for path in find(project.source_dir, "*.py"):
        copy(path, join(project.build_dir, project.name, path), inside=False, symlinks=False)

    for dir_name in project.extra_source_dirs:
        for path in find(dir_name):
            copy(path, join(project.build_dir, project.name, path), inside=False, symlinks=False)

@target(requires=build,
        args=[Argument("include", help="Run only tests with names matching PATTERN", metavar="PATTERN"),
              Argument("verbose", help="Print detailed logging to the console"),
              Argument("list", help="Print the test names and exit")])
def test(include=None, verbose=False, list=False):
    from commandant import TestCommand

    with project_env():
        try:
            import importlib
            modules = [importlib.import_module(x) for x in project.test_modules]
        except ImportError: # pragma: nocover
            modules = [__import__(x, fromlist=[""]) for x in project.test_modules]

        command = TestCommand(*modules)
        args = []

        if list:
            args.append("--list")

        if verbose:
            args.append("--verbose")

        if include is not None:
            args.append(include)

        command.main(args)

@target(requires=build,
        args=[Argument("dest_dir", help="A path prepended to installed files")])
def install(dest_dir=""):
    assert project.name
    assert is_dir(project.build_dir)

    build = read_json(join(project.build_dir, "build.json"))
    prefix = dest_dir + build["prefix"]

    for path in find(join(project.build_dir, "bin")):
        copy(path, join(prefix, path[6:]), inside=False, symlinks=False)

    for path in find(join(project.build_dir, project.name)):
        copy(path, join(prefix, "lib", path[6:]), inside=False, symlinks=False)

@target
def clean():
    remove(project.build_dir)

    for path in find(".", "__pycache__"):
        remove(path)

    for path in find(".", "*.pyc"):
        remove(path)

@target(help="Update Git submodules",
        args=[Argument("remote", help="Get remote commits"),
              Argument("recursive", help="Update modules recursively")])
def modules(remote=False, recursive=False):
    check_program("git")

    command = "git submodule update --init".split()

    if remote:
        command.append("--remote")

    if recursive:
        command.append("--recursive")

    run(" ".join(command))

@target(help="Generate shell settings for the project environment",
        description="Source the output from your shell.  For example:\n\n\n  $ source <(plano env)")
def env():
    assert project.name

    home_var = "{0}_HOME".format(project.name.upper().replace("-", "_"))
    home_dir = join("$PWD", project.build_dir, project.name)

    print("export {0}={1}".format(home_var, home_dir))
    print("export PATH={0}:$PATH".format(join("$PWD", project.build_dir, "bin")))

    python_path = [
        join(home_dir, project.source_dir),
        join("$PWD", project.source_dir),
    ]

    try:
        python_path.append(ENV["PYTHONPATH"])
    except KeyError: # pragma: nocover
        pass

    python_path.extend(_sys.path)

    print("export PYTHONPATH={0}".format(":".join(python_path)))

class project_env(working_env):
    def __init__(self):
        assert project.name

        home_var = "{0}_HOME".format(project.name.upper().replace("-", "_"))

        env = {
            home_var: get_absolute_path(join(project.build_dir, project.name)),
            "PATH": get_absolute_path(join(project.build_dir, "bin")) + ":" + ENV["PATH"],
            "PYTHONPATH": get_absolute_path(join(project.build_dir, project.name, project.source_dir)),
        }

        super(project_env, self).__init__(**env)
