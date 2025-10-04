#!/usr/local/autopkg/python
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

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Mock the imports before importing the module
sys.modules["packager"] = MagicMock()
sys.modules["launch2"] = MagicMock()

# Load autopkgserver as a module by reading and executing it
autopkgserver_path = Path(__file__).parent.parent / "autopkgserver" / "autopkgserver"
with open(autopkgserver_path, "r", encoding="utf-8") as f:
    autopkgserver_code = f.read()

# Create a module
autopkgserver = types.ModuleType("autopkgserver")
autopkgserver.__file__ = str(autopkgserver_path)
sys.modules["autopkgserver"] = autopkgserver

# Execute the code in the module's namespace
exec(autopkgserver_code, autopkgserver.__dict__)

# Import what we need
APPNAME = autopkgserver.APPNAME
SOCKET = autopkgserver.SOCKET
VERSION = autopkgserver.VERSION
AutoPkgServer = autopkgserver.AutoPkgServer
AutoPkgServerError = autopkgserver.AutoPkgServerError
PkgHandler = autopkgserver.PkgHandler
chown_structure = autopkgserver.chown_structure
main = autopkgserver.main
request_structure = autopkgserver.request_structure


class TestPkgHandler(unittest.TestCase):
    """Test class for PkgHandler."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = PkgHandler(
            request=MagicMock(), client_address=("127.0.0.1", 12345), server=MagicMock()
        )
        self.handler.log = MagicMock()

    def test_verify_request_syntax_valid_request(self):
        """Should return True and no errors for valid request."""
        plist = {
            "pkgroot": "/tmp/pkgroot",
            "pkgdir": "/tmp/output",
            "pkgname": "TestPackage",
            "pkgtype": "flat",
            "id": "com.example.test",
            "version": "1.0.0",
            "infofile": "",
            "chown": [],
            "scripts": "",
        }
        syntax_ok, errors = self.handler.verify_request_syntax(plist)

        self.assertTrue(syntax_ok)
        self.assertEqual(errors, [])

    def test_verify_request_syntax_not_a_dict(self):
        """Should return False and error when plist is not a dictionary."""
        plist = ["not", "a", "dict"]
        syntax_ok, errors = self.handler.verify_request_syntax(plist)

        self.assertFalse(syntax_ok)
        self.assertEqual(len(errors), 1)
        self.assertIn("Request root is not a dictionary", errors[0])

    def test_verify_request_syntax_missing_required_key(self):
        """Should return False and error when required key is missing."""
        plist = {
            "pkgroot": "/tmp/pkgroot",
            "pkgdir": "/tmp/output",
            "pkgname": "TestPackage",
            "pkgtype": "flat",
            # Missing 'id', 'version', etc.
        }
        syntax_ok, errors = self.handler.verify_request_syntax(plist)

        self.assertFalse(syntax_ok)
        self.assertGreater(len(errors), 0)
        # Check that at least one error mentions a missing key
        self.assertTrue(any("missing key" in error for error in errors))

    def test_verify_request_syntax_wrong_type(self):
        """Should return False and error when key has wrong type."""
        plist = {
            "pkgroot": "/tmp/pkgroot",
            "pkgdir": "/tmp/output",
            "pkgname": "TestPackage",
            "pkgtype": "flat",
            "id": "com.example.test",
            "version": "1.0.0",
            "infofile": "",
            "chown": "not_a_list",  # Should be a list
            "scripts": "",
        }
        syntax_ok, errors = self.handler.verify_request_syntax(plist)

        self.assertFalse(syntax_ok)
        self.assertTrue(any("not of type" in error for error in errors))

    def test_verify_request_syntax_invalid_pkgtype(self):
        """Should return False and error for non-flat package type."""
        plist = {
            "pkgroot": "/tmp/pkgroot",
            "pkgdir": "/tmp/output",
            "pkgname": "TestPackage",
            "pkgtype": "bundle",  # Not supported
            "id": "com.example.test",
            "version": "1.0.0",
            "infofile": "",
            "chown": [],
            "scripts": "",
        }
        syntax_ok, errors = self.handler.verify_request_syntax(plist)

        self.assertFalse(syntax_ok)
        self.assertTrue(any("pkgtype must be flat" in error for error in errors))

    def test_verify_request_syntax_invalid_chown_entry(self):
        """Should return False and error when chown entry is invalid."""
        plist = {
            "pkgroot": "/tmp/pkgroot",
            "pkgdir": "/tmp/output",
            "pkgname": "TestPackage",
            "pkgtype": "flat",
            "id": "com.example.test",
            "version": "1.0.0",
            "infofile": "",
            "chown": ["not_a_dict"],  # Should be list of dicts
            "scripts": "",
        }
        syntax_ok, errors = self.handler.verify_request_syntax(plist)

        self.assertFalse(syntax_ok)
        self.assertTrue(any("chown entry" in error for error in errors))

    def test_verify_request_syntax_valid_chown_entry(self):
        """Should return True for valid chown entry."""
        plist = {
            "pkgroot": "/tmp/pkgroot",
            "pkgdir": "/tmp/output",
            "pkgname": "TestPackage",
            "pkgtype": "flat",
            "id": "com.example.test",
            "version": "1.0.0",
            "infofile": "",
            "chown": [
                {
                    "path": "Applications",
                    "user": "root",
                    "group": "wheel",
                    "mode": "0755",
                }
            ],
            "scripts": "",
        }
        syntax_ok, errors = self.handler.verify_request_syntax(plist)

        self.assertTrue(syntax_ok)
        self.assertEqual(errors, [])

    def test_verify_request_syntax_chown_missing_key(self):
        """Should return False when chown entry is missing required key."""
        plist = {
            "pkgroot": "/tmp/pkgroot",
            "pkgdir": "/tmp/output",
            "pkgname": "TestPackage",
            "pkgtype": "flat",
            "id": "com.example.test",
            "version": "1.0.0",
            "infofile": "",
            "chown": [
                {"path": "Applications", "user": "root"}  # Missing group and mode
            ],
            "scripts": "",
        }
        syntax_ok, errors = self.handler.verify_request_syntax(plist)

        self.assertFalse(syntax_ok)
        self.assertTrue(any("chown entry is missing" in error for error in errors))

    def test_verify_request_syntax_chown_with_int_uid_gid(self):
        """Should accept integer uid/gid in chown entry."""
        plist = {
            "pkgroot": "/tmp/pkgroot",
            "pkgdir": "/tmp/output",
            "pkgname": "TestPackage",
            "pkgtype": "flat",
            "id": "com.example.test",
            "version": "1.0.0",
            "infofile": "",
            "chown": [{"path": "Applications", "user": 0, "group": 0, "mode": "0755"}],
            "scripts": "",
        }
        syntax_ok, errors = self.handler.verify_request_syntax(plist)

        self.assertTrue(syntax_ok)
        self.assertEqual(errors, [])


class TestAutoPkgServer(unittest.TestCase):
    """Test class for AutoPkgServer."""

    @patch("autopkgserver.socket.fromfd")
    def test_init_creates_socket(self, mock_fromfd):
        """Should create socket from file descriptor."""
        mock_socket = MagicMock()
        mock_fromfd.return_value = mock_socket

        server = AutoPkgServer(socket_fd=3, RequestHandlerClass=PkgHandler)

        mock_fromfd.assert_called_once()
        mock_socket.listen.assert_called_once_with(server.request_queue_size)
        self.assertFalse(server.timed_out)

    @patch("autopkgserver.socket.fromfd")
    def test_handle_timeout_sets_flag(self, mock_fromfd):
        """Should set timed_out flag when handle_timeout is called."""
        mock_socket = MagicMock()
        mock_fromfd.return_value = mock_socket

        server = AutoPkgServer(socket_fd=3, RequestHandlerClass=PkgHandler)
        self.assertFalse(server.timed_out)

        server.handle_timeout()
        self.assertTrue(server.timed_out)

    @patch("autopkgserver.socket.fromfd")
    @patch("autopkgserver.logging.getLogger")
    @patch("autopkgserver.logging.StreamHandler")
    @patch("autopkgserver.logging.handlers.RotatingFileHandler")
    def test_setup_logging_success(
        self, mock_file_handler, mock_stream_handler, mock_get_logger, mock_fromfd
    ):
        """Should set up logging handlers successfully."""
        mock_socket = MagicMock()
        mock_fromfd.return_value = mock_socket
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        server = AutoPkgServer(socket_fd=3, RequestHandlerClass=PkgHandler)
        server.setup_logging()

        mock_get_logger.assert_called_once_with(APPNAME)
        mock_logger.setLevel.assert_called_once()
        self.assertEqual(mock_logger.addHandler.call_count, 2)

    @patch("autopkgserver.socket.fromfd")
    @patch("autopkgserver.logging.getLogger")
    @patch("autopkgserver.logging.handlers.RotatingFileHandler")
    def test_setup_logging_raises_on_file_error(
        self, mock_file_handler, mock_get_logger, mock_fromfd
    ):
        """Should raise AutoPkgServerError when file logging fails."""
        mock_socket = MagicMock()
        mock_fromfd.return_value = mock_socket
        mock_get_logger.return_value = MagicMock()
        mock_file_handler.side_effect = OSError(13, "Permission denied")

        server = AutoPkgServer(socket_fd=3, RequestHandlerClass=PkgHandler)

        with self.assertRaises(AutoPkgServerError) as ctx:
            server.setup_logging()

        self.assertIn("Can't open log", str(ctx.exception))


class TestMain(unittest.TestCase):
    """Test class for main function."""

    @patch("autopkgserver.os.geteuid")
    def test_main_requires_root(self, mock_geteuid):
        """Should return 1 if not running as root."""
        mock_geteuid.return_value = 501  # Not root

        with patch("autopkgserver.time.sleep"):
            result = main([])

        self.assertEqual(result, 1)


class TestConstants(unittest.TestCase):
    """Test class for module constants."""

    def test_appname_constant(self):
        """APPNAME should be set correctly."""
        self.assertEqual(APPNAME, "autopkgserver")

    def test_version_constant(self):
        """VERSION should be set and be a valid version string."""
        self.assertIsInstance(VERSION, str)
        self.assertRegex(VERSION, r"^\d+\.\d+")

    def test_socket_constant(self):
        """SOCKET should be set correctly."""
        self.assertEqual(SOCKET, "/var/run/autopkgserver")

    def test_request_structure_has_required_keys(self):
        """request_structure should contain all required keys."""
        required_keys = [
            "pkgroot",
            "pkgdir",
            "pkgname",
            "pkgtype",
            "id",
            "version",
            "infofile",
            "chown",
            "scripts",
        ]
        for key in required_keys:
            self.assertIn(key, request_structure)

    def test_chown_structure_has_required_keys(self):
        """chown_structure should contain all required keys."""
        required_keys = ["path", "user", "group", "mode"]
        for key in required_keys:
            self.assertIn(key, chown_structure)


if __name__ == "__main__":
    unittest.main()
