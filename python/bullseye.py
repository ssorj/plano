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

from __future__ import print_function

import collections as _collections
import fnmatch as _fnmatch
import os as _os
import shutil as _shutil
import sys as _sys

from plano import *

class _Project:
    def __init__(self):
        self.name = None
        self.source_dir = "python"
        self.included_modules = ["*"]
        self.excluded_modules = ["plano", "bullseye"]
        self.data_dirs = []
        self.build_dir = "build"
        self.test_modules = []

project = _Project()

_default_prefix = join(get_home_dir(), ".local")

def check_project():
    assert project.name
    assert project.source_dir
    assert project.build_dir

class project_env(working_env):
    def __init__(self):
        check_project()

        home_var = "{0}_HOME".format(project.name.upper().replace("-", "_"))

        env = {
            home_var: get_absolute_path(join(project.build_dir, project.name)),
            "PATH": get_absolute_path(join(project.build_dir, "bin")) + ":" + ENV["PATH"],
            "PYTHONPATH": get_absolute_path(join(project.build_dir, project.name, project.source_dir)),
        }

        super(project_env, self).__init__(**env)

def configure_file(input_file, output_file, substitutions, quiet=False):
    notice("Configuring '{0}' for output '{1}'", input_file, output_file)

    content = read(input_file)

    for name, value in substitutions.items():
        content = content.replace("@{0}@".format(name), value)

    write(output_file, content)

    _shutil.copymode(input_file, output_file)

    return output_file

_prefix_arg = CommandArgument("prefix", help="The base path for installed files", default=_default_prefix)
_clean_arg = CommandArgument("clean_", help="Clean before starting", display_name="clean")
_verbose_arg = CommandArgument("verbose", help="Print detailed logging to the console")

@command(args=(_prefix_arg, _clean_arg))
def build(app, prefix=None, clean_=False):
    check_project()

    if clean_:
        clean(app)

    build_file = join(project.build_dir, "build.json")
    build_data = {}

    if exists(build_file):
        build_data = read_json(build_file)

    mtime = _os.stat(project.source_dir).st_mtime

    for path in find(project.source_dir):
        mtime = max(mtime, _os.stat(path).st_mtime)

    if prefix is None:
        prefix = build_data.get("prefix", _default_prefix)

    new_build_data = {"prefix": prefix, "mtime": mtime}

    debug("Existing build data: {0}", pformat(build_data))
    debug("New build data:      {0}", pformat(new_build_data))

    if build_data == new_build_data:
        debug("Already built")
        return

    write_json(build_file, new_build_data)

    default_home = join(prefix, "lib", project.name)

    for path in find("bin", "*.in"):
        configure_file(path, join(project.build_dir, path[:-3]), {"default_home": default_home})

    for path in find("bin", exclude="*.in"):
        copy(path, join(project.build_dir, path), inside=False, symlinks=False)

    for path in find(project.source_dir, "*.py"):
        module_name = get_name_stem(path)
        included = any([_fnmatch.fnmatchcase(module_name, x) for x in project.included_modules])
        excluded = any([_fnmatch.fnmatchcase(module_name, x) for x in project.excluded_modules])

        if included and not excluded:
            copy(path, join(project.build_dir, project.name, path), inside=False, symlinks=False)

    for dir_name in project.data_dirs:
        for path in find(dir_name):
            copy(path, join(project.build_dir, project.name, path), inside=False, symlinks=False)

@command(args=(CommandArgument("include", help="Run only tests with names matching PATTERN", metavar="PATTERN"),
               CommandArgument("exclude", help="Do not run tests with names matching PATTERN", metavar="PATTERN"),
               CommandArgument("enable", help="Enable disabled tests matching PATTERN", metavar="PATTERN"),
               CommandArgument("list_", help="Print the test names and exit", display_name="list"),
               _verbose_arg, _clean_arg))
def test(app, include="*", exclude=None, enable=None, list_=False, verbose=False, clean_=False):
    check_project()

    if clean_:
        clean(app)

    if not list_:
        build(app)

    with project_env():
        from plano import _import_module
        modules = [_import_module(x) for x in project.test_modules]

        if not modules: # pragma: nocover
            notice("No tests found")
            return

        args = list()

        if list_:
            print_tests(modules)
            return

        exclude = nvl(exclude, ())
        enable = nvl(enable, ())

        run_tests(modules, include=include, exclude=exclude, enable=enable, verbose=verbose)

@command(args=(CommandArgument("staging_dir", help="A path prepended to installed files"),
               _prefix_arg, _clean_arg))
def install(app, staging_dir="", prefix=None, clean_=False):
    check_project()

    build(app, prefix=prefix, clean_=clean_)

    assert is_dir(project.build_dir), list_dir()

    build_file = join(project.build_dir, "build.json")
    build_data = read_json(build_file)
    build_prefix = project.build_dir + "/"
    install_prefix = staging_dir + build_data["prefix"]

    for path in find(join(project.build_dir, "bin")):
        copy(path, join(install_prefix, remove_prefix(path, build_prefix)), inside=False, symlinks=False)

    for path in find(join(project.build_dir, project.name)):
        copy(path, join(install_prefix, "lib", remove_prefix(path, build_prefix)), inside=False, symlinks=False)

@command
def clean(app):
    check_project()

    remove(project.build_dir)
    remove(find(".", "__pycache__"))
    remove(find(".", "*.pyc"))

@command(args=(CommandArgument("remote", help="Get remote commits"),
               CommandArgument("recursive", help="Update modules recursively")))
def modules(app, remote=False, recursive=False):
    """Update Git submodules"""

    check_program("git")

    command = ["git", "submodule", "update", "--init"]

    if remote:
        command.append("--remote")

    if recursive:
        command.append("--recursive")

    run(command)

@command(args=(CommandArgument("undo", help="Generate settings that restore the previous environment"),))
def env(app, undo=False):
    """
    Generate shell settings for the project environment

    To apply the settings, source the output from your shell:

        $ source <(plano env)
    """

    check_project()

    project_dir = get_current_dir() # XXX Needs some checking
    home_var = "{0}_HOME".format(project.name.upper().replace("-", "_"))
    old_home_var = "OLD_{0}".format(home_var)
    home_dir = join(project_dir, project.build_dir, project.name)

    if undo:
        print("[[ ${0} ]] && export {1}=${2} && unset {3}".format(old_home_var, home_var, old_home_var, old_home_var))
        print("[[ $OLD_PATH ]] && export PATH=$OLD_PATH && unset OLD_PATH")
        print("[[ $OLD_PYTHONPATH ]] && export PYTHONPATH=$OLD_PYTHONPATH && unset OLD_PYTHONPATH")

        return

    print("[[ ${0} ]] && export {1}=${2}".format(home_var, old_home_var, home_var))
    print("[[ $PATH ]] && export OLD_PATH=$PATH")
    print("[[ $PYTHONPATH ]] && export OLD_PYTHONPATH=$PYTHONPATH")

    print("export {0}={1}".format(home_var, home_dir))

    path = [
        join(project_dir, project.build_dir, "bin"),
        ENV.get("PATH", ""),
    ]

    print("export PATH={0}".format(join_path_var(*path)))

    python_path = [
        join(home_dir, project.source_dir),
        join(project_dir, project.source_dir),
        ENV.get("PYTHONPATH", ""),
    ]

    print("export PYTHONPATH={0}".format(join_path_var(*python_path)))

_project_files = _collections.OrderedDict()

_project_files[".gitignore"] = """
*.pyc
__pycache__/
/build
"""

_project_files["README.md"] = """
# {project_title}

[![main](https://github.com/ssorj/{project_name}/workflows/main/badge.svg)](https://github.com/ssorj/{project_name}/actions?query=workflow%3Amain)

## Project commands

Once you have set up the project, you can use the `./plano` command in
the root of the project to perform project tasks.  It accepts a
subcommand.  Use `./plano --help` to list the available commands.
"""

_project_files["LICENSE.txt"] = """
Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      "Licensor" shall mean the copyright owner or entity authorized by
      the copyright owner that is granting the License.

      "Legal Entity" shall mean the union of the acting entity and all
      other entities that control, are controlled by, or are under common
      control with that entity. For the purposes of this definition,
      "control" means (i) the power, direct or indirect, to cause the
      direction or management of such entity, whether by contract or
      otherwise, or (ii) ownership of fifty percent (50%) or more of the
      outstanding shares, or (iii) beneficial ownership of such entity.

      "You" (or "Your") shall mean an individual or Legal Entity
      exercising permissions granted by this License.

      "Source" form shall mean the preferred form for making modifications,
      including but not limited to software source code, documentation
      source, and configuration files.

      "Object" form shall mean any form resulting from mechanical
      transformation or translation of a Source form, including but
      not limited to compiled object code, generated documentation,
      and conversions to other media types.

      "Work" shall mean the work of authorship, whether in Source or
      Object form, made available under the License, as indicated by a
      copyright notice that is included in or attached to the work
      (an example is provided in the Appendix below).

      "Derivative Works" shall mean any work, whether in Source or Object
      form, that is based on (or derived from) the Work and for which the
      editorial revisions, annotations, elaborations, or other modifications
      represent, as a whole, an original work of authorship. For the purposes
      of this License, Derivative Works shall not include works that remain
      separable from, or merely link (or bind by name) to the interfaces of,
      the Work and Derivative Works thereof.

      "Contribution" shall mean any work of authorship, including
      the original version of the Work and any modifications or additions
      to that Work or Derivative Works thereof, that is intentionally
      submitted to Licensor for inclusion in the Work by the copyright owner
      or by an individual or Legal Entity authorized to submit on behalf of
      the copyright owner. For the purposes of this definition, "submitted"
      means any form of electronic, verbal, or written communication sent
      to the Licensor or its representatives, including but not limited to
      communication on electronic mailing lists, source code control systems,
      and issue tracking systems that are managed by, or on behalf of, the
      Licensor for the purpose of discussing and improving the Work, but
      excluding communication that is conspicuously marked or otherwise
      designated in writing by the copyright owner as "Not a Contribution."

      "Contributor" shall mean Licensor and any individual or Legal Entity
      on behalf of whom a Contribution has been received by Licensor and
      subsequently incorporated within the Work.

   2. Grant of Copyright License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      copyright license to reproduce, prepare Derivative Works of,
      publicly display, publicly perform, sublicense, and distribute the
      Work and such Derivative Works in Source or Object form.

   3. Grant of Patent License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      (except as stated in this section) patent license to make, have made,
      use, offer to sell, sell, import, and otherwise transfer the Work,
      where such license applies only to those patent claims licensable
      by such Contributor that are necessarily infringed by their
      Contribution(s) alone or by combination of their Contribution(s)
      with the Work to which such Contribution(s) was submitted. If You
      institute patent litigation against any entity (including a
      cross-claim or counterclaim in a lawsuit) alleging that the Work
      or a Contribution incorporated within the Work constitutes direct
      or contributory patent infringement, then any patent licenses
      granted to You under this License for that Work shall terminate
      as of the date such litigation is filed.

   4. Redistribution. You may reproduce and distribute copies of the
      Work or Derivative Works thereof in any medium, with or without
      modifications, and in Source or Object form, provided that You
      meet the following conditions:

      (a) You must give any other recipients of the Work or
          Derivative Works a copy of this License; and

      (b) You must cause any modified files to carry prominent notices
          stating that You changed the files; and

      (c) You must retain, in the Source form of any Derivative Works
          that You distribute, all copyright, patent, trademark, and
          attribution notices from the Source form of the Work,
          excluding those notices that do not pertain to any part of
          the Derivative Works; and

      (d) If the Work includes a "NOTICE" text file as part of its
          distribution, then any Derivative Works that You distribute must
          include a readable copy of the attribution notices contained
          within such NOTICE file, excluding those notices that do not
          pertain to any part of the Derivative Works, in at least one
          of the following places: within a NOTICE text file distributed
          as part of the Derivative Works; within the Source form or
          documentation, if provided along with the Derivative Works; or,
          within a display generated by the Derivative Works, if and
          wherever such third-party notices normally appear. The contents
          of the NOTICE file are for informational purposes only and
          do not modify the License. You may add Your own attribution
          notices within Derivative Works that You distribute, alongside
          or as an addendum to the NOTICE text from the Work, provided
          that such additional attribution notices cannot be construed
          as modifying the License.

      You may add Your own copyright statement to Your modifications and
      may provide additional or different license terms and conditions
      for use, reproduction, or distribution of Your modifications, or
      for any such Derivative Works as a whole, provided Your use,
      reproduction, and distribution of the Work otherwise complies with
      the conditions stated in this License.

   5. Submission of Contributions. Unless You explicitly state otherwise,
      any Contribution intentionally submitted for inclusion in the Work
      by You to the Licensor shall be under the terms and conditions of
      this License, without any additional terms or conditions.
      Notwithstanding the above, nothing herein shall supersede or modify
      the terms of any separate license agreement you may have executed
      with Licensor regarding such Contributions.

   6. Trademarks. This License does not grant permission to use the trade
      names, trademarks, service marks, or product names of the Licensor,
      except as required for reasonable and customary use in describing the
      origin of the Work and reproducing the content of the NOTICE file.

   7. Disclaimer of Warranty. Unless required by applicable law or
      agreed to in writing, Licensor provides the Work (and each
      Contributor provides its Contributions) on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
      implied, including, without limitation, any warranties or conditions
      of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
      PARTICULAR PURPOSE. You are solely responsible for determining the
      appropriateness of using or redistributing the Work and assume any
      risks associated with Your exercise of permissions under this License.

   8. Limitation of Liability. In no event and under no legal theory,
      whether in tort (including negligence), contract, or otherwise,
      unless required by applicable law (such as deliberate and grossly
      negligent acts) or agreed to in writing, shall any Contributor be
      liable to You for damages, including any direct, indirect, special,
      incidental, or consequential damages of any character arising as a
      result of this License or out of the use or inability to use the
      Work (including but not limited to damages for loss of goodwill,
      work stoppage, computer failure or malfunction, or any and all
      other commercial damages or losses), even if such Contributor
      has been advised of the possibility of such damages.

   9. Accepting Warranty or Additional Liability. While redistributing
      the Work or Derivative Works thereof, You may choose to offer,
      and charge a fee for, acceptance of support, warranty, indemnity,
      or other liability obligations and/or rights consistent with this
      License. However, in accepting such obligations, You may act only
      on Your own behalf and on Your sole responsibility, not on behalf
      of any other Contributor, and only if You agree to indemnify,
      defend, and hold each Contributor harmless for any liability
      incurred by, or claims asserted against, such Contributor by reason
      of your accepting any such warranty or additional liability.

   END OF TERMS AND CONDITIONS

   APPENDIX: How to apply the Apache License to your work.

      To apply the Apache License to your work, attach the following
      boilerplate notice, with the fields enclosed by brackets "{{}}"
      replaced with your own identifying information. (Don't include
      the brackets!)  The text should be enclosed in the appropriate
      comment syntax for the file format. We also recommend that a
      file or class name and description of purpose be included on the
      same "printed page" as the copyright notice for easier
      identification within third-party archives.

   Copyright {{yyyy}} {{name of copyright owner}}

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

_project_files["VERSION.txt"] = """
0.1.0-SNAPSHOT
"""

@command(args=(CommandArgument("filename", help="Which file to generate"),
               CommandArgument("stdout", help="Print to stdout instead of writing the file directly")))
def generate(app, filename, stdout=False):
    """
    Generate standard project files

    Use one of the following filenames:

        .gitignore
        README.md
        LICENSE.txt
        VERSION.txt

    Or use the special filename "all" to generate all of them.
    """

    assert project.name

    if filename == "all":
        for name in _project_files:
            _generate_file(name, stdout)
    else:
        _generate_file(filename, stdout)

def _generate_file(filename, stdout):
    try:
        content = _project_files[filename]
    except KeyError:
        exit("File {0} is not one of the options".format(repr(filename)))

    content = content.lstrip()
    content = content.format(project_title=project.name.capitalize(), project_name=project.name)

    if stdout:
        print(content, end="")
    else:
        write(filename, content)
