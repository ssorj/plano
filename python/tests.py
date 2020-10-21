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

import os as _os
import pwd as _pwd

from plano import *

def open_test_session(session):
    enable_logging(level="warn")

# XXX
# def test_archive_operations(session):

def test_logging_operations(session):
    with temp_file() as f:
        disable_logging()

        enable_logging(output=f, level="error")
        enable_logging(output=f, level="notice")
        enable_logging(output=f, level="warn")
        enable_logging(output=f, level="warning")
        enable_logging(output=f, level="debug")

        try:
            try:
                fail("Nooo!")
            except PlanoException:
                pass

            error("Error!")
            warn("Warning!")
            notice("Take a look!")
            debug("By the way")
            debug("abc{0}{1}{2}", 1, 2, 3)
            eprint("Here's a story")
            eprint("About a", "man named Brady")

            exc = Exception("abc123")

            try:
                fail(exc)
            except Exception as e:
                assert e is exc, e

            try:
                exit()
            except SystemExit as e:
                pass

            try:
                exit("abc")
            except SystemExit as e:
                pass

            try:
                exit(123)
            except SystemExit as e:
                pass

            try:
                exit(-123)
            except SystemExit as e:
                pass

            try:
                exit(object())
            except PlanoException:
                pass

            flush()
        except:
            print(read(f))
            raise
        finally:
            enable_logging(output=STDERR, level="warn")

# XXX file_name, name_stem, name_extension, program_name
def test_path_operations(session):
    result = get_home_dir()
    assert result == ENV["HOME"], result

    result = get_home_dir("alice")
    assert result.endswith("alice"), result

    with working_dir("/"):
        curr_dir = get_current_dir()
        assert curr_dir == "/", curr_dir

        path = "a/b/c"
        result = get_absolute_path(path)
        assert result == join(curr_dir, path), result

    path = "/x/y/z"
    result = get_absolute_path(path)
    assert result == path, result

    path = "a//b/../c/"
    result = normalize_path(path)
    assert result == "a/c", result

    path = "/a/../c"
    result = get_real_path(path)
    assert result == "/c", result

    path = "/alpha/beta.ext"
    path_split = "/alpha", "beta.ext"
    path_split_extension = "/alpha/beta", ".ext"

    result = join(*path_split)
    assert result == path, result

    result = split(path)
    assert result == path_split, result

    result = split_extension(path)
    assert result == path_split_extension, result

    result = get_parent_dir("/x/y/z")
    assert result == "/x/y", result

# XXX rename remove make_link read_link
def test_file_operations(session):
    temp = make_temp_dir()

    alpha_dir = make_dir(join(temp, "alpha-dir"))
    alpha_file = touch(join(alpha_dir, "alpha-file"))

    beta_dir = make_dir(join(temp, "beta-dir"))
    beta_file = touch(join(beta_dir, "beta-file"))

    assert exists(beta_file)

    copied_file = copy(alpha_file, beta_dir)
    assert copied_file == join(beta_dir, "alpha-file")

    copied_dir = copy(alpha_dir, beta_dir)
    assert copied_dir == join(beta_dir, "alpha-dir")

    moved_file = move(beta_file, alpha_dir)
    assert moved_file == join(alpha_dir, "beta-file")

    moved_dir = move(beta_dir, alpha_dir)
    assert moved_dir == join(alpha_dir, "beta-dir")

# XXX make_dir, change_dir, list_dir, working_dir, find*
def test_dir_operations(session):
    with working_dir():
        make_dir("some-dir")
        touch("some-dir/some-file")

        result = list_dir("some-dir")
        assert len(result), len(result)

    with working_dir(quiet=True):
        touch("a-file")

def test_temp_operations(session):
    td = get_temp_dir()

    result = make_temp_file()
    assert result.startswith(td), result

    result = make_temp_file(suffix=".txt")
    assert result.endswith(".txt"), result

    result = make_temp_dir()
    assert result.startswith(td), result

    with temp_file() as f:
        write(f, "test")

    with working_dir() as d:
        list_dir(d)

def test_user_operations(session):
    user = _pwd.getpwuid(_os.getuid())[0]
    result = get_user()
    assert result == user, (result, user)

# XXX read*, write*, append*, prepend*, touch, tail*
def test_io_operations(session):
    pass

def test_process_operations(session):
    result = get_process_id()
    assert result, result

    run("date")
    run("date", stash=True)

    proc = run("echo hello", check=False)
    assert proc.exit_code == 0, proc.exit_code

    proc = run("cat /uh/uh", check=False)
    assert proc.exit_code > 0, proc.exit_code

    with temp_file() as temp:
        run("date", output=temp)

    run("date", output=DEVNULL)
    run("date", stdout=DEVNULL)
    run("date", stderr=DEVNULL)

    run("echo hello", quiet=True)
    run("echo hello | cat", shell=True)

    try:
        run("cat /whoa/not/really", stash=True)
    except PlanoProcessError:
        pass

    result = call("echo hello")
    assert result == "hello\n", result

    result = call("echo hello | cat", shell=True)
    assert result == "hello\n", result

    try:
        call("cat /whoa/not/really")
    except PlanoProcessError:
        pass

    with start("sleep 10"):
        sleep(0.5)

def test_string_operations(session):
    result = replace("ab", "a", "b")
    assert result == "bb", result

    result = replace("aba", "a", "b", count=1)
    assert result == "bba", result

    result = nvl(None, "a")
    assert result == "a", result

    result = nvl("b", "a")
    assert result == "b", result

    result = nvl("b", "a", "x{0}x")
    assert result == "xbx", result

    result = shorten("abc", 2)
    assert result == "ab", result

    result = shorten("abc", None)
    assert result == "abc", result

    result = shorten("ellipsis", 6, ellipsis="...")
    assert result == "ell...", result

    result = shorten(None, 6)
    assert result == "", result

    result = plural(None)
    assert result == "", result

    result = plural("")
    assert result == "", result

    result = plural("test")
    assert result == "tests", result

    result = plural("test", 1)
    assert result == "test", result

    result = plural("bus")
    assert result == "busses", result

    result = plural("bus", 1)
    assert result == "bus", result

    encoded_result = base64_encode(b"abc")
    decoded_result = base64_decode(encoded_result)
    assert decoded_result == b"abc", decoded_result

def test_port_operations(session):
    result = get_random_port()
    assert result >= 49152 and result <= 65535, result

    # XXX wait_for_port

def test_unique_id_operations(session):
    id1 = get_unique_id()
    id2 = get_unique_id()

    assert id1 != id2, (id1, id2)

    result = get_unique_id(1)
    assert len(result) == 2

    result = get_unique_id(16)
    assert len(result) == 32
