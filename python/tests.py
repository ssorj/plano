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

from plano import *

def open_test_session(session):
    enable_logging(level="warn")

# XXX which string_replace working_env random_port

# XXX make_dir, change_dir, list_dir, working_dir, find*
# def test_dir_operations(session):

# XXX read*, write*, append*, prepend*, touch, tail*
# def test_file_io(session):

# def test_archive_operations(session):

# def test_port_operations(session):

# XXX rename remove make_link read_link
def test_file_operations(session):
    with temp_working_dir():
        touch("some-file")

        assert exists("some-file")

        make_dir("some-dir")
        touch("some-dir")

    temp_dir = make_temp_dir()

    alpha_dir = make_dir(join(temp_dir, "alpha-dir"))
    alpha_file = touch(join(alpha_dir, "alpha-file"))

    beta_dir = make_dir(join(temp_dir, "beta-dir"))
    beta_file = touch(join(beta_dir, "beta-file"))

    copied_file = copy(alpha_file, beta_dir)
    assert copied_file == join(beta_dir, "alpha-file")

    copied_dir = copy(alpha_dir, beta_dir)
    assert copied_dir == join(beta_dir, "alpha-dir")

    moved_file = move(beta_file, alpha_dir)
    assert moved_file == join(alpha_dir, "beta-file")

    moved_dir = move(beta_dir, alpha_dir)
    assert moved_dir == join(alpha_dir, "beta-dir")

def test_logging(session):
    with temp_file() as f:
        disable_logging()
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

            flush()
        except KeyboardInterrupt:
            raise
        except:
            print(read(f))
            raise
        finally:
            enable_logging(output=STDERR, level="warn")

# XXX parent_dir, file_name, name_stem, name_extension, program_name
def test_path_operations(session):
    result = get_home_dir()
    assert result == ENV["HOME"], result

    result = get_home_dir("alice")
    assert result.endswith("alice"), result

    curr_dir = get_current_dir()

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

# XXX temp_working_dir
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

    with temp_working_dir() as d:
        list_dir(d)

def test_unique_id(session):
    id1 = get_unique_id()
    id2 = get_unique_id()
    assert id1 != id2

    result = get_unique_id(1)
    assert len(result) == 2

    result = get_unique_id(16)
    assert len(result) == 32

# XXX Much too limited
def test_process_operations(session):
    call("date", quiet=True)

    with open(make_temp_file(), "w") as temp:
        call("date", output=temp)
