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
import signal as _signal
import socket as _socket
import sys as _sys
import threading as _threading

try:
    import http.server as _http
except ImportError: # pragma: nocover
    import BaseHTTPServer as _http

from plano import *

def open_test_session(session):
    if session.verbose:
        enable_logging(level="debug")

def test_targets(session):
    planofile = get_absolute_path("scripts/test_project.planofile")

    def invoke(*args):
        command = PlanoCommand()
        command.main(["--verbose", "-f", planofile] + list(args))

    with working_dir():
        touch("bin/command1.in")
        touch("bin/command2")
        touch("python/lib.py")
        touch("python/lib.pyc")
        touch("python/__pycache__")
        touch("files/yellow.txt")

        invoke("build")
        invoke("build", "--prefix", "/who")
        # invoke("test")
        # invoke("test", "--verbose")
        # invoke("test", "--list")
        invoke("test", "--include", "test_hello", "--list")
        invoke("install")
        invoke("install", "--dest-dir", "/what")
        invoke("clean")
        invoke("env")

        try:
            invoke("modules", "--remote", "--recursive")
            assert False
        except PlanoException:
            pass
