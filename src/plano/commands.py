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

from .main import *
from .main import _capitalize_help

import argparse as _argparse
import importlib as _importlib
import inspect as _inspect
import os as _os
import sys as _sys

class PlanoTestCommand(BaseCommand):
    def __init__(self, test_modules=[]):
        super(PlanoTestCommand, self).__init__()

        self.test_modules = test_modules

        if _inspect.ismodule(self.test_modules):
            self.test_modules = [self.test_modules]

        self.parser = BaseArgumentParser()
        self.parser.add_argument("include", metavar="PATTERN", nargs="*", default=["*"],
                                 help="Run tests with names matching PATTERN (default '*', all tests)")
        self.parser.add_argument("-e", "--exclude", metavar="PATTERN", action="append", default=[],
                                 help="Do not run tests with names matching PATTERN (repeatable)")
        self.parser.add_argument("-m", "--module", action="append", default=[],
                                 help="Collect tests from MODULE (repeatable)")
        self.parser.add_argument("-l", "--list", action="store_true",
                                 help="Print the test names and exit")
        self.parser.add_argument("--enable", metavar="PATTERN", action="append", default=[],
                                 help=_argparse.SUPPRESS)
        self.parser.add_argument("--unskip", metavar="PATTERN", action="append", default=[],
                                 help="Run skipped tests matching PATTERN (repeatable)")
        self.parser.add_argument("--timeout", metavar="SECONDS", type=int, default=300,
                                 help="Fail any test running longer than SECONDS (default 300)")
        self.parser.add_argument("--fail-fast", action="store_true",
                                 help="Exit on the first failure encountered in a test run")
        self.parser.add_argument("--iterations", metavar="COUNT", type=int, default=1,
                                 help="Run the tests COUNT times (default 1)")

    def parse_args(self, args):
        return self.parser.parse_args(args)

    def init(self, args):
        self.list_only = args.list
        self.include_patterns = args.include
        self.exclude_patterns = args.exclude
        self.enable_patterns = args.enable
        self.unskip_patterns = args.unskip
        self.timeout = args.timeout
        self.fail_fast = args.fail_fast
        self.iterations = args.iterations

        try:
            for name in args.module:
                self.test_modules.append(_importlib.import_module(name))
        except ImportError as e:
            raise PlanoError(e)

    def run(self):
        if self.list_only:
            print_tests(self.test_modules)
            return

        for i in range(self.iterations):
            run_tests(self.test_modules, include=self.include_patterns,
                      exclude=self.exclude_patterns,
                      enable=self.enable_patterns, unskip=self.unskip_patterns,
                      test_timeout=self.timeout, fail_fast=self.fail_fast,
                      verbose=self.verbose, quiet=self.quiet)

_plano_command = None

class PlanoCommand(BaseCommand):
    def __init__(self, module=None, description="Run commands defined as Python functions", epilog=None):
        self.module = module
        self.bound_commands = dict()
        self.running_commands = list()
        self.passthrough_args = None

        assert self.module is None or _inspect.ismodule(self.module), self.module

        self.pre_parser = BaseArgumentParser(description=description, add_help=False)
        self.pre_parser.add_argument("-h", "--help", action="store_true",
                                     help="Show this help message and exit")

        if self.module is None:
            self.pre_parser.add_argument("-f", "--file", help="Load commands from FILE (default '.plano.py')")
            self.pre_parser.add_argument("-m", "--module", help="Load commands from MODULE")

        self.parser = _argparse.ArgumentParser(parents=(self.pre_parser,),
                                               description=description, epilog=epilog,
                                               add_help=False, allow_abbrev=False)

        # This is intentionally added after self.pre_parser is passed
        # as parent to self.parser, since it is used only in the
        # preliminary parsing.
        self.pre_parser.add_argument("command", nargs="?", help=_argparse.SUPPRESS)

        global _plano_command
        _plano_command = self

    def parse_args(self, args):
        pre_args, _ = self.pre_parser.parse_known_args(args)

        if self.module is None:
            if pre_args.module is None:
                self.module = self._load_file(pre_args.file)
            else:
                self.module = self._load_module(pre_args.module)

        if self.module is not None:
            self._bind_commands(self.module)

        self._process_commands()

        self.preceding_commands = list()

        if pre_args.command is not None and "," in pre_args.command:
            names = pre_args.command.split(",")

            for name in names[:-1]:
                try:
                    self.preceding_commands.append(self.bound_commands[name])
                except KeyError:
                    self.parser.error(f"Command '{name}' is unknown")

            args[args.index(pre_args.command)] = names[-1]

        args, self.passthrough_args = self.parser.parse_known_args(args)

        return args

    def init(self, args):
        self.help = args.help

        self.selected_command = None
        self.command_args = list()
        self.command_kwargs = dict()

        if args.command is not None:
            for command in self.preceding_commands:
                command()

            self.selected_command = self.bound_commands[args.command]

            if not self.selected_command.passthrough and self.passthrough_args:
                self.parser.error(f"unrecognized arguments: {' '.join(self.passthrough_args)}")

            for arg in self.selected_command.args.values():
                if arg.name == "passthrough_args":
                    continue

                if arg.positional:
                    if arg.multiple:
                        self.command_args.extend(getattr(args, arg.name))
                    else:
                        self.command_args.append(getattr(args, arg.name))
                else:
                    self.command_kwargs[arg.name] = getattr(args, arg.name)

            if self.selected_command.passthrough:
                self.command_kwargs["passthrough_args"] = self.passthrough_args

    def run(self):
        if self.help or self.module is None or self.selected_command is None:
            self.parser.print_help()
            return

        with Timer() as timer:
            self.selected_command(*self.command_args, **self.command_kwargs)

        cprint("OK", color="green", file=_sys.stderr, end="")
        cprint(" ({})".format(format_duration(timer.elapsed_time)), color="magenta", file=_sys.stderr)

    def _load_module(self, name):
        try:
            return _importlib.import_module(name)
        except ImportError:
            exit("Module '{}' not found", name)

    def _load_file(self, path):
        if path is not None and is_dir(path):
            path = self._find_file(path)

        if path is not None and not is_file(path):
            exit("File '{}' not found", path)

        if path is None:
            path = self._find_file(get_current_dir())

        if path is None:
            return

        debug("Loading '{}'", path)

        _sys.path.insert(0, join(get_parent_dir(path), "python"))

        spec = _importlib.util.spec_from_file_location("_plano", path)
        module = _importlib.util.module_from_spec(spec)
        _sys.modules["_plano"] = module

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            error(e)
            exit("Failure loading {}: {}", path, str(e))

        return module

    def _find_file(self, dir):
        # Planofile and .planofile remain temporarily for backward compatibility
        for name in (".plano.py", "Planofile", ".planofile"):
            path = join(dir, name)

            if is_file(path):
                return path

    def _bind_commands(self, module):
        for var in vars(module).values():
            if callable(var) and var.__class__.__name__ == "Command":
                self.bound_commands[var.name] = var

    def _process_commands(self):
        subparsers = self.parser.add_subparsers(title="commands", dest="command")

        for command in self.bound_commands.values():
            add_help = False if command.passthrough else True

            subparser = subparsers.add_parser(command.name, help=command.help,
                                              description=nvl(command.description, command.help), add_help=add_help,
                                              formatter_class=_argparse.RawDescriptionHelpFormatter)

            for arg in command.args.values():
                if arg.positional:
                    if arg.multiple:
                        subparser.add_argument(arg.name, metavar=arg.metavar, type=arg.type, help=arg.help, nargs="*")
                    elif arg.optional:
                        subparser.add_argument(arg.name, metavar=arg.metavar, type=arg.type, help=arg.help, nargs="?", default=arg.default)
                    else:
                        subparser.add_argument(arg.name, metavar=arg.metavar, type=arg.type, help=arg.help)
                else:
                    flag_args = list()

                    if arg.short_option is not None:
                        flag_args.append("-{}".format(arg.short_option))

                    flag_args.append("--{}".format(arg.display_name))

                    help = arg.help

                    if arg.default not in (None, False):
                        if help is None:
                            help = "Default value is {}".format(repr(arg.default))
                        else:
                            help += " (default {})".format(repr(arg.default))

                    if arg.default is False:
                        subparser.add_argument(*flag_args, dest=arg.name, default=arg.default, action="store_true", help=help)
                    else:
                        subparser.add_argument(*flag_args, dest=arg.name, default=arg.default, metavar=arg.metavar, type=arg.type, help=help)

            _capitalize_help(subparser)

def plano(): # pragma: nocover
    PlanoCommand().main()

def plano_test(): # pragma: nocover
    PlanoTestCommand().main()
