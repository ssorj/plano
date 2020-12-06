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
import codecs as _codecs
import collections as _collections
import fnmatch as _fnmatch
import getpass as _getpass
import inspect as _inspect
import json as _json
import os as _os
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

LINE_SEP = _os.linesep
PATH_SEP = _os.sep
PATH_VAR_SEP = _os.pathsep
ENV = _os.environ
ARGS = _sys.argv

STDIN = _sys.stdin
STDOUT = _sys.stdout
STDERR = _sys.stderr
DEVNULL = _os.devnull

PYTHON2 = _sys.version_info[0] == 2

_logging_levels = (
    "debug",
    "notice",
    "warn",
    "error",
)

_debug = _logging_levels.index("debug")
_notice = _logging_levels.index("notice")
_warn = _logging_levels.index("warn")
_error = _logging_levels.index("error")

_logging_output = None
_logging_threshold = _notice

def enable_logging(level="warn", output=None):
    if level == "warning":
        level = "warn"

    assert level in _logging_levels

    global _logging_threshold
    _logging_threshold = _logging_levels.index(level)

    if _is_string(output):
        output = open(output, "w")

    global _logging_output
    _logging_output = output

def disable_logging():
    global _logging_threshold
    _logging_threshold = 4

def fail(message, *args):
    error(message, *args)

    if isinstance(message, BaseException):
        raise message

    raise PlanoException(message.format(*args))

def error(message, *args):
    _print_message("Error", message, args)

def warn(message, *args):
    if _logging_threshold <= _warn:
        _print_message("Warning", message, args)

def notice(message, *args):
    if _logging_threshold <= _notice:
        _print_message(None, message, args)

def debug(message, *args):
    if _logging_threshold <= _debug:
        _print_message("Debug", message, args)

def exit(arg=None, *args):
    if arg in (0, None):
        _sys.exit()

    if _is_string(arg):
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

def _print_message(category, message, args):
    out = nvl(_logging_output, _sys.stderr)

    if isinstance(message, BaseException) and hasattr(message, "__traceback__"):
        print(_format_message(category, "Exception:", []), file=out)
        _traceback.print_exception(type(message), message, message.__traceback__, file=out)
    else:
        message = _format_message(category, message, args)
        print(message, file=out)

    out.flush()

def _format_message(category, message, args):
    if not _is_string(message):
        message = str(message)

    if args:
        message = message.format(*args)

    if len(message) > 0 and message[0].islower():
        message = message[0].upper() + message[1:]

    if category:
        message = "{0}: {1}".format(category, message)

    program = get_program_name()
    message = "{0}: {1}".format(program, message)

    return message

def _log(quiet, message, *args):
    if quiet:
        debug(message, *args)
    else:
        notice(message, *args)

def eprint(*args, **kwargs):
    print(*args, file=_sys.stderr, **kwargs)

def flush():
    STDOUT.flush()
    STDERR.flush()

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
    def __init__(self, color, bright=False, file=STDOUT):
        elems = [_color_codes[color]]

        if bright:
            elems.append(";1")

        elems.append("m")

        self.color = "".join(elems)
        self.file = file

        self.has_colors = hasattr(self.file, "isatty") and self.file.isatty()

    def __enter__(self):
        if self.has_colors:
            print(self.color, file=self.file, end="")

    def __exit__(self, exc_type, exc_value, traceback):
        if self.has_colors:
            print("\u001b[0m", file=self.file, end="")
            self.file.flush()

get_absolute_path = _os.path.abspath
normalize_path = _os.path.normpath
get_real_path = _os.path.realpath
get_relative_path = _os.path.relpath
exists = _os.path.lexists
is_absolute = _os.path.isabs
is_dir = _os.path.isdir
is_file = _os.path.isfile
is_link = _os.path.islink
get_file_size = _os.path.getsize

join = _os.path.join
split = _os.path.split
split_extension = _os.path.splitext

get_current_dir = _os.getcwd

def get_home_dir(user=None):
    return _os.path.expanduser("~{0}".format(user or ""))

def get_user():
    return _getpass.getuser()

def get_hostname():
    return _socket.gethostname()

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

def get_program_name(command=None):
    if command is None:
        args = ARGS
    else:
        args = command.split()

    for arg in args:
        if "=" not in arg:
            return get_base_name(arg)

def which(program_name):
    assert "PATH" in ENV

    for dir_ in ENV["PATH"].split(PATH_VAR_SEP):
        program = join(dir_, program_name)

        if _os.access(program, _os.X_OK):
            return program

def check_program(program_name):
    if which(program_name) is None:
        raise PlanoException("Program '{0}' is unavailable".format(program_name))

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

def touch(file):
    try:
        _os.utime(file, None)
    except OSError:
        append(file, "")

    return file

def tail(file, n):
    return "".join(tail_lines(file, n))

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

def tail_lines(file, n):
    assert n >= 0

    with _codecs.open(file, encoding="utf-8", mode="r") as f:
        pos = n + 1
        lines = list()

        while len(lines) <= n:
            try:
                f.seek(-pos, 2)
            except IOError:
                f.seek(0)
                break
            finally:
                lines = f.readlines()

            pos *= 2

        return lines[-n:]

def read_json(file):
    with _codecs.open(file, encoding="utf-8", mode="r") as f:
        return _json.load(f)

def write_json(file, obj):
    make_parent_dir(file, quiet=True)

    with _codecs.open(file, encoding="utf-8", mode="w") as f:
        _json.dump(obj, f, indent=4, separators=(",", ": "), sort_keys=True)

    return file

def parse_json(json):
    return _json.loads(json)

def emit_json(obj):
    return _json.dumps(obj, indent=4, separators=(",", ": "), sort_keys=True)

def _run_curl(method, url, content=None, content_file=None, content_type=None, output_file=None, insecure=False):
    check_program("curl")

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

def get_temp_dir():
    return _tempfile.gettempdir()

def get_user_temp_dir():
    try:
        return ENV["XDG_RUNTIME_DIR"]
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

# No args constructor gets a temp dir
class working_dir(object):
    def __init__(self, dir=None, remove=False, quiet=False):
        self.dir = dir
        self.prev_dir = None
        self.remove = remove
        self.quiet = quiet

        if self.dir is None:
            self.dir = make_temp_dir()
            self.remove = True

    def __enter__(self):
        if self.dir == ".":
            return

        _log(self.quiet, "Entering directory '{0}'", get_absolute_path(self.dir))

        make_dir(self.dir, quiet=True)

        self.prev_dir = change_dir(self.dir, quiet=True)

        return self.dir

    def __exit__(self, exc_type, exc_value, traceback):
        if self.dir == ".":
            return

        _log(self.quiet, "Returning to directory '{0}'", get_absolute_path(self.prev_dir))

        change_dir(self.prev_dir, quiet=True)

        if self.remove:
            remove(self.dir, quiet=True)

# Length in bytes, renders twice as long in hex
def get_unique_id(length=16):
    assert length >= 1
    assert length <= 16

    uuid_bytes = _uuid.uuid4().bytes
    uuid_bytes = uuid_bytes[:length]

    return _binascii.hexlify(uuid_bytes).decode("utf-8")

def base64_encode(string):
    return _base64.b64encode(string)

def base64_decode(string):
    return _base64.b64decode(string)

def url_encode(string):
    return _urlparse.quote_plus(string)

def url_decode(string):
    return _urlparse.unquote_plus(string)

# symlinks=True - Preserve symlinks
# inside=True - Place from_path inside to_path if to_path is a directory
def copy(from_path, to_path, symlinks=True, inside=True, quiet=False):
    _log(quiet, "Copying '{0}' to '{1}'", from_path, to_path)

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
    _log(quiet, "Moving '{0}' to '{1}'", from_path, to_path)

    to_path = copy(from_path, to_path, inside=inside, quiet=True)
    remove(from_path)

    return to_path

def remove(path, quiet=False):
    _log(quiet, "Removing '{0}'", path)

    if not exists(path):
        return

    if is_dir(path):
        _shutil.rmtree(path, ignore_errors=True)
    else:
        _os.remove(path)

    return path

def make_link(path, linked_path, quiet=False):
    _log(quiet, "Making link '{0}' to '{1}'", path, linked_path)

    make_parent_dir(path, quiet=True)
    remove(path, quiet=True)

    _os.symlink(linked_path, path)

    return path

def read_link(path):
    return _os.readlink(path)

def find(dir, *patterns):
    matched_paths = set()

    if not patterns:
        patterns = ("*",)

    for root, dirs, files in _os.walk(dir):
        for pattern in patterns:
            matched_dirs = _fnmatch.filter(dirs, pattern)
            matched_files = _fnmatch.filter(files, pattern)

            matched_paths.update([join(root, x) for x in matched_dirs])
            matched_paths.update([join(root, x) for x in matched_files])

    return sorted(matched_paths)

def configure_file(input_file, output_file, substitutions, quiet=False):
    _log(quiet, "Configuring '{0}' for output '{1}'", input_file, output_file)

    content = read(input_file)

    for name, value in substitutions.items():
        content = content.replace("@{0}@".format(name), value)

    write(output_file, content)

    _shutil.copymode(input_file, output_file)

    return output_file

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
def change_dir(dir_, quiet=False):
    _log(quiet, "Changing directory to '{0}'", dir_)

    prev_dir = get_current_dir()

    if not dir_:
        return prev_dir

    _os.chdir(dir_)

    return prev_dir

def list_dir(dir_=None, *patterns):
    if dir_ is None:
        dir_ = get_current_dir()

    assert is_dir(dir_)

    names = _os.listdir(dir_)

    if not patterns:
        return sorted(names)

    matched_names = set()

    for pattern in patterns:
        matched_names.update(_fnmatch.filter(names, pattern))

    return sorted(matched_names)

class working_env(object):
    def __init__(self, **env_vars):
        self.env_vars = env_vars
        self.prev_env_vars = dict()

    def __enter__(self):
        for name, value in self.env_vars.items():
            if name in ENV:
                self.prev_env_vars[name] = ENV[name]

            ENV[name] = str(value)

    def __exit__(self, exc_type, exc_value, traceback):
        for name, value in self.env_vars.items():
            if name in self.prev_env_vars:
                ENV[name] = self.prev_env_vars[name]
            else:
                del ENV[name]

## Process operations

def get_process_id():
    return _os.getpid()

def sleep(seconds, quiet=False):
    _log(quiet, "Sleeping for {0} {1}", seconds, plural("second", seconds))

    _time.sleep(seconds)

# quiet=False - Don't log at notice level
# stash=False - No output unless there is an error
# output=<file> - Send stdout and stderr to a file
# stdin=<file> - XXX
# stdout=<file> - Send stdout to a file
# stderr=<file> - Send stderr to a file
# shell=False - XXX
def start(command, stdin=None, stdout=None, stderr=None, output=None, shell=False, stash=False, quiet=False):
    _log(quiet, "Starting '{0}'", command)

    if output is not None:
        stdout, stderr = output, output

    if _is_string(stdin):
        stdin = open(stdin, "r")

    if _is_string(stdout):
        stdout = open(stdout, "w")

    if _is_string(stderr):
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
        args = command
    else:
        args = _shlex.split(command)

    try:
        proc = PlanoProcess(args, stdin=stdin, stdout=stdout, stderr=stderr, shell=shell, close_fds=True, stash_file=stash_file)
    except OSError as e:
        raise PlanoException("Command '{0}': {1}".format(command, str(e)))

    debug("{0} started", proc)

    return proc

def stop(proc, quiet=False):
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

    # XXX Timeout

    return wait(proc, quiet=True)

def kill(proc, quiet=False):
    _log(quiet, "Killing {0}", proc)

    proc.terminate()

def wait(proc, check=False, quiet=False):
    _log(quiet, "Waiting for {0} to exit", proc)

    proc.wait()

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
    _log(quiet, "Running '{0}'", command)

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
    _log(quiet, "Calling '{0}'", command)

    proc = run(command, stdin=_subprocess.PIPE, stdout=_subprocess.PIPE, stderr=_subprocess.PIPE,
               input=input, shell=shell, check=True, quiet=True)

    return proc.stdout_result

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
        return "process {0} ('{1}')".format(self.pid, " ".join(self.args))

class PlanoException(Exception):
    pass

class PlanoProcessError(_subprocess.CalledProcessError, PlanoException):
    def __init__(self, proc):
        super(PlanoProcessError, self).__init__(proc.exit_code, " ".join(proc.args))

def default_sigterm_handler(signum, frame):
    for proc in _child_processes:
        if proc.poll() is None:
            proc.terminate()

    exit(-(_signal.SIGTERM))

_signal.signal(_signal.SIGTERM, default_sigterm_handler)

def make_archive(input_dir, output_file=None, quiet=False):
    check_program("tar")

    archive_stem = get_base_name(input_dir)

    if output_file is None:
        output_file = "{0}.tar.gz".format(join(get_current_dir(), archive_stem))

    _log(quiet, "Making archive '{0}' from dir '{1}'", output_file, input_dir)

    with working_dir(get_parent_dir(input_dir)):
        run("tar -czf {0} {1}".format(output_file, archive_stem))

    return output_file

def extract_archive(input_file, output_dir=None, quiet=False):
    check_program("tar")

    if output_dir is None:
        output_dir = get_current_dir()

    _log(quiet, "Extracting archive '{0}' to dir '{1}'", input_file, output_dir)

    input_file = get_absolute_path(input_file)

    with working_dir(output_dir):
        run("tar -xf {0}".format(input_file))

    return output_dir

def rename_archive(input_file, new_archive_stem, quiet=False):
    _log(quiet, "Renaming archive '{0}' with stem '{1}'", input_file, new_archive_stem)

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

def get_random_port(min=49152, max=65535):
    return _random.randint(min, max)

def wait_for_port(port, host="", timeout=30, quiet=False):
    _log(quiet, "Waiting for port {0}", port)

    if _is_string(port):
        port = int(port)

    sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)

    start = _time.time()

    try:
        while True:
            if sock.connect_ex((host, port)) == 0:
                return

            sleep(0.1, quiet=True)

            if _time.time() - start > timeout:
                fail("Timed out waiting for port {0} to open", port)
    finally:
        sock.close()

def replace(string, expr, replacement, count=0):
    return _re.sub(expr, replacement, string, count)

def nvl(value, substitution, template=None):
    if value is None:
        return substitution

    if template is not None:
        return template.format(value)

    return value

def shorten(string, max_, ellipsis=""):
    assert max_ is None or isinstance(max_, int)

    if string is None:
        return ""

    if max_ is None or len(string) < max_:
        return string
    else:
        if ellipsis:
            string = string + ellipsis
            end = max(0, max_ - len(ellipsis))
            return string[0:end] + ellipsis
        else:
            return string[0:max_]

def plural(noun, count=0):
    if noun in (None, ""):
        return ""

    if count == 1:
        return noun

    if noun.endswith("s"):
        return "{0}ses".format(noun)

    return "{0}s".format(noun)

def _is_string(obj):
    try:
        return isinstance(obj, basestring)
    except NameError:
        return isinstance(obj, str)

try:
    import importlib as _importlib

    def _import_module(name):
        return _importlib.import_module(name)
except ImportError: # pragma: nocover
    def _import_module(name):
        return __import__(name, fromlist=[""])

_target_help = {
    "build":    "Build artifacts from source",
    "clean":    "Clean up the source tree",
    "dist":     "Generate distribution artifacts",
    "install":  "Install the built artifacts on your system",
    "test":     "Run the tests",
}

def target(_function=None, extends=None, name=None, default=False, help=None, description=None, requires=None, args=None):
    class decorator(object):
        def __init__(self, function):
            self.function = function
            self.extends = extends
            self.default = default

            self.called = False

            if self.extends is None:
                self.name = nvl(name, function.__name__.replace("_", "-"))
                self.help = nvl(help, _target_help.get(self.name))
                self.description = description
                self.requires = requires
                self.args = self.process_args(args)

                if self.name in PlanoCommand.targets:
                    debug("Target '{0}' is already defined", self.name)
            else:
                assert name is None
                assert args is None # For now, no override

                self.name = self.extends.name
                self.help = nvl(help, self.extends.help)
                self.description = nvl(description, self.extends.description)
                self.requires = nvl(requires, self.extends.requires)
                self.args = self.extends.args

            debug("Adding target '{0}'", self.name)

            PlanoCommand.targets[self.name] = self

        def process_args(self, input_args):
            input_args_by_name = {}

            if input_args is not None:
                input_args_by_name = dict(zip([x.name for x in input_args], input_args))

            output_args = list()
            names, _, _, defaults = _inspect.getargspec(self.function)
            defaults = dict(zip(reversed(names), reversed(nvl(defaults, []))))

            for name in names:
                try:
                    arg = input_args_by_name[name]
                except KeyError:
                    arg = Argument(name)

                if name in defaults:
                    arg.has_default = True

                    if defaults[name] is not None:
                        arg.default = defaults[name]

                if arg.default not in (None, False):
                    if arg.type is None:
                        arg.type = type(arg.default)

                    if _is_string(arg.default):
                        default = "'{0}'".format(arg.default)
                    else:
                        default = arg.default

                    if arg.help is None:
                        arg.help = "The default is {0}".format(default)
                    else:
                        arg.help = "{0} (default {1})".format(arg.help, default)

                output_args.append(arg)

            return output_args

        def __call__(self, *args):
            if self.called:
                return

            self.called = True

            if self.requires is not None:
                if callable(self.requires):
                    run_target(self.requires.name)
                else:
                    for target in self.requires:
                        run_target(target.name)

            PlanoCommand.running_targets.append(self)

            arrow = "--" * len(PlanoCommand.running_targets)
            displayed_args = list()

            for arg, value in zip(self.args, args):
                if arg.default == value:
                    continue

                if _is_string(value):
                    value = "\"{0}\"".format(value)
                elif value in (True, False):
                    value = str(value).lower()

                displayed_args.append("{0}={1}".format(arg.option_name, value))

            with console_color("magenta", file=STDERR):
                eprint("{0}> {1}".format(arrow, self.name), end="")

                if displayed_args:
                    eprint(" ({0})".format(", ".join(displayed_args)), end="")

                eprint()

            if self.extends is not None:
                self.extends.function(*args[:len(_inspect.getargspec(self.extends.function).args)])

            self.function(*args[:len(_inspect.getargspec(self.function).args)])

            with console_color("magenta", file=STDERR):
                eprint("<{0} {1}".format(arrow, self.name))

            PlanoCommand.running_targets.pop()

    if _function is None:
        return decorator
    else:
        return decorator(_function)

def run_target(name):
    PlanoCommand.targets[name]()

def import_targets(module_name, *target_names):
    targets = _collections.OrderedDict(PlanoCommand.targets)

    try:
        module = _import_module(module_name)

        for name in target_names:
            targets[name] = getattr(module, name)
    finally:
        PlanoCommand.targets = targets

class Argument(object):
    def __init__(self, name, option_name=None, metavar=None, type=None, help=None, default=None):
        self.name = name
        self.option_name = nvl(option_name, self.name.replace("_", "-"))
        self.metavar = nvl(metavar, self.name.replace("_", "-").upper())
        self.type = type
        self.help = help
        self.default = default

        self.has_default = False

class PlanoCommand(object):
    targets = _collections.OrderedDict()
    running_targets = list()

    def __init__(self):
        PlanoCommand.targets.clear()
        PlanoCommand.running_targets = list() # Python 3 has clear()

        description = "Run targets defined as Python functions"

        self.parser = _argparse.ArgumentParser(prog="plano", description=description, add_help=False)

        self.parser.add_argument("-h", "--help", action="store_true",
                                 help="Show this help message and exit")
        self.parser.add_argument("-f", "--file",
                                 help="Load targets from FILE (default 'Planofile' or '.planofile')")
        self.parser.add_argument("--verbose", action="store_true",
                                 help="Print detailed logging to the console")
        self.parser.add_argument("--quiet", action="store_true",
                                 help="Print no logging to the console")
        self.parser.add_argument("--init-only", action="store_true",
                                 help=_argparse.SUPPRESS)

    def init(self, args):
        starting_args, remaining_args = self.parser.parse_known_args(args)

        if starting_args.verbose:
            enable_logging(level="debug")

        if starting_args.quiet:
            disable_logging()

        self.init_only = starting_args.init_only

        self.load_config(starting_args.file)

        self.process_targets()

        if not remaining_args:
            args = _sys.argv[1:]

            for target in PlanoCommand.targets.values():
                if target.default:
                    args.append(target.name)
                    break

        args = self.parser.parse_args(args)

        if args.help or args.target is None:
            self.parser.print_help()
            self.init_only = True
            return

        self.target = PlanoCommand.targets[args.target]
        self.target_args = [getattr(args, arg.name) for arg in self.target.args]

    def load_config(self, planofile):
        if planofile is not None and not exists(planofile):
            exit("File '{0}' not found", planofile)

        planofile = nvl(planofile, "Planofile")

        if not exists(planofile):
            planofile = ".planofile"

        if not exists(planofile):
            return

        debug("Loading '{0}'", planofile)

        _sys.path.insert(0, join(get_parent_dir(planofile), "python"))

        try:
            with open(planofile) as f:
                exec(f.read(), globals())
        except Exception as e:
            error(e)
            exit("Failure loading '{0}': {1}", planofile, str(e))

    def process_targets(self):
        subparsers = self.parser.add_subparsers(title="targets", dest="target")

        for target in PlanoCommand.targets.values():
            description = nvl(target.description, target.help)
            subparser = subparsers.add_parser(target.name, help=target.help, description=description,
                                              formatter_class=_argparse.RawDescriptionHelpFormatter)

            for arg in target.args:
                if arg.has_default:
                    flag = "--{0}".format(arg.option_name)

                    if arg.default is False:
                        subparser.add_argument(flag, dest=arg.name, default=arg.default, action="store_true",
                                               help=arg.help)
                    else:
                        subparser.add_argument(flag, dest=arg.name, default=arg.default, metavar=arg.metavar,
                                               type=arg.type, help=arg.help)
                else:
                    subparser.add_argument(arg.option_name, metavar=arg.metavar, type=arg.type, help=arg.help)

            # Patch the default help text
            try:
                subparser._actions[0].help = "Show this help message and exit"
            except: # pragma: nocover
                pass

    def main(self, args=None):
        start = _time.time()

        self.init(args)

        if self.init_only:
            return

        self.target(*self.target_args)

        elapsed = _time.time() - start

        with console_color("green", file=STDERR):
            eprint("OK", end="")

        with console_color("magenta", file=STDERR):
            eprint(" ({0:.2f}s)".format(elapsed))

if __name__ == "__main__": # pragma: nocover
    command = PlanoCommand()
    command.main()
