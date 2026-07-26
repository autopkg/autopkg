#!/usr/local/autopkg/python
#
# Copyright 2026 Elliot Jordan
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from autopkglib import ProcessorError
from autopkglib.InstallFromDMG import InstallFromDMG


class TestInstallFromDMG(unittest.TestCase):
    """Test class for the InstallFromDMG processor."""

    def setUp(self):
        self.processor = InstallFromDMG()
        self.processor.env = {}

    def _socketpair(self):
        ours, theirs = socket.socketpair()
        self.addCleanup(ours.close)
        self.addCleanup(theirs.close)
        self.processor.socket = ours
        return ours, theirs

    def test_send_request_leaves_the_socket_usable_for_disconnect(self):
        """Reading the reply must not close the socket's descriptor.

        os.fdopen(socket.fileno()) took ownership of the descriptor and closed
        it when the reader closed, so disconnect() went on to close a
        descriptor the socket no longer owned. Here that went unnoticed:
        disconnect() swallows OSError."""
        ours, theirs = self._socketpair()
        theirs.sendall(b"OK:copied\n")

        with patch("plistlib.dumps", return_value=b""):
            result = self.processor.send_request({"items_to_copy": []})

        self.assertEqual(result, "copied")
        # Fails with EBADF if the reply reader closed the socket's descriptor.
        ours.sendall(b"still open\n")
        self.processor.disconnect()
        self.assertEqual(ours.fileno(), -1)

    def test_send_request_empty_reply(self):
        """An empty reply should report that autopkginstalld sent no reply."""
        _ours, theirs = self._socketpair()
        # Half-close so the reply read hits EOF while the request send still
        # succeeds, as it would if the daemon died after accepting.
        theirs.shutdown(socket.SHUT_WR)

        with patch("plistlib.dumps", return_value=b""):
            with self.assertRaisesRegex(
                ProcessorError, "No reply from autopkginstalld"
            ):
                self.processor.send_request({"items_to_copy": []})


if __name__ == "__main__":
    unittest.main()
