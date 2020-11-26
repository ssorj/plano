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
        self.build_dir = "build"
        self.extra_dirs = []
        self.default_prefix = join(get_home_dir(), ".local")

project = _Project()

@target
def build(dest_dir="", prefix=None):
    assert project.name

    if prefix is None:
        prefix = project.default_prefix

    write_json(join(project.build_dir, "build.json"), {"prefix": prefix, "dest_dir": dest_dir})

    default_home = join(project.default_prefix, "lib", project.name)

    for path in find("bin", "*.in"):
        configure_file(path, join(project.build_dir, path[:-3]), {"default_home": default_home})

    for path in find("bin"):
        if path.endswith(".in"):
            continue

        copy(path, join(project.build_dir, path), inside=False, symlinks=False)

    for path in find("python", "*.py"):
        copy(path, join(project.build_dir, project.name, path), inside=False, symlinks=False)

    for dir_name in project.extra_dirs:
        for path in find(dir_name):
            copy(path, join(project.build_dir, project.name, path), inside=False, symlinks=False)

@target(requires=build)
def install():
    assert project.name
    assert is_dir(project.build_dir)

    build = read_json(join(project.build_dir, "build.json"))
    prefix = build["dest_dir"] + build["prefix"]

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
        args=(Argument("remote", help="Get remote commits"),
              Argument("recursive", help="Update modules recursively")))
def modules(remote=False, recursive=False):
    command = "git submodule update --init".split()

    if remote:
        command.append("--remote")

    if recursive:
        command.append("--recursive")

    run(" ".join(command))

@target(help="Generate shell settings for the project environment")
def env():
    assert project.name

    home_var = "{0}_HOME".format(project.name.upper().replace("-", "_"))

    print("export {0}=$PWD/build/{1}".format(home_var, project.name))
    print("export PATH=$PWD/build/bin:$PWD/scripts:$PATH")

    python_path = [
        "${0}/python".format(home_var),
        "$PWD/python",
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
            home_var: get_absolute_path("build/{0}".format(project.name)),
            "PATH": get_absolute_path("build/bin") + ":" + ENV["PATH"],
            "PYTHONPATH": get_absolute_path("build/{0}/python".format(project.name)),
        }

        super(project_env, self).__init__(**env)
