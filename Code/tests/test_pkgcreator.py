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

import os.path
import socket
import unittest
from copy import deepcopy
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import MagicMock, patch

from autopkglib import ProcessorError
from autopkglib.PkgCreator import PkgCreator


class TestPkgCreator(unittest.TestCase):
    """Test class for PkgCreator Processor."""

    def setUp(self):
        self.maxDiff: int = 100000
        self.tmp_dir = TemporaryDirectory()
        self.good_env: dict[str, Any] = {
            "pkg_request": {
                "pkgroot": "/path/to/root",
                "pkgname": "TestPackage",
                "id": "com.example.testpackage",
                "version": "1.0.0",
                "pkgtype": "flat",
                "pkgdir": self.tmp_dir.name,
                "infofile": "",
                "scripts": "",
                "chown": [],
            },
            "RECIPE_CACHE_DIR": self.tmp_dir.name,
            "RECIPE_DIR": self.tmp_dir.name,
        }
        self.minimal_env: dict[str, Any] = {
            "pkg_request": {
                "pkgroot": "/path/to/root",
                "pkgname": "TestPackage",
                "id": "com.example.testpackage",
                "version": "1.0.0",
            },
            "RECIPE_CACHE_DIR": self.tmp_dir.name,
        }
        self.bad_env: dict[str, Any] = {}
        self.processor = PkgCreator(env=deepcopy(self.good_env))
        self.addCleanup(self.tmp_dir.cleanup)

    def tearDown(self):
        pass

    def _mkpath(self, *parts: str) -> str:
        """Returns a path into the per testcase temporary directory."""
        return os.path.join(self.tmp_dir.name, *parts)

    def test_missing_pkg_request_raises(self):
        """The processor should raise an exception if pkg_request is missing."""
        self.processor.env = self.bad_env
        with self.assertRaises(KeyError):
            self.processor.main()

    def test_missing_required_key_raises(self):
        """The processor should raise an exception if required keys are missing."""
        # Test missing pkgroot
        bad_request = {"pkgname": "test", "id": "com.test", "version": "1.0"}
        self.processor.env = {
            "pkg_request": bad_request,
            "RECIPE_CACHE_DIR": self.tmp_dir.name,
        }
        with self.assertRaisesRegex(ProcessorError, "Request key pkgroot missing"):
            self.processor.main()

    @patch("autopkglib.PkgCreator.disconnect")
    @patch("autopkglib.PkgCreator.send_request")
    @patch("autopkglib.PkgCreator.connect")
    @patch("autopkglib.PkgCreator.pkg_already_exists")
    def test_builds_package_successfully(
        self, mock_exists, mock_connect, mock_send, mock_disconnect
    ):
        """The processor should build a package successfully."""
        mock_exists.return_value = False
        expected_pkg_path = self._mkpath("TestPackage.pkg")
        mock_send.return_value = expected_pkg_path

        self.processor.main()

        self.assertEqual(self.processor.env["pkg_path"], expected_pkg_path)
        self.assertTrue(self.processor.env["new_package_request"])
        mock_connect.assert_called_once()
        mock_send.assert_called_once()
        mock_disconnect.assert_called_once()

    @patch("autopkglib.PkgCreator.pkg_already_exists")
    def test_skips_build_if_package_exists(self, mock_exists):
        """The processor should skip building if package already exists."""
        mock_exists.return_value = True
        expected_pkg_path = self._mkpath("TestPackage.pkg")

        self.processor.main()

        self.assertEqual(self.processor.env["pkg_path"], expected_pkg_path)
        self.assertFalse(self.processor.env["new_package_request"])

    def test_fills_in_default_values(self):
        """The processor should fill in default values for optional keys."""
        self.processor.env = deepcopy(self.minimal_env)

        with patch("autopkglib.PkgCreator.pkg_already_exists", return_value=True):
            self.processor.main()

        request = self.processor.env["pkg_request"]
        self.assertEqual(request["pkgtype"], "flat")
        self.assertEqual(request["infofile"], "")
        self.assertEqual(request["scripts"], "")
        self.assertEqual(request["chown"], [])

    def test_find_path_for_relpath_cache_dir(self):
        """Test finding relative paths in RECIPE_CACHE_DIR."""
        # Create a test file in cache dir
        test_file = self._mkpath("test_file.txt")
        with open(test_file, "w") as f:
            f.write("test")

        result = self.processor.find_path_for_relpath("test_file.txt")
        self.assertEqual(result, test_file)

    def test_find_path_for_relpath_recipe_dir(self):
        """Test finding relative paths in RECIPE_DIR."""
        recipe_dir = self._mkpath("recipe_dir")
        os.makedirs(recipe_dir, exist_ok=True)
        test_file = os.path.join(recipe_dir, "test_file.txt")
        with open(test_file, "w") as f:
            f.write("test")

        self.processor.env["RECIPE_DIR"] = recipe_dir
        self.processor.env["RECIPE_CACHE_DIR"] = self._mkpath("cache")
        os.makedirs(self.processor.env["RECIPE_CACHE_DIR"], exist_ok=True)

        result = self.processor.find_path_for_relpath("test_file.txt")
        self.assertEqual(result, test_file)

    def test_find_path_for_relpath_not_found_raises(self):
        """Test that missing relative paths raise an exception."""
        with self.assertRaisesRegex(ProcessorError, "Can't find nonexistent_file.txt"):
            self.processor.find_path_for_relpath("nonexistent_file.txt")

    @patch("subprocess.Popen")
    def test_xar_expand_success(self, mock_popen):
        """Test successful xar expansion."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        test_pkg = self._mkpath("test.pkg")
        self.processor.xar_expand(test_pkg)

        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        self.assertIn("/usr/bin/xar", args)
        self.assertIn(test_pkg, args)

    @patch("subprocess.Popen")
    def test_xar_expand_failure(self, mock_popen):
        """Test xar expansion failure."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "xar error")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        test_pkg = self._mkpath("test.pkg")
        with self.assertRaisesRegex(ProcessorError, "extraction.*failed"):
            self.processor.xar_expand(test_pkg)

    @patch("subprocess.Popen", side_effect=OSError(2, "No such file"))
    def test_xar_expand_oserror(self, mock_popen):
        """Test xar expansion OSError."""
        test_pkg = self._mkpath("test.pkg")
        with self.assertRaisesRegex(ProcessorError, "xar execution failed"):
            self.processor.xar_expand(test_pkg)

    @patch("autopkglib.PkgCreator.xar_expand")
    def test_pkg_already_exists_true(self, mock_xar):
        """Test pkg_already_exists returns True for matching package."""
        # Create test package file
        pkg_path = self._mkpath("test.pkg")
        with open(pkg_path, "w") as f:
            f.write("fake package")

        # Create PackageInfo file content that will be "extracted"
        packageinfo_content = '<?xml version="1.0" encoding="UTF-8"?><pkg-info identifier="com.test" version="1.0.0"/>'

        # Mock xar_expand to create the PackageInfo file
        def mock_xar_side_effect(path):
            packageinfo_file = self._mkpath("PackageInfo")
            with open(packageinfo_file, "w") as f:
                f.write(packageinfo_content)

        mock_xar.side_effect = mock_xar_side_effect

        result = self.processor.pkg_already_exists(pkg_path, "com.test", "1.0.0")
        self.assertTrue(result)

    @patch("autopkglib.PkgCreator.xar_expand")
    def test_pkg_already_exists_false_different_version(self, mock_xar):
        """Test pkg_already_exists returns False for different version."""
        # Create test package file
        pkg_path = self._mkpath("test.pkg")
        with open(pkg_path, "w") as f:
            f.write("fake package")

        # Create PackageInfo file content with different version
        packageinfo_content = '<?xml version="1.0" encoding="UTF-8"?><pkg-info identifier="com.test" version="2.0.0"/>'

        def mock_xar_side_effect(path):
            packageinfo_file = self._mkpath("PackageInfo")
            with open(packageinfo_file, "w") as f:
                f.write(packageinfo_content)

        mock_xar.side_effect = mock_xar_side_effect

        result = self.processor.pkg_already_exists(pkg_path, "com.test", "1.0.0")
        self.assertFalse(result)

    def test_pkg_already_exists_no_file(self):
        """Test pkg_already_exists returns False when package doesn't exist."""
        pkg_path = self._mkpath("nonexistent.pkg")
        result = self.processor.pkg_already_exists(pkg_path, "com.test", "1.0.0")
        self.assertFalse(result)

    @patch("autopkglib.PkgCreator.xar_expand", side_effect=ProcessorError("xar failed"))
    @patch("os.unlink")
    def test_pkg_already_exists_xar_failure_removes_pkg(self, mock_unlink, mock_xar):
        """Test that package is removed if xar expansion fails."""
        pkg_path = self._mkpath("test.pkg")
        with open(pkg_path, "w") as f:
            f.write("fake package")

        result = self.processor.pkg_already_exists(pkg_path, "com.test", "1.0.0")
        self.assertFalse(result)
        mock_unlink.assert_called_with(pkg_path)

    @patch("socket.socket")
    def test_connect_success(self, mock_socket):
        """Test successful connection to autopkgserver."""
        mock_sock = MagicMock()
        mock_socket.return_value = mock_sock

        self.processor.connect()

        mock_socket.assert_called_with(socket.AF_UNIX, socket.SOCK_STREAM)
        mock_sock.connect.assert_called_once()

    @patch("socket.socket")
    def test_connect_failure(self, mock_socket):
        """Test connection failure to autopkgserver."""
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = OSError("Connection failed")
        mock_socket.return_value = mock_sock

        with self.assertRaisesRegex(ProcessorError, "Unable to contact autopkgserver"):
            self.processor.connect()

    def test_send_request_success(self):
        """Test successful request sending."""
        mock_socket = MagicMock()
        mock_file = MagicMock()
        mock_file.read.return_value = "OK:/path/to/package.pkg"
        mock_socket.makefile.return_value.__enter__.return_value = mock_file
        self.processor.socket = mock_socket

        result = self.processor.send_request({"test": "request"})

        self.assertEqual(result, "/path/to/package.pkg")
        mock_socket.makefile.assert_called_once_with(mode="r")

    def test_send_request_error(self):
        """Test error response from send_request."""
        mock_socket = MagicMock()
        mock_file = MagicMock()
        mock_file.read.return_value = "ERROR:Package build failed"
        mock_socket.makefile.return_value.__enter__.return_value = mock_file
        self.processor.socket = mock_socket

        with self.assertRaisesRegex(ProcessorError, "Package build failed"):
            self.processor.send_request({"test": "request"})

    def test_disconnect(self):
        """Test disconnection from autopkgserver."""
        mock_socket = MagicMock()
        self.processor.socket = mock_socket

        self.processor.disconnect()

        mock_socket.close.assert_called_once()

    def test_disconnect_with_error(self):
        """Test disconnection with socket error."""
        mock_socket = MagicMock()
        mock_socket.close.side_effect = OSError("Close failed")
        self.processor.socket = mock_socket

        # Should not raise an exception, just log
        self.processor.disconnect()

    @patch("autopkglib.PkgCreator.disconnect")
    @patch("autopkglib.PkgCreator.send_request")
    @patch("autopkglib.PkgCreator.connect")
    @patch("autopkglib.PkgCreator.pkg_already_exists")
    def test_disconnect_called_on_exception(
        self, mock_exists, mock_connect, mock_send, mock_disconnect
    ):
        """Test that disconnect is called even if an exception occurs."""
        mock_exists.return_value = False
        mock_send.side_effect = ProcessorError("Build failed")

        with self.assertRaises(ProcessorError):
            self.processor.main()

        mock_disconnect.assert_called_once()

    def test_converts_relative_paths_to_absolute(self):
        """Test that relative paths are converted to absolute paths."""
        # Create test files
        test_root = self._mkpath("pkgroot")
        test_scripts = self._mkpath("scripts")
        os.makedirs(test_root, exist_ok=True)
        os.makedirs(test_scripts, exist_ok=True)

        # Set up environment with relative paths
        self.processor.env["pkg_request"] = {
            "pkgroot": "pkgroot",  # relative path
            "scripts": "scripts",  # relative path
            "pkgname": "TestPackage",
            "id": "com.test",
            "version": "1.0.0",
        }

        with patch("autopkglib.PkgCreator.pkg_already_exists", return_value=True):
            self.processor.main()

        request = self.processor.env["pkg_request"]
        self.assertTrue(request["pkgroot"].startswith("/"))
        self.assertTrue(request["scripts"].startswith("/"))

    @patch("autopkglib.PkgCreator.disconnect")
    @patch("autopkglib.PkgCreator.send_request")
    @patch("autopkglib.PkgCreator.connect")
    @patch("autopkglib.PkgCreator.pkg_already_exists")
    def test_sets_summary_result(
        self, mock_exists, mock_connect, mock_send, mock_disconnect
    ):
        """Test that summary result is set correctly."""
        mock_exists.return_value = False
        pkg_path = self._mkpath("TestPackage.pkg")
        mock_send.return_value = pkg_path

        self.processor.main()

        summary = self.processor.env["pkg_creator_summary_result"]
        self.assertIn("summary_text", summary)
        self.assertIn("data", summary)
        self.assertEqual(summary["data"]["pkg_path"], pkg_path)

    def test_force_pkg_build_overrides_existing(self):
        """Test that force_pkg_build overrides existing package check."""
        # Create test package file
        pkg_path = self._mkpath("TestPackage.pkg")
        with open(pkg_path, "w") as f:
            f.write("fake package")

        self.processor.env["force_pkg_build"] = True

        result = self.processor.pkg_already_exists(pkg_path, "com.test", "1.0.0")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
