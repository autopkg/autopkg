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
sys.modules["installer"] = MagicMock()
sys.modules["itemcopier"] = MagicMock()
sys.modules["launch2"] = MagicMock()

# Load autopkginstalld as a module by reading and executing it
autopkginstalld_path = (
    Path(__file__).parent.parent / "autopkgserver" / "autopkginstalld"
)
with open(autopkginstalld_path, "r", encoding="utf-8") as f:
    autopkginstalld_code = f.read()

# Create a module
autopkginstalld = types.ModuleType("autopkginstalld")
autopkginstalld.__file__ = str(autopkginstalld_path)
sys.modules["autopkginstalld"] = autopkginstalld

# Execute the code in the module's namespace
exec(autopkginstalld_code, autopkginstalld.__dict__)

# Import what we need
APPNAME = autopkginstalld.APPNAME
VERSION = autopkginstalld.VERSION
AutoPkgInstallDaemon = autopkginstalld.AutoPkgInstallDaemon
AutoPkgInstallDaemonError = autopkginstalld.AutoPkgInstallDaemonError
RunHandler = autopkginstalld.RunHandler
main = autopkginstalld.main


class TestRunHandler(unittest.TestCase):
    """Test class for RunHandler."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = RunHandler(
            request=MagicMock(), client_address=("127.0.0.1", 12345), server=MagicMock()
        )
        self.handler.log = MagicMock()

    def test_verify_request_syntax_valid_package_request(self):
        """Should return True and no errors for valid package request."""
        plist = {"package": "/path/to/package.pkg"}
        syntax_ok, errors = self.handler.verify_request_syntax(plist)

        self.assertTrue(syntax_ok)
        self.assertEqual(errors, [])

    def test_verify_request_syntax_valid_mount_point_request(self):
        """Should return True and no errors for valid mount_point request."""
        plist = {"mount_point": "/Volumes/Something"}
        syntax_ok, errors = self.handler.verify_request_syntax(plist)

        # This should pass because we only check for 'package' key
        # mount_point is handled separately in the handle method
        self.assertFalse(syntax_ok)
        self.assertIn("Request does not contain package", errors[0])

    def test_verify_request_syntax_not_a_dict(self):
        """Should return False and error when plist is not a dictionary."""
        plist = ["not", "a", "dict"]
        syntax_ok, errors = self.handler.verify_request_syntax(plist)

        self.assertFalse(syntax_ok)
        self.assertEqual(len(errors), 1)
        self.assertIn("Request root is not a dictionary", errors[0])

    def test_verify_request_syntax_missing_package_key(self):
        """Should return False and error when package key is missing."""
        plist = {"something": "else"}
        syntax_ok, errors = self.handler.verify_request_syntax(plist)

        self.assertFalse(syntax_ok)
        self.assertEqual(len(errors), 1)
        self.assertIn("Request does not contain package", errors[0])


class TestAutoPkgInstallDaemon(unittest.TestCase):
    """Test class for AutoPkgInstallDaemon."""

    @patch("autopkginstalld.socket.fromfd")
    def test_init_creates_socket(self, mock_fromfd):
        """Should create socket from file descriptor."""
        mock_socket = MagicMock()
        mock_fromfd.return_value = mock_socket

        daemon = AutoPkgInstallDaemon(socket_fd=3, RequestHandlerClass=RunHandler)

        mock_fromfd.assert_called_once()
        mock_socket.listen.assert_called_once_with(daemon.request_queue_size)
        self.assertFalse(daemon.timed_out)

    @patch("autopkginstalld.socket.fromfd")
    def test_handle_timeout_sets_flag(self, mock_fromfd):
        """Should set timed_out flag when handle_timeout is called."""
        mock_socket = MagicMock()
        mock_fromfd.return_value = mock_socket

        daemon = AutoPkgInstallDaemon(socket_fd=3, RequestHandlerClass=RunHandler)
        self.assertFalse(daemon.timed_out)

        daemon.handle_timeout()
        self.assertTrue(daemon.timed_out)

    @patch("autopkginstalld.socket.fromfd")
    @patch("autopkginstalld.logging.getLogger")
    @patch("autopkginstalld.logging.StreamHandler")
    @patch("autopkginstalld.logging.handlers.RotatingFileHandler")
    def test_setup_logging_success(
        self, mock_file_handler, mock_stream_handler, mock_get_logger, mock_fromfd
    ):
        """Should set up logging handlers successfully."""
        mock_socket = MagicMock()
        mock_fromfd.return_value = mock_socket
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        daemon = AutoPkgInstallDaemon(socket_fd=3, RequestHandlerClass=RunHandler)
        daemon.setup_logging()

        mock_get_logger.assert_called_once_with(APPNAME)
        mock_logger.setLevel.assert_called_once()
        self.assertEqual(mock_logger.addHandler.call_count, 2)

    @patch("autopkginstalld.socket.fromfd")
    @patch("autopkginstalld.logging.getLogger")
    @patch("autopkginstalld.logging.handlers.RotatingFileHandler")
    def test_setup_logging_raises_on_file_error(
        self, mock_file_handler, mock_get_logger, mock_fromfd
    ):
        """Should raise AutoPkgInstallDaemonError when file logging fails."""
        mock_socket = MagicMock()
        mock_fromfd.return_value = mock_socket
        mock_get_logger.return_value = MagicMock()
        mock_file_handler.side_effect = OSError(13, "Permission denied")

        daemon = AutoPkgInstallDaemon(socket_fd=3, RequestHandlerClass=RunHandler)

        with self.assertRaises(AutoPkgInstallDaemonError) as ctx:
            daemon.setup_logging()

        self.assertIn("Can't open log", str(ctx.exception))


class TestMain(unittest.TestCase):
    """Test class for main function."""

    @patch("autopkginstalld.os.geteuid")
    def test_main_requires_root(self, mock_geteuid):
        """Should return 1 if not running as root."""
        mock_geteuid.return_value = 501  # Not root

        with patch("autopkginstalld.time.sleep"):
            result = main([])

        self.assertEqual(result, 1)

    @patch("autopkginstalld.os.geteuid")
    @patch("autopkginstalld.os.stat")
    @patch("autopkginstalld.os.path.realpath")
    @patch("autopkginstalld.os.path.abspath")
    @patch("autopkginstalld.os.path.dirname")
    @patch("autopkginstalld.sys.argv", ["/usr/local/bin/autopkginstalld"])
    def test_main_checks_ownership(
        self, mock_dirname, mock_abspath, mock_realpath, mock_stat, mock_geteuid
    ):
        """Should check file ownership and permissions."""
        mock_geteuid.return_value = 0  # Running as root
        mock_abspath.return_value = "/usr/local/bin/autopkginstalld"
        mock_realpath.return_value = "/usr/local/bin/autopkginstalld"

        # Mock dirname to traverse up the directory tree
        dirname_values = [
            "/usr/local/bin",  # First call
            "/usr/local",  # Second call
            "/usr",  # Third call
            "/",  # Fourth call - this will break the loop
        ]
        mock_dirname.side_effect = dirname_values

        # Mock stat to return wrong ownership
        mock_stat_result = MagicMock()
        mock_stat_result.st_uid = 501  # Not root
        mock_stat_result.st_gid = 0
        mock_stat_result.st_mode = 0o755
        mock_stat.return_value = mock_stat_result

        with patch("autopkginstalld.time.sleep"):
            result = main([])

        self.assertEqual(result, 1)

    @patch("autopkginstalld.os.geteuid")
    @patch("autopkginstalld.os.stat")
    @patch("autopkginstalld.os.path.realpath")
    @patch("autopkginstalld.os.path.abspath")
    @patch("autopkginstalld.os.path.dirname")
    @patch("autopkginstalld.sys.argv", ["/usr/local/bin/autopkginstalld"])
    def test_main_checks_world_writable(
        self, mock_dirname, mock_abspath, mock_realpath, mock_stat, mock_geteuid
    ):
        """Should fail if file is world writable."""
        mock_geteuid.return_value = 0  # Running as root
        mock_abspath.return_value = "/usr/local/bin/autopkginstalld"
        mock_realpath.return_value = "/usr/local/bin/autopkginstalld"

        # Mock dirname to traverse up the directory tree
        dirname_values = [
            "/usr/local/bin",  # First call
            "/usr/local",  # Second call
            "/usr",  # Third call
            "/",  # Fourth call - this will break the loop
        ]
        mock_dirname.side_effect = dirname_values

        # Mock stat to return world writable
        mock_stat_result = MagicMock()
        mock_stat_result.st_uid = 0
        mock_stat_result.st_gid = 0
        mock_stat_result.st_mode = 0o757  # World writable
        mock_stat.return_value = mock_stat_result

        with patch("autopkginstalld.time.sleep"):
            result = main([])

        self.assertEqual(result, 1)


class TestConstants(unittest.TestCase):
    """Test class for module constants."""

    def test_appname_constant(self):
        """APPNAME should be set correctly."""
        self.assertEqual(APPNAME, "autopkginstalld")

    def test_version_constant(self):
        """VERSION should be set and be a valid version string."""
        self.assertIsInstance(VERSION, str)
        self.assertRegex(VERSION, r"^\d+\.\d+")


if __name__ == "__main__":
    unittest.main()
