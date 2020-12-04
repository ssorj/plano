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

import collections as _collections
import sys as _sys

from plano import *
from plano import _import_module

class _Project:
    def __init__(self):
        self.name = None
        self.source_dir = "python"
        self.extra_source_dirs = []
        self.build_dir = "build"
        self.test_modules = []

project = _Project()

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

@target(args=[Argument("clean_", option_name="clean", help="Clean before building"),
              Argument("prefix", help="The base path for installed files")])
def build(clean_=False, prefix=join(get_home_dir(), ".local")):
    assert project.name

    if clean_:
        clean()

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
        args=[Argument("include", metavar="PATTERN", help="Run only tests with names matching PATTERN"),
              Argument("verbose", help="Print detailed logging to the console"),
              Argument("list_", option_name="list", help="Print the test names and exit")])
def test(include=None, verbose=False, list_=False):
    from commandant import TestCommand

    with project_env():
        modules = [_import_module(x) for x in project.test_modules]
        # try:
        #     import importlib
        #     modules = [importlib.import_module(x) for x in project.test_modules]
        # except ImportError: # pragma: nocover
        #     modules = [__import__(x, fromlist=[""]) for x in project.test_modules]

        command = TestCommand(*modules)
        args = list()

        if list_:
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

_project_files = _collections.OrderedDict()

_project_files[".gitignore"] = """
*.pyc
__pycache__/
/build
/dist
/.coverage
/htmlcov
"""

_project_files["README.md"] = """
# {title}

## Dependencies
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

_description = """
Generate standard project files

Use one of the following filenames:

  {0}

Or use the special filename "all" to generate all of them.
""".format("\n  ".join(_project_files))

@target(help="Generate standard project files", description=_description,
        args=[Argument("filename", help="Which file to generate"),
              Argument("stdout", help="Print to stdout instead of writing the file directly")])
def generate(filename, stdout=False):
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
        exit("File '{0}' is not one of the options".format(filename))

    content = content.strip()
    content = content.format(title=project.name.capitalize(), name=project.name)

    if stdout:
        print(content)
    else:
        write(filename, content)
