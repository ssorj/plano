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

import argparse as _argparse
import base64 as _base64
import binascii as _binascii
import code as _code
import codecs as _codecs
import collections as _collections
import fnmatch as _fnmatch
import getpass as _getpass
import inspect as _inspect
import json as _json
import os as _os
import pprint as _pprint
import pkgutil as _pkgutil
import random as _random
import re as _re
import shlex as _shlex
import shutil as _shutil
import signal as _signal
import socket as _socket
import subprocess as _subprocess
import sys as _sys
import tempfile as _tempfile
import time as _time
import traceback as _traceback
import uuid as _uuid

try: # pragma: nocover
    import urllib.parse as _urlparse
except ImportError: # pragma: nocover
    import urllib as _urlparse

try:
    import importlib as _importlib

    def _import_module(name):
        return _importlib.import_module(name)
except ImportError: # pragma: nocover
    def _import_module(name):
        return __import__(name, fromlist=[""])

_max = max

## Exceptions

class PlanoException(Exception):
    pass

class PlanoError(PlanoException):
    pass

class PlanoTimeout(PlanoException):
    pass

class PlanoTestSkipped(Exception):
    pass

## Global variables

ENV = _os.environ
ARGS = _sys.argv

STDIN = _sys.stdin
STDOUT = _sys.stdout
STDERR = _sys.stderr
DEVNULL = _os.devnull

PYTHON2 = _sys.version_info[0] == 2
PYTHON3 = _sys.version_info[0] == 3

PLANO_DEBUG = "PLANO_DEBUG" in ENV

## Archive operations

def make_archive(input_dir, output_file=None, quiet=False):
    """
    group: archive_operations
    """

    check_programs("tar")

    archive_stem = get_base_name(input_dir)

    if output_file is None:
        output_file = "{0}.tar.gz".format(join(get_current_dir(), archive_stem))

    _log(quiet, "Making archive {0} from directory {1}", repr(output_file), repr(input_dir))

    with working_dir(get_parent_dir(input_dir)):
        run("tar -czf {0} {1}".format(output_file, archive_stem))

    return output_file

def extract_archive(input_file, output_dir=None, quiet=False):
    check_programs("tar")

    if output_dir is None:
        output_dir = get_current_dir()

    _log(quiet, "Extracting archive {0} to directory {1}", repr(input_file), repr(output_dir))

    input_file = get_absolute_path(input_file)

    with working_dir(output_dir):
        run("tar -xf {0}".format(input_file))

    return output_dir

def rename_archive(input_file, new_archive_stem, quiet=False):
    _log(quiet, "Renaming archive {0} with stem {1}", repr(input_file), repr(new_archive_stem))

    output_dir = get_absolute_path(get_parent_dir(input_file))
    output_file = "{0}.tar.gz".format(join(output_dir, new_archive_stem))

    input_file = get_absolute_path(input_file)

    with working_dir():
        extract_archive(input_file)

        input_name = list_dir()[0]
        input_dir = move(input_name, new_archive_stem)

        make_archive(input_dir, output_file=output_file)

    remove(input_file)

    return output_file

## Command operations

class BaseCommand(object):
    def main(self, args=None):
        args = self.parse_args(args)

        assert args is None or isinstance(args, _argparse.Namespace), args

        self.verbose = args.verbose
        self.quiet = args.quiet
        self.init_only = args.init_only

        level = "notice"

        if self.verbose:
            level = "debug"

        if self.quiet:
            level = "error"

        with logging_enabled(level=level):
            try:
                self.init(args)

                if self.init_only:
                    return

                self.run()
            except PlanoError as e:
                if self.verbose:
                    _traceback.print_exc()
                    exit(1)
                else:
                    exit(str(e))

    def parse_args(self, args): # pragma: nocover
        raise NotImplementedError()

    def init(self, args): # pragma: nocover
        raise NotImplementedError()

    def run(self): # pragma: nocover
        raise NotImplementedError()

class BaseArgumentParser(_argparse.ArgumentParser):
    def __init__(self, **kwargs):
        super(BaseArgumentParser, self).__init__(**kwargs)

        self.allow_abbrev = False
        self.formatter_class = _argparse.RawDescriptionHelpFormatter

        self.add_argument("--verbose", action="store_true",
                          help="Print detailed logging to the console")
        self.add_argument("--quiet", action="store_true",
                          help="Print no logging to the console")
        self.add_argument("--init-only", action="store_true",
                          help=_argparse.SUPPRESS)

        _capitalize_help(self)

# Patch the default help text
def _capitalize_help(parser):
    try:
        for action in parser._actions:
            if action.help and action.help is not _argparse.SUPPRESS:
                action.help = capitalize(action.help)
    except: # pragma: nocover
        pass

## Console operations

def flush():
    _sys.stdout.flush()
    _sys.stderr.flush()

def eprint(*args, **kwargs):
    print(*args, file=_sys.stderr, **kwargs)

def pprint(*args, **kwargs):
    args = [pformat(x) for x in args]
    print(*args, **kwargs)

_color_codes = {
    "black": "\u001b[30",
    "red": "\u001b[31",
    "green": "\u001b[32",
    "yellow": "\u001b[33",
    "blue": "\u001b[34",
    "magenta": "\u001b[35",
    "cyan": "\u001b[36",
    "white": "\u001b[37",
}

class console_color(object):
    def __init__(self, color=None, file=_sys.stdout, bright=False):
        self.color = color
        self.file = file
        self.color_code = None

        if self.color is not None:
            elems = [_color_codes[color]]

            if bright:
                elems.append(";1")

            elems.append("m")

            self.color_code = "".join(elems)

        self.enabled = self.color_code is not None and PYTHON3 and hasattr(self.file, "isatty") and self.file.isatty()

    def __enter__(self):
        if self.enabled:
            print(self.color_code, file=self.file, end="", flush=True)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.enabled:
            print("\u001b[0m", file=self.file, end="", flush=True)

def cprint(*args, **kwargs):
    color = kwargs.pop("color", "white")
    bright = kwargs.pop("bright", False)
    file = kwargs.get("file", _sys.stdout)

    with console_color(color, bright=bright, file=file):
        print(*args, **kwargs)

class output_redirected(object):
    def __init__(self, output, quiet=False):
        self.output = output
        self.quiet = quiet

    def __enter__(self):
        flush()

        _log(self.quiet, "Redirecting output to file {0}", repr(self.output))

        if is_string(self.output):
            output = open(self.output, "w")

        self.prev_stdout, self.prev_stderr = _sys.stdout, _sys.stderr
        _sys.stdout, _sys.stderr = output, output

    def __exit__(self, exc_type, exc_value, traceback):
        flush()

        _sys.stdout, _sys.stderr = self.prev_stdout, self.prev_stderr

try:
    breakpoint
except NameError: # pragma: nocover
    def breakpoint():
        import pdb
        pdb.set_trace()

def repl(vars): # pragma: nocover
    _code.InteractiveConsole(locals=vars).interact()

## Directory operations

def find(dirs=None, include="*", exclude=()):
    if dirs is None:
        dirs = "."

    if is_string(dirs):
        dirs = (dirs,)

    if is_string(include):
        include = (include,)

    if is_string(exclude):
        exclude = (exclude,)

    found = set()

    for dir in dirs:
        for root, dir_names, file_names in _os.walk(dir):
            names = dir_names + file_names

            for include_pattern in include:
                names = _fnmatch.filter(names, include_pattern)

                for exclude_pattern in exclude:
                    for name in _fnmatch.filter(names, exclude_pattern):
                        names.remove(name)

                if root.startswith("./"):
                    root = remove_prefix(root, "./")
                elif root == ".":
                    root = ""

                found.update([join(root, x) for x in names])

    return sorted(found)

def make_dir(dir, quiet=False):
    if dir == "":
        return dir

    if not exists(dir):
        _log(quiet, "Making directory '{0}'", dir)
        _os.makedirs(dir)

    return dir

def make_parent_dir(path, quiet=False):
    return make_dir(get_parent_dir(path), quiet=quiet)

# Returns the current working directory so you can change it back
def change_dir(dir, quiet=False):
    _log(quiet, "Changing directory to {0}", repr(dir))

    prev_dir = get_current_dir()

    if not dir:
        return prev_dir

    _os.chdir(dir)

    return prev_dir

def list_dir(dir=None, include="*", exclude=()):
    if dir is None:
        dir = get_current_dir()

    assert is_dir(dir)

    if is_string(include):
        include = (include,)

    if is_string(exclude):
        exclude = (exclude,)

    names = _os.listdir(dir)

    for include_pattern in include:
        names = _fnmatch.filter(names, include_pattern)

        for exclude_pattern in exclude:
            for name in _fnmatch.filter(names, exclude_pattern):
                names.remove(name)

    return sorted(names)

# No args constructor gets a temp dir
class working_dir(object):
    def __init__(self, dir=None, quiet=False):
        self.dir = dir
        self.prev_dir = None
        self.remove = False
        self.quiet = quiet

        if self.dir is None:
            self.dir = make_temp_dir()
            self.remove = True

    def __enter__(self):
        if self.dir == ".":
            return

        _log(self.quiet, "Entering directory {0}", repr(get_absolute_path(self.dir)))

        make_dir(self.dir, quiet=True)

        self.prev_dir = change_dir(self.dir, quiet=True)

        return self.dir

    def __exit__(self, exc_type, exc_value, traceback):
        if self.dir == ".":
            return

        _log(self.quiet, "Returning to directory {0}", repr(get_absolute_path(self.prev_dir)))

        change_dir(self.prev_dir, quiet=True)

        if self.remove:
            remove(self.dir, quiet=True)

## Environment operations

def join_path_var(*paths):
    return _os.pathsep.join(unique(skip(paths)))

def get_current_dir():
    return _os.getcwd()

def get_home_dir(user=None):
    return _os.path.expanduser("~{0}".format(user or ""))

def get_user():
    return _getpass.getuser()

def get_hostname():
    return _socket.gethostname()

def get_program_name(command=None):
    if command is None:
        args = ARGS
    else:
        args = command.split()

    for arg in args:
        if "=" not in arg:
            return get_base_name(arg)

def which(program_name):
    assert "PATH" in _os.environ, _os.environ

    for dir in _os.environ["PATH"].split(_os.pathsep):
        program = join(dir, program_name)

        if _os.access(program, _os.X_OK):
            return program

def check_env(*vars):
    for var in vars:
        if var not in _os.environ:
            raise PlanoError("Environment variable {0} is not set".format(repr(var)))

def check_modules(*modules):
    for module in modules:
        if _pkgutil.find_loader(module) is None:
            raise PlanoError("Module {0} is not found".format(repr(module)))

def check_programs(*programs):
    for program in programs:
        if which(program) is None:
            raise PlanoError("Program {0} is not found".format(repr(program)))

class working_env(object):
    def __init__(self, **vars):
        self.amend = vars.pop("amend", True)
        self.vars = vars

    def __enter__(self):
        self.prev_vars = dict(_os.environ)

        if not self.amend:
            for name, value in list(_os.environ.items()):
                if name not in self.vars:
                    del _os.environ[name]

        for name, value in self.vars.items():
            _os.environ[name] = str(value)

    def __exit__(self, exc_type, exc_value, traceback):
        for name, value in self.prev_vars.items():
            _os.environ[name] = value

        for name, value in self.vars.items():
            if name not in self.prev_vars:
                del ENV[name]

class working_python_path(object):
    def __init__(self, path, amend=True):
        if is_string(path):
            if not is_absolute(path):
                path = get_absolute_path(path)

            path = [path]

        if amend:
            path = path + _sys.path

        self.path = path

    def __enter__(self):
        self.prev_path = _sys.path
        _sys.path = self.path

    def __exit__(self, exc_type, exc_value, traceback):
        _sys.path = self.prev_path

## File operations

def touch(file, quiet=False):
    _log(quiet, "Touching {0}", repr(file))

    try:
        _os.utime(file, None)
    except OSError:
        append(file, "")

    return file

# symlinks=True - Preserve symlinks
# inside=True - Place from_path inside to_path if to_path is a directory
def copy(from_path, to_path, symlinks=True, inside=True, quiet=False):
    _log(quiet, "Copying {0} to {1}", repr(from_path), repr(to_path))

    if is_dir(to_path) and inside:
        to_path = join(to_path, get_base_name(from_path))
    else:
        make_parent_dir(to_path, quiet=True)

    if is_dir(from_path):
        for name in list_dir(from_path):
            copy(join(from_path, name), join(to_path, name), symlinks=symlinks, inside=False, quiet=True)

        _shutil.copystat(from_path, to_path)
    elif is_link(from_path) and symlinks:
        make_link(to_path, read_link(from_path), quiet=True)
    else:
        _shutil.copy2(from_path, to_path)

    return to_path

# inside=True - Place from_path inside to_path if to_path is a directory
def move(from_path, to_path, inside=True, quiet=False):
    _log(quiet, "Moving {0} to {1}", repr(from_path), repr(to_path))

    to_path = copy(from_path, to_path, inside=inside, quiet=True)
    remove(from_path, quiet=True)

    return to_path

def remove(paths, quiet=False):
    if is_string(paths):
        paths = (paths,)

    for path in paths:
        if not exists(path):
            continue

        _log(quiet, "Removing {0}", repr(path))

        if is_dir(path):
            _shutil.rmtree(path, ignore_errors=True)
        else:
            _os.remove(path)

def get_file_size(file):
    return _os.path.getsize(file)

## IO operations

def read(file):
    with _codecs.open(file, encoding="utf-8", mode="r") as f:
        return f.read()

def write(file, string):
    make_parent_dir(file, quiet=True)

    with _codecs.open(file, encoding="utf-8", mode="w") as f:
        f.write(string)

    return file

def append(file, string):
    make_parent_dir(file, quiet=True)

    with _codecs.open(file, encoding="utf-8", mode="a") as f:
        f.write(string)

    return file

def prepend(file, string):
    orig = read(file)
    return write(file, string + orig)

def tail(file, count):
    return "".join(tail_lines(file, count))

def read_lines(file):
    with _codecs.open(file, encoding="utf-8", mode="r") as f:
        return f.readlines()

def write_lines(file, lines):
    make_parent_dir(file, quiet=True)

    with _codecs.open(file, encoding="utf-8", mode="w") as f:
        f.writelines(lines)

    return file

def append_lines(file, lines):
    make_parent_dir(file, quiet=True)

    with _codecs.open(file, encoding="utf-8", mode="a") as f:
        f.writelines(lines)

    return file

def prepend_lines(file, lines):
    orig_lines = read_lines(file)

    make_parent_dir(file, quiet=True)

    with _codecs.open(file, encoding="utf-8", mode="w") as f:
        f.writelines(lines)
        f.writelines(orig_lines)

    return file

def tail_lines(file, count):
    assert count >= 0

    with _codecs.open(file, encoding="utf-8", mode="r") as f:
        pos = count + 1
        lines = list()

        while len(lines) <= count:
            try:
                f.seek(-pos, 2)
            except IOError:
                f.seek(0)
                break
            finally:
                lines = f.readlines()

            pos *= 2

        return lines[-count:]

## Iterable operations

def unique(iterable):
    return list(_collections.OrderedDict.fromkeys(iterable).keys())

def skip(iterable, values=(None, "")):
    items = list()

    for item in iterable:
        if item not in values:
            items.append(item)

    return items

## JSON operations

def read_json(file):
    with _codecs.open(file, encoding="utf-8", mode="r") as f:
        return _json.load(f)

def write_json(file, data):
    make_parent_dir(file, quiet=True)

    with _codecs.open(file, encoding="utf-8", mode="w") as f:
        _json.dump(data, f, indent=4, separators=(",", ": "), sort_keys=True)

    return file

def parse_json(json):
    return _json.loads(json)

def emit_json(data):
    return _json.dumps(data, indent=4, separators=(",", ": "), sort_keys=True)

## HTTP operations

def _run_curl(method, url, content=None, content_file=None, content_type=None, output_file=None, insecure=False):
    check_programs("curl")

    options = [
        "-sf",
        "-X", method,
        "-H", "'Expect:'",
    ]

    if content is not None:
        assert content_file is None
        options.extend(("-d", "@-"))

    if content_file is not None:
        assert content is None, content
        options.extend(("-d", "@{0}".format(content_file)))

    if content_type is not None:
        options.extend(("-H", "'Content-Type: {0}'".format(content_type)))

    if output_file is not None:
        options.extend(("-o", output_file))

    if insecure:
        options.append("--insecure")

    options = " ".join(options)
    command = "curl {0} {1}".format(options, url)

    if output_file is None:
        return call(command, input=content)
    else:
        make_parent_dir(output_file, quiet=True)
        run(command, input=content)

def http_get(url, output_file=None, insecure=False):
    return _run_curl("GET", url, output_file=output_file, insecure=insecure)

def http_get_json(url, insecure=False):
    return parse_json(http_get(url, insecure=insecure))

def http_put(url, content, content_type=None, insecure=False):
    _run_curl("PUT", url, content=content, content_type=content_type, insecure=insecure)

def http_put_file(url, content_file, content_type=None, insecure=False):
    _run_curl("PUT", url, content_file=content_file, content_type=content_type, insecure=insecure)

def http_put_json(url, data, insecure=False):
    http_put(url, emit_json(data), content_type="application/json", insecure=insecure)

def http_post(url, content, content_type=None, output_file=None, insecure=False):
    return _run_curl("POST", url, content=content, content_type=content_type, output_file=output_file, insecure=insecure)

def http_post_file(url, content_file, content_type=None, output_file=None, insecure=False):
    return _run_curl("POST", url, content_file=content_file, content_type=content_type, output_file=output_file, insecure=insecure)

def http_post_json(url, data, insecure=False):
    return parse_json(http_post(url, emit_json(data), content_type="application/json", insecure=insecure))

## Link operations

def make_link(path, linked_path, quiet=False):
    _log(quiet, "Making link {0} to {1}", repr(path), repr(linked_path))

    make_parent_dir(path, quiet=True)
    remove(path, quiet=True)

    _os.symlink(linked_path, path)

    return path

def read_link(path):
    return _os.readlink(path)

## Logging operations

_logging_levels = (
    "debug",
    "notice",
    "warn",
    "error",
    "disabled",
)

_debug = _logging_levels.index("debug")
_notice = _logging_levels.index("notice")
_warn = _logging_levels.index("warn")
_error = _logging_levels.index("error")
_disabled = _logging_levels.index("disabled")

_logging_output = None
_logging_threshold = _notice

def enable_logging(level="notice", output=None):
    assert level in _logging_levels

    debug("Enabling logging (level={0}, output={1})", repr(level), repr(nvl(output, "stderr")))

    global _logging_threshold
    _logging_threshold = _logging_levels.index(level)

    if is_string(output):
        output = open(output, "w")

    global _logging_output
    _logging_output = output

def disable_logging():
    debug("Disabling logging")

    global _logging_threshold
    _logging_threshold = _disabled

class logging_enabled(object):
    def __init__(self, level="notice", output=None):
        self.level = level
        self.output = output

    def __enter__(self):
        self.prev_level = _logging_levels[_logging_threshold]
        self.prev_output = _logging_output

        if self.level == "disabled":
            disable_logging()
        else:
            enable_logging(level=self.level, output=self.output)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.prev_level == "disabled":
            disable_logging()
        else:
            enable_logging(level=self.prev_level, output=self.prev_output)

class logging_disabled(logging_enabled):
    def __init__(self):
        super(logging_disabled, self).__init__(level="disabled")

def fail(message, *args):
    error(message, *args)

    if isinstance(message, BaseException):
        raise message

    raise PlanoError(message.format(*args))

def error(message, *args):
    log(_error, message, *args)

def warn(message, *args):
    log(_warn, message, *args)

def notice(message, *args):
    log(_notice, message, *args)

def debug(message, *args):
    log(_debug, message, *args)

def log(level, message, *args):
    if is_string(level):
        level = _logging_levels.index(level)

    if _logging_threshold <= level:
        _print_message(level, message, args)

def _print_message(level, message, args, color=None):
    out = nvl(_logging_output, _sys.stderr)

    print("{0}: ".format(get_program_name()), file=out, end="")

    color = ("cyan", "blue", "yellow", "red", None)[level]
    cprint("{0:>6}: ".format(_logging_levels[level]), color=color, file=out, end="")

    if isinstance(message, BaseException) and hasattr(message, "__traceback__"):
        print("{0}: {1}".format(type(message).__name__, str(message)), file=out)
        _traceback.print_exception(type(message), message, message.__traceback__, file=out)
        return

    if not is_string(message):
        message = str(message)

    if args:
        message = message.format(*args)

    print(capitalize(message), file=out)

    out.flush()

def _log(quiet, message, *args):
    if quiet:
        debug(message, *args)
    else:
        notice(message, *args)

## Path operations

def get_absolute_path(path):
    return _os.path.abspath(path)

def normalize_path(path):
    return _os.path.normpath(path)

def get_real_path(path):
    return _os.path.realpath(path)

def get_relative_path(path, start=None):
    return _os.path.relpath(path, start=start)

def get_file_url(path):
    return "file:{0}".format(get_absolute_path(path))

def exists(path):
    return _os.path.lexists(path)

def is_absolute(path):
    return _os.path.isabs(path)

def is_dir(path):
    return _os.path.isdir(path)

def is_file(path):
    return _os.path.isfile(path)

def is_link(path):
    return _os.path.islink(path)

def join(*paths):
    return _os.path.join(*paths)

def split(path):
    return _os.path.split(path)

def split_extension(path):
    return _os.path.splitext(path)

def get_parent_dir(path):
    path = normalize_path(path)
    parent, child = split(path)

    return parent

def get_base_name(path):
    path = normalize_path(path)
    parent, name = split(path)

    return name

def get_name_stem(file):
    name = get_base_name(file)

    if name.endswith(".tar.gz"):
        name = name[:-3]

    stem, ext = split_extension(name)

    return stem

def get_name_extension(file):
    name = get_base_name(file)
    stem, ext = split_extension(name)

    return ext

def check_exists(*paths):
    for path in paths:
        if not exists(path):
            raise PlanoError("File or directory {0} is not found".format(repr(path)))

def check_files(*paths):
    for path in paths:
        if not is_file(path):
            raise PlanoError("File {0} is not found".format(repr(path)))

def check_dirs(*paths):
    for path in paths:
        if not is_dir(path):
            raise PlanoError("Directory {0} is not found".format(repr(path)))

def await_exists(path, timeout=30, quiet=False):
    _log(quiet, "Waiting for path {0} to exist", repr(path))

    timeout_message = "Timed out waiting for path {0} to exist".format(path)
    period = 0.125

    with Timer(timeout=timeout, timeout_message=timeout_message) as timer:
        while True:
            try:
                check_exists(path)
            except PlanoError:
                sleep(period, quiet=True)
                period = min(1, period * 2)
            else:
                return

## Port operations

def get_random_port(min=49152, max=65535):
    ports = [_random.randint(min, max) for _ in range(3)]

    for port in ports:
        try:
            check_ports(port)
        except PlanoError:
            return port

    raise PlanoError("Random ports unavailable")

def check_ports(*ports, **kwargs):
    host = kwargs.pop("host", "localhost")
    assert not kwargs, kwargs

    for port in ports:
        sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)

        if sock.connect_ex((host, port)) != 0:
            raise PlanoError("Port {0} (host {1}) is not reachable".format(repr(port), repr(host)))

def await_port(port, host="localhost", timeout=30, quiet=False):
    _log(quiet, "Waiting for port {0}", port)

    if is_string(port):
        port = int(port)

    timeout_message = "Timed out waiting for port {0} to open".format(port)
    period = 0.125

    with Timer(timeout=timeout, timeout_message=timeout_message) as timer:
        while True:
            try:
                check_ports(port, host=host)
            except PlanoError:
                sleep(period, quiet=True)
                period = min(1, period * 2)
            else:
                return

## Process operations

def get_process_id():
    return _os.getpid()

def _format_command(command):
    if is_string(command):
        return repr(command)

    return repr(" ".join(command))

# quiet=False - Don't log at notice level
# stash=False - No output unless there is an error
# output=<file> - Send stdout and stderr to a file
# stdin=<file> - XXX
# stdout=<file> - Send stdout to a file
# stderr=<file> - Send stderr to a file
# shell=False - XXX
def start(command, stdin=None, stdout=None, stderr=None, output=None, shell=False, stash=False, quiet=False):
    _log(quiet, "Starting command {0}", _format_command(command))

    if output is not None:
        stdout, stderr = output, output

    if is_string(stdin):
        stdin = open(stdin, "r")

    if is_string(stdout):
        stdout = open(stdout, "w")

    if is_string(stderr):
        stderr = open(stderr, "w")

    if stdin is None:
        stdin = _sys.stdin

    if stdout is None:
        stdout = _sys.stdout

    if stderr is None:
        stderr = _sys.stderr

    stash_file = None

    if stash:
        stash_file = make_temp_file()
        out = open(stash_file, "w")
        stdout = out
        stderr = out

    if shell:
        if is_string(command):
            args = command
        else:
            args = " ".join(command)
    else:
        if is_string(command):
            args = _shlex.split(command)
        else:
            args = command

    try:
        proc = PlanoProcess(args, stdin=stdin, stdout=stdout, stderr=stderr, shell=shell, close_fds=True, stash_file=stash_file)
    except OSError as e:
        raise PlanoError("Command {0}: {1}".format(_format_command(command), str(e)))

    debug("{0} started", proc)

    return proc

def stop(proc, timeout=None, quiet=False):
    _log(quiet, "Stopping {0}", proc)

    if proc.poll() is not None:
        if proc.exit_code == 0:
            debug("{0} already exited normally", proc)
        elif proc.exit_code == -(_signal.SIGTERM):
            debug("{0} was already terminated", proc)
        else:
            debug("{0} already exited with code {1}", proc, proc.exit_code)

        return proc

    kill(proc, quiet=True)

    return wait(proc, timeout=timeout, quiet=True)

def kill(proc, quiet=False):
    _log(quiet, "Killing {0}", proc)

    proc.terminate()

def wait(proc, timeout=None, check=False, quiet=False):
    _log(quiet, "Waiting for {0} to exit", proc)

    if PYTHON2: # pragma: nocover
        assert timeout is None, "The timeout option is not supported on Python 2"
        proc.wait()
    else:
        try:
            proc.wait(timeout=timeout)
        except _subprocess.TimeoutExpired:
            raise PlanoTimeout()

    if proc.exit_code == 0:
        debug("{0} exited normally", proc)
    elif proc.exit_code < 0:
        debug("{0} was terminated by signal {1}", proc, abs(proc.exit_code))
    else:
        debug("{0} exited with code {1}", proc, proc.exit_code)

    if proc.stash_file is not None:
        if proc.exit_code > 0:
            eprint(read(proc.stash_file), end="")

        remove(proc.stash_file, quiet=True)

    if check and proc.exit_code > 0:
        raise PlanoProcessError(proc)

    return proc

# input=<string> - Pipe <string> to the process
def run(command, stdin=None, stdout=None, stderr=None, input=None, output=None,
        stash=False, shell=False, check=True, quiet=False):
    _log(quiet, "Running command {0}", _format_command(command))

    if input is not None:
        assert stdin in (None, _subprocess.PIPE), stdin

        input = input.encode("utf-8")
        stdin = _subprocess.PIPE

    proc = start(command, stdin=stdin, stdout=stdout, stderr=stderr, output=output,
                 stash=stash, shell=shell, quiet=True)

    proc.stdout_result, proc.stderr_result = proc.communicate(input=input)

    if proc.stdout_result is not None:
        proc.stdout_result = proc.stdout_result.decode("utf-8")

    if proc.stderr_result is not None:
        proc.stderr_result = proc.stderr_result.decode("utf-8")

    return wait(proc, check=check, quiet=True)

# input=<string> - Pipe the given input into the process
def call(command, input=None, shell=False, quiet=False):
    _log(quiet, "Calling {0}", _format_command(command))

    proc = run(command, stdin=_subprocess.PIPE, stdout=_subprocess.PIPE, stderr=_subprocess.PIPE,
               input=input, shell=shell, check=True, quiet=True)

    return proc.stdout_result

def exit(arg=None, *args):
    if arg in (0, None):
        _sys.exit()

    if is_string(arg):
        error(arg, *args)
        _sys.exit(1)

    if isinstance(arg, BaseException):
        error(str(arg))
        _sys.exit(1)

    if isinstance(arg, int):
        if arg > 0:
            error("Exiting with code {0}", arg)
        else:
            notice("Exiting with code {0}", arg)

        _sys.exit(arg)

    raise PlanoException("Illegal argument")

_child_processes = list()

class PlanoProcess(_subprocess.Popen):
    def __init__(self, args, **options):
        self.stash_file = options.pop("stash_file", None)

        super(PlanoProcess, self).__init__(args, **options)

        self.args = args
        self.stdout_result = None
        self.stderr_result = None

        _child_processes.append(self)

    @property
    def exit_code(self):
        return self.returncode

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        kill(self)

    def __repr__(self):
        return "process {0} (command {1})".format(self.pid, _format_command(self.args))

class PlanoProcessError(_subprocess.CalledProcessError, PlanoError):
    def __init__(self, proc):
        super(PlanoProcessError, self).__init__(proc.exit_code, " ".join(proc.args))

def _default_sigterm_handler(signum, frame):
    for proc in _child_processes:
        if proc.poll() is None:
            proc.terminate()

    exit(-(_signal.SIGTERM))

_signal.signal(_signal.SIGTERM, _default_sigterm_handler)

## String operations

def replace(string, expr, replacement, count=0):
    return _re.sub(expr, replacement, string, count)

def remove_prefix(string, prefix):
    if string is None:
        return ""

    if prefix and string.startswith(prefix):
        string = string[len(prefix):]

    return string

def remove_suffix(string, suffix):
    if string is None:
        return ""

    if suffix and string.endswith(suffix):
        string = string[:-len(suffix)]

    return string

def shorten(string, max, ellipsis=None):
    assert max is None or isinstance(max, int)

    if string is None:
        return ""

    if max is None or len(string) < max:
        return string
    else:
        if ellipsis is not None:
            string = string + ellipsis
            end = _max(0, max - len(ellipsis))
            return string[0:end] + ellipsis
        else:
            return string[0:max]

def plural(noun, count=0, plural=None):
    if noun in (None, ""):
        return ""

    if count == 1:
        return noun

    if plural is None:
        if noun.endswith("s"):
            plural = "{0}ses".format(noun)
        else:
            plural = "{0}s".format(noun)

    return plural

def capitalize(string):
    if not string:
        return ""

    return string[0].upper() + string[1:]

def base64_encode(string):
    return _base64.b64encode(string)

def base64_decode(string):
    return _base64.b64decode(string)

def url_encode(string):
    return _urlparse.quote_plus(string)

def url_decode(string):
    return _urlparse.unquote_plus(string)

## Temp operations

def get_temp_dir():
    return _tempfile.gettempdir()

def get_user_temp_dir():
    try:
        return _os.environ["XDG_RUNTIME_DIR"]
    except KeyError:
        return join(get_temp_dir(), get_user())

def make_temp_file(suffix="", dir=None):
    if dir is None:
        dir = get_temp_dir()

    return _tempfile.mkstemp(prefix="plano-", suffix=suffix, dir=dir)[1]

def make_temp_dir(suffix="", dir=None):
    if dir is None:
        dir = get_temp_dir()

    return _tempfile.mkdtemp(prefix="plano-", suffix=suffix, dir=dir)

class temp_file(object):
    def __init__(self, suffix="", dir=None):
        self.file = make_temp_file(suffix=suffix, dir=dir)

    def __enter__(self):
        return self.file

    def __exit__(self, exc_type, exc_value, traceback):
        remove(self.file, quiet=True)

## Time operations

def sleep(seconds, quiet=False):
    _log(quiet, "Sleeping for {0} {1}", seconds, plural("second", seconds))

    _time.sleep(seconds)

def get_time():
    return _time.time()

def format_duration(duration):
    if duration >= 240:
        return "{0:.0f}m".format(duration / 60)

    if duration >= 60:
        return "{0:.0f}s".format(duration)

    return "{0:.1f}s".format(duration)

class Timer(object):
    def __init__(self, timeout=None, timeout_message=None):
        # Alarms work with integral seconds only
        assert timeout is None or isinstance(timeout, int), type(timeout)

        self.timeout = timeout
        self.timeout_message = timeout_message

        self.start_time = None
        self.stop_time = None

    def start(self):
        self.start_time = get_time()

        if self.timeout is not None:
            _signal.signal(_signal.SIGALRM, self.raise_timeout)
            _signal.alarm(self.timeout)

    def stop(self):
        self.stop_time = get_time()

        if self.timeout is not None:
            _signal.alarm(0)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    @property
    def elapsed_time(self):
        assert self.start_time is not None

        if self.stop_time is None:
            return get_time() - self.start_time
        else:
            return self.stop_time - self.start_time

    def raise_timeout(self, *args):
        raise PlanoTimeout(self.timeout_message)

## Unique ID operations

# Length in bytes, renders twice as long in hex
def get_unique_id(bytes=16):
    assert bytes >= 1
    assert bytes <= 16

    uuid_bytes = _uuid.uuid4().bytes
    uuid_bytes = uuid_bytes[:bytes]

    return _binascii.hexlify(uuid_bytes).decode("utf-8")

## Value operations

def is_string(value):
    try:
        return isinstance(value, basestring)
    except NameError:
        return isinstance(value, str)

def nvl(value, replacement):
    if value is None:
        return replacement

    return value

def pformat(value):
    return _pprint.pformat(value, width=120)

def format_repr(obj, limit=None):
    attrs = ["{0}={1}".format(k, repr(v)) for k, v in obj.__dict__.items()]
    return "{0}({1})".format(obj.__class__.__name__, ", ".join(attrs[:limit]))

class Namespace(object):
    def __init__(self, **kwargs):
        for name in kwargs:
            setattr(self, name, kwargs[name])

    def __eq__(self, other):
        return vars(self) == vars(other)

    def __contains__(self, key):
        return key in self.__dict__

    def __repr__(self):
        return format_repr(self)

## Test operations

def test(_function=None, name=None, timeout=None, disabled=False):
    class Test(object):
        def __init__(self, function):
            self.function = function
            self.name = nvl(name, self.function.__name__)
            self.timeout = timeout
            self.disabled = disabled

            self.module = _inspect.getmodule(self.function)

            if not hasattr(self.module, "_plano_tests"):
                self.module._plano_tests = list()

            self.module._plano_tests.append(self)

        def __call__(self, test_run):
            try:
                self.function()
            except SystemExit as e:
                error(e)
                raise PlanoError("System exit with code {0}".format(e))

        def __repr__(self):
            return "test '{0}:{1}'".format(self.module.__name__, self.name)

    if _function is None:
        return Test
    else:
        return Test(_function)

def print_tests(modules):
    if _inspect.ismodule(modules):
        modules = (modules,)

    for module in modules:
        for test in module._plano_tests:
            print(test)

def run_tests(modules, include="*", exclude=(), enable=(), test_timeout=300, fail_fast=False, verbose=False, quiet=False):
    if _inspect.ismodule(modules):
        modules = (modules,)

    if is_string(include):
        include = (include,)

    if is_string(exclude):
        exclude = (exclude,)

    if is_string(enable):
        enable = (enable,)

    test_run = TestRun(test_timeout=test_timeout, fail_fast=fail_fast, verbose=verbose, quiet=quiet)

    for module in modules:
        if verbose:
            notice("Running tests from module {0} (file {1})", repr(module.__name__), repr(module.__file__))
        elif not quiet:
            cprint("Test module {}:".format(repr(module.__name__)), color="cyan")

        if not hasattr(module, "_plano_tests"):
            warn("Module {0} has no tests", repr(module.__name__))
            continue

        for test in module._plano_tests:
            included = any([_fnmatch.fnmatchcase(test.name, x) for x in include])
            excluded = any([_fnmatch.fnmatchcase(test.name, x) for x in exclude])
            disabled = test.disabled and not any([_fnmatch.fnmatchcase(test.name, x) for x in enable])

            if included and not excluded and not disabled:
                test_run.tests.append(test)
                _run_test(test_run, test)

    total = len(test_run.tests)
    skipped = len(test_run.skipped_tests)
    failed = len(test_run.failed_tests)

    if total == 0:
        raise PlanoError("No tests ran")

    if failed == 0:
        message = "RESULT: All tests passed ({0} skipped)".format(skipped)

        if verbose:
            notice(message)
        elif not quiet:
            cprint(message, color="green")
    else:
        message = "RESULT: {0} {1} failed ({2} skipped)".format(failed, plural("test", failed), skipped)

        if verbose:
            error(message)
        elif not quiet:
            cprint(message, color="red")

        raise PlanoError(message)

def _run_test(test_run, test):
    if test_run.verbose:
        notice("Running {0}", test)
    elif not test_run.quiet:
        print("{0:.<72} ".format(test.name + " "), end="")

    timeout = nvl(test.timeout, test_run.test_timeout)

    with temp_file() as output_file:
        try:
            with Timer(timeout=timeout) as timer:
                if test_run.verbose:
                    test(test_run)
                else:
                    with output_redirected(output_file, quiet=True):
                        test(test_run)
        except KeyboardInterrupt:
            raise
        except PlanoTestSkipped as e:
            test_run.skipped_tests.append(test)

            if test_run.verbose:
                notice("{0} SKIPPED ({1})", test, format_duration(timer.elapsed_time))
            elif not test_run.quiet:
                _print_test_result("SKIPPED", timer, "yellow")
                print("Reason: {0}".format(str(e)))
        except Exception as e:
            test_run.failed_tests.append(test)

            if test_run.verbose:
                _traceback.print_exc()

                if isinstance(e, PlanoTimeout):
                    error("{0} **FAILED** (TIMEOUT) ({1})", test, format_duration(timer.elapsed_time))
                else:
                    error("{0} **FAILED** ({1})", test, format_duration(timer.elapsed_time))
            elif not test_run.quiet:
                if isinstance(e, PlanoTimeout):
                    _print_test_result("**FAILED** (TIMEOUT)", timer, "red")
                else:
                    _print_test_result("**FAILED**", timer, "red")

                _print_test_error(e)
                _print_test_output(output_file)

            if test_run.fail_fast:
                return True
        else:
            test_run.passed_tests.append(test)

            if test_run.verbose:
                notice("{0} PASSED ({1})", test, format_duration(timer.elapsed_time))
            elif not test_run.quiet:
                _print_test_result("PASSED", timer)

def _print_test_result(status, timer, color="white"):
    cprint("{0:<7}".format(status), color=color, end="")
    print("{0:>6}".format(format_duration(timer.elapsed_time)))

def _print_test_error(e):
    cprint("--- Error ---", color="yellow")

    if isinstance(e, PlanoProcessError):
        print("> {0}".format(str(e)))
    else:
        lines = _traceback.format_exc().rstrip().split("\n")
        lines = ["> {0}".format(x) for x in lines]

        print("\n".join(lines))

def _print_test_output(output_file):
    if get_file_size(output_file) == 0:
        return

    cprint("--- Output ---", color="yellow")

    with open(output_file, "r") as out:
        for line in out:
            print("> {0}".format(line), end="")

class TestRun(object):
    def __init__(self, test_timeout=None, fail_fast=False, verbose=False, quiet=False):
        self.tests = list()
        self.skipped_tests = list()
        self.failed_tests = list()
        self.passed_tests = list()

        self.test_timeout = test_timeout
        self.fail_fast = fail_fast
        self.verbose = verbose
        self.quiet = quiet

class expect_exception(object):
    def __init__(self, exception_type=Exception):
        self.exception_type = exception_type

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_value is None:
            assert False

        return isinstance(exc_value, self.exception_type)

class expect_error(expect_exception):
    def __init__(self):
        super(expect_error, self).__init__(PlanoError)

class expect_timeout(expect_exception):
    def __init__(self):
        super(expect_timeout, self).__init__(PlanoTimeout)

class expect_system_exit(expect_exception):
    def __init__(self):
        super(expect_system_exit, self).__init__(SystemExit)

class expect_output(temp_file):
    def __init__(self, value=None, contains=None):
        super(expect_output, self).__init__()
        self.value = value
        self.contains = contains

    def __exit__(self, exc_type, exc_value, traceback):
        result = read(self.file)

        if self.value is None:
            assert len(result) > 0, result
        else:
            assert result == self.value, result

        if self.contains is not None:
            assert self.contains in result, result

        super(expect_output, self).__exit__(exc_type, exc_value, traceback)

class PlanoTestCommand(BaseCommand):
    def __init__(self, test_modules=[]):
        super(PlanoTestCommand, self).__init__()

        self.test_modules = test_modules

        if _inspect.ismodule(self.test_modules):
            self.test_modules = [self.test_modules]

        self.parser = BaseArgumentParser()
        self.parser.add_argument("include", metavar="PATTERN", nargs="*", default=["*"],
                                 help="Run only tests with names matching PATTERN. This option can be repeated.")
        self.parser.add_argument("-e", "--exclude", metavar="PATTERN", action="append", default=[],
                                 help="Do not run tests with names matching PATTERN. This option can be repeated.")
        self.parser.add_argument("-m", "--module", action="append", default=[],
                                 help="Load tests from MODULE.  This option can be repeated.")
        self.parser.add_argument("-l", "--list", action="store_true",
                                 help="Print the test names and exit")
        self.parser.add_argument("--enable", metavar="PATTERN", action="append", default=[],
                                 help="Enable disabled tests matching PATTERN.  This option can be repeated.")
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
        self.timeout = args.timeout
        self.fail_fast = args.fail_fast
        self.iterations = args.iterations

        try:
            for name in args.module:
                self.test_modules.append(_import_module(name))
        except ImportError as e:
            raise PlanoError(e)

    def run(self):
        if self.list_only:
            print_tests(self.test_modules)
            return

        for i in range(self.iterations):
            run_tests(self.test_modules, include=self.include_patterns, exclude=self.exclude_patterns, enable=self.enable_patterns,
                      test_timeout=self.timeout, fail_fast=self.fail_fast, verbose=self.verbose, quiet=self.quiet)

## Plano command operations

_command_help = {
    "build":    "Build artifacts from source",
    "clean":    "Clean up the source tree",
    "dist":     "Generate distribution artifacts",
    "install":  "Install the built artifacts on your system",
    "test":     "Run the tests",
}

def command(_function=None, extends=None, name=None, args=None, help=None, description=None):
    class Command(object):
        def __init__(self, function):
            self.function = function
            self.extends = extends
            self.name = nvl(name, function.__name__.replace("_", "-"))

            if self.extends is None:
                self.args = self.process_args(args)
                self.help = nvl(help, _command_help.get(self.name))
                self.description = description
            else:
                self.args = self.extends.args
                self.help = nvl(help, self.extends.help)
                self.description = nvl(description, self.extends.description)

            self.module = _inspect.getmodule(self.function)
            self.container = None

            debug("Defining {0}", self)

            for arg in self.args.values():
                debug("  {0}", str(arg).capitalize())

        def __repr__(self):
            return "command '{0}:{1}'".format(self.module.__name__, self.name)

        def process_args(self, input_args):
            sig = _inspect.signature(self.function)
            input_args = {x.name: x for x in nvl(input_args, ())}
            output_args = _collections.OrderedDict()

            for param in sig.parameters.values():
                try:
                    arg = input_args[param.name]
                except KeyError:
                    arg = CommandArgument(param.name)

                if param.kind is param.POSITIONAL_ONLY: # pragma: nocover
                    arg.positional = True
                elif param.kind is param.POSITIONAL_OR_KEYWORD and param.default is param.empty:
                    arg.positional = True
                elif param.kind is param.POSITIONAL_OR_KEYWORD and param.default is not param.empty:
                    arg.optional = True
                    arg.default = param.default
                elif param.kind is param.VAR_POSITIONAL:
                    arg.positional = True
                    arg.multiple = True
                elif param.kind is param.KEYWORD_ONLY:
                    arg.optional = True
                    arg.default = param.default
                else: # pragma: nocover
                    raise NotImplementedError(param.kind)

                if arg.type is None and arg.default not in (None, False): # XXX why false?
                    arg.type = type(arg.default)

                output_args[arg.name] = arg

            return output_args

        def attach(self, container):
            if self.extends:
                self.extends.attach(container)

            debug("Attaching {0}", self)

            self.container = container
            self.container.attached_commands[self.name] = self

        def __call__(self, *args, **kwargs):
            assert self.container is not None, self

            command = self.container.attached_commands[self.name]

            if command is not self:
                command(*args, **kwargs)
                return

            debug("Running {0} {1} {2}".format(self, args, kwargs))

            self.container.running_commands.append(self)

            dashes = "--" * len(self.container.running_commands)
            display_args = list(self.get_display_args(args, kwargs))

            with console_color("magenta", file=_sys.stderr):
                eprint("{0}> {1}".format(dashes, self.name), end="")

                if display_args:
                    eprint(" ({0})".format(", ".join(display_args)), end="")

                eprint()

            if self.extends is not None:
                call_args, call_kwargs = self.extends.get_call_args(args, kwargs)
                self.extends.function(*call_args, **call_kwargs)

            call_args, call_kwargs = self.get_call_args(args, kwargs)

            self.function(*call_args, **call_kwargs)

            cprint("<{0} {1}".format(dashes, self.name), color="magenta", file=_sys.stderr)

            self.container.running_commands.pop()

            if self.container.running_commands:
                name = self.container.running_commands[-1].name

                cprint("{0}| {1}".format(dashes[:-2], name), color="magenta", file=_sys.stderr)

        def get_display_args(self, args, kwargs):
            for i, arg in enumerate(self.args.values()):
                if arg.positional:
                    if arg.multiple:
                        for va in args[i:]:
                            yield repr(va)
                    elif arg.optional:
                        value = args[i]

                        if value == arg.default:
                            continue

                        yield repr(value)
                    else:
                        yield repr(args[i])
                else:
                    value = kwargs.get(arg.name, arg.default)

                    if value == arg.default:
                        continue

                    if value in (True, False):
                        value = str(value).lower()
                    else:
                        value = repr(value)

                    yield "{0}={1}".format(arg.display_name, value)

        def get_call_args(self, args, kwargs):
            sig = _inspect.signature(self.function)
            call_args = list()
            call_kwargs = dict()

            for i, param in enumerate(sig.parameters.values()):
                if param.kind is param.POSITIONAL_ONLY: # pragma: nocover
                    call_args.append(args[i])
                elif param.kind is param.POSITIONAL_OR_KEYWORD and param.default is param.empty:
                    call_args.append(args[i])
                elif param.kind is param.POSITIONAL_OR_KEYWORD and param.default is not param.empty:
                    command_arg = self.args[param.name]

                    if command_arg.positional:
                        call_args.append(args[i])
                    else:
                        call_kwargs[param.name] = kwargs.get(param.name, param.default)
                elif param.kind is param.VAR_POSITIONAL:
                    call_args.extend(args[i:])
                elif param.kind is param.KEYWORD_ONLY:
                    call_kwargs[param.name] = kwargs.get(param.name, param.default)
                else: # pragma: nocover
                    raise NotImplementedError(param.kind)

            return call_args, call_kwargs

    if _function is None:
        return Command
    else:
        return Command(_function)

class CommandArgument(object):
    def __init__(self, name, display_name=None, type=None, metavar=None, help=None, short_option=None, default=None, positional=False):
        self.name = name
        self.display_name = nvl(display_name, self.name.replace("_", "-"))
        self.type = type
        self.metavar = nvl(metavar, self.display_name.upper())
        self.help = help
        self.short_option = short_option
        self.default = default
        self.positional = positional

        self.optional = False
        self.multiple = False

    def __repr__(self):
        return "argument '{0}' (default {1})".format(self.name, repr(self.default))

class PlanoCommand(BaseCommand):
    def __init__(self, planofile=None):
        self.planofile = planofile

        description = "Run commands defined as Python functions"

        self.pre_parser = BaseArgumentParser(description=description, add_help=False)
        self.pre_parser.add_argument("-h", "--help", action="store_true",
                                     help="Show this help message and exit")

        if self.planofile is None:
            self.pre_parser.add_argument("-f", "--file",
                                         help="Load commands from FILE (default 'Planofile' or '.planofile')")

        self.parser = _argparse.ArgumentParser(parents=(self.pre_parser,), add_help=False, allow_abbrev=False)

        self.attached_commands = _collections.OrderedDict()
        self.running_commands = list()

        self.default_command_name = None
        self.default_command_args = None
        self.default_command_kwargs = None

    def parse_args(self, args):
        pre_args, _ = self.pre_parser.parse_known_args(args)

        self._load_config(getattr(pre_args, "file", None))
        self._process_commands()

        return self.parser.parse_args(args)

    def init(self, args):
        # XXX Can this move to the top of run?
        if args.help or args.command is None and self.default_command_name is None:
            self.parser.print_help()
            self.init_only = True
            return

        if args.command is None:
            self.selected_command = self.attached_commands[self.default_command_name]
            self.command_args = self.default_command_args
            self.command_kwargs = self.default_command_kwargs
        else:
            self.selected_command = self.attached_commands[args.command]
            self.command_args = list()
            self.command_kwargs = dict()

            for arg in self.selected_command.args.values():
                if arg.positional:
                    if arg.multiple:
                        self.command_args.extend(getattr(args, arg.name))
                    else:
                        self.command_args.append(getattr(args, arg.name))
                else:
                    self.command_kwargs[arg.name] = getattr(args, arg.name)

    def run(self):
        with Timer() as timer:
            self.selected_command(*self.command_args, **self.command_kwargs)

        cprint("OK", color="green", file=_sys.stderr, end="")
        cprint(" ({0})".format(format_duration(timer.elapsed_time)), color="magenta", file=_sys.stderr)

    def set_default_command(self, name, *args, **kwargs):
        self.default_command_name = name
        self.default_command_args = args
        self.default_command_kwargs = kwargs

    def _load_config(self, planofile):
        if planofile is None:
            planofile = self.planofile

        if planofile is not None and is_dir(planofile):
            planofile = self._find_planofile(planofile)

        if planofile is not None and not is_file(planofile):
            exit("Planofile '{0}' not found", planofile)

        if planofile is None:
            planofile = self._find_planofile(get_current_dir())

        if planofile is None:
            return

        debug("Loading '{0}'", planofile)

        _sys.path.insert(0, join(get_parent_dir(planofile), "python"))

        scope = dict(globals())
        scope["plano"] = self

        try:
            with open(planofile) as f:
                exec(f.read(), scope)
        except Exception as e:
            error(e)
            exit("Failure loading {0}: {1}", repr(planofile), str(e))

        for var in scope.values():
            if callable(var) and hasattr(var, "attach"):
                var.attach(self)

    def _find_planofile(self, dir):
        for name in ("Planofile", ".planofile"):
            path = join(dir, name)

            if is_file(path):
                return path

    def _process_commands(self):
        subparsers = self.parser.add_subparsers(title="commands", dest="command")

        for command in self.attached_commands.values():
            subparser = subparsers.add_parser(command.name, help=command.help,
                                              description=nvl(command.description, command.help),
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
                        flag_args.append("-{0}".format(arg.short_option))

                    flag_args.append("--{0}".format(arg.display_name))

                    help = arg.help

                    if arg.default not in (None, False):
                        if help is None:
                            help = "Default value is {0}".format(repr(arg.default))
                        else:
                            help += " (default {0})".format(repr(arg.default))

                    if arg.default is False:
                        subparser.add_argument(*flag_args, dest=arg.name, default=arg.default, action="store_true", help=help)
                    else:
                        subparser.add_argument(*flag_args, dest=arg.name, default=arg.default, metavar=arg.metavar, type=arg.type, help=help)

            _capitalize_help(subparser)

if PLANO_DEBUG: # pragma: nocover
    enable_logging(level="debug")

if __name__ == "__main__": # pragma: nocover
    PlanoCommand().main()
