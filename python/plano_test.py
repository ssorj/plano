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
    set_message_threshold("warn")

def test_logging(session):
    with temp_file() as file:
        with open(file, "w") as fp:
            set_message_output(fp)
            set_message_threshold("debug")

            try:
                try:
                    fail("Nooo!")
                except PlanoException:
                    pass

                error("Error!")
                warn("Warning!")
                notice("Take a look!")
                debug("By the way")
                debug("abc{}{}{}", 1, 2, 3)
                eprint("Here's a story")
                eprint("About a {}", "man named Brady")
                flush()
            except KeyboardInterrupt:
                raise
            except:
                fp.flush()
                print(read(file))
                raise
            finally:
                set_message_output(STD_ERR)
                set_message_threshold("warn")

def test_path_operations(session):
    curr_dir = current_dir()

    path = "a/b/c"
    result = absolute_path(path)

    assert result == join(curr_dir, path), result

    path = "/x/y/z"
    result = absolute_path(path)

    assert result == path, result

    path = "a//b/../c/"
    result = normalize_path(path)

    assert result == "a/c", result

    # XXX with temp_working_dir():

    path = "/a/../c"
    result = real_path(path)

    assert result == "/c", result
