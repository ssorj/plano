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
def build():
    assert project.name

    # XXX Make these settable
    dest_dir = ""
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

    for path in find(join(project.build_dir, "bin")):
        copy(path, join(f"{build['dest_dir']}{build['prefix']}", path[6:]), inside=False, symlinks=False)

    for path in find(join(project.build_dir, project.name)):
        copy(path, join(f"{build['dest_dir']}{build['prefix']}", "lib", path[6:]), inside=False, symlinks=False)

@target
def clean():
    remove(project.build_dir)

    for path in find(".", "__pycache__"):
        remove(path)

    for path in find(".", "*.pyc"):
        remove(path)

@target(help="Update Git submodules")
def modules():
    run("git submodule update --init --remote --recursive")

@target(help="Generate shell settings for the project environment")
def env():
    assert project.name

    home_var = f"{project.name.upper()}_HOME"

    print(f"export {home_var}=$PWD/build/{project.name}")
    print("export PATH=$PWD/build/bin:$PWD/scripts:$PATH")

    if "PYTHONPATH" in ENV:
        print(f"export PYTHONPATH=${home_var}/python:$PWD/python:{ENV['PYTHONPATH']}")
    else:
        print(f"export PYTHONPATH=${home_var}/python:$PWD/python:{':'.join(_sys.path)}")

class project_env(working_env):
    def __init__(self):
        assert project.name

        env = {
            f"{project.name.upper()}_HOME": get_absolute_path(f"build/{project.name}"),
            "PATH": get_absolute_path("build/bin") + ":" + ENV["PATH"],
            "PYTHONPATH": get_absolute_path(f"build/{project.name}/python"),
        }

        super().__init__(**env)
