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

import os
import socket
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from autopkglib import ProcessorError, _AutopkginstalldClient
from autopkglib.Installer import AUTOPKGINSTALLD_SOCKET, Installer


class TestInstaller(unittest.TestCase):
    """Test class for Installer processor."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.recipe_cache_dir = os.path.join(self.tmp_dir.name, "recipe-cache")
        os.makedirs(self.recipe_cache_dir)
        self.package_path = os.path.join(self.recipe_cache_dir, "Test.pkg")
        Path(self.package_path).touch()
        self.processor = Installer()
        self.processor.env = {
            "pkg_path": self.package_path,
            "RECIPE_CACHE_DIR": self.recipe_cache_dir,
        }

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_install_request_includes_recipe_cache_dir(self):
        """Should send the effective recipe cache directory to the daemon."""
        with (
            patch.object(self.processor, "connect") as mock_connect,
            patch.object(
                self.processor, "send_request", return_value="DONE"
            ) as mock_send_request,
            patch.object(self.processor, "disconnect") as mock_disconnect,
        ):
            self.processor.install()

        mock_connect.assert_called_once_with()
        mock_send_request.assert_called_once_with(
            {
                "package": self.package_path,
                "recipe_cache_dir": self.recipe_cache_dir,
            }
        )
        mock_disconnect.assert_called_once_with()

    def test_uses_shared_autopkginstalld_client(self):
        self.assertIs(Installer.connect, _AutopkginstalldClient.connect)
        self.assertIs(Installer.send_request, _AutopkginstalldClient.send_request)
        self.assertIs(Installer.disconnect, _AutopkginstalldClient.disconnect)

    def test_exposes_autopkginstalld_socket(self):
        self.assertEqual(AUTOPKGINSTALLD_SOCKET, "/var/run/autopkginstalld")

    def test_send_request_forwards_status_lines(self):
        mock_file = MagicMock()
        mock_file.readline.side_effect = ["Installing package\n", "OK:DONE\n"]
        self.processor.socket = MagicMock()
        self.processor.socket.makefile.return_value.__enter__.return_value = mock_file

        with (
            patch("plistlib.dumps", return_value=b""),
            patch.object(self.processor, "output") as mock_output,
        ):
            result = self.processor.send_request({"package": self.package_path})

        self.assertEqual(result, "DONE")
        mock_output.assert_called_once_with("Installing package")

    def test_send_request_error(self):
        mock_file = MagicMock()
        mock_file.readline.return_value = "ERROR:Installation failed\n"
        self.processor.socket = MagicMock()
        self.processor.socket.makefile.return_value.__enter__.return_value = mock_file

        with (
            patch("plistlib.dumps", return_value=b""),
            self.assertRaisesRegex(ProcessorError, "Installation failed"),
        ):
            self.processor.send_request({"package": self.package_path})

    def test_disconnect_tolerates_close_error(self):
        self.processor.socket = MagicMock()
        self.processor.socket.close.side_effect = OSError("already closed")

        self.processor.disconnect()

    def test_send_request_empty_reply(self):
        """An empty reply should report that autopkginstalld sent no reply."""
        mock_file = MagicMock()
        mock_file.readline.return_value = ""
        self.processor.socket = MagicMock()

        self.processor.socket.makefile.return_value.__enter__.return_value = mock_file

        with patch("plistlib.dumps", return_value=b""):
            with self.assertRaisesRegex(
                ProcessorError, "No reply from autopkginstalld"
            ):
                self.processor.send_request({"package": self.package_path})

        # The socket's own fd must be shared, not handed to os.fdopen, which
        # would close it here and leave disconnect() closing it a second time.
        self.processor.socket.makefile.assert_called_once_with(mode="r")

    def test_send_request_leaves_the_socket_usable_for_disconnect(self):
        """Reading the reply must not close the socket's descriptor.

        os.fdopen(socket.fileno()) took ownership of the descriptor and closed
        it when the reader closed, so disconnect() went on to close a
        descriptor the socket no longer owned -- harmless only for as long as
        nothing else had claimed that number in the meantime."""
        ours, theirs = socket.socketpair()
        self.addCleanup(ours.close)
        self.addCleanup(theirs.close)
        theirs.sendall(b"OK:/tmp/installed.pkg\n")
        self.processor.socket = ours

        with patch("plistlib.dumps", return_value=b""):
            result = self.processor.send_request({"package": self.package_path})

        self.assertEqual(result, "/tmp/installed.pkg")
        # Fails with EBADF if the reply reader closed the socket's descriptor.
        ours.sendall(b"still open\n")
        self.processor.disconnect()
        self.assertEqual(ours.fileno(), -1)


if __name__ == "__main__":
    unittest.main()
