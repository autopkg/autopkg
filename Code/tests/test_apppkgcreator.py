#!/usr/local/autopkg/python
#
# Copyright 2025 Elliot Jordan
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
import plistlib
import unittest
from copy import deepcopy
from tempfile import TemporaryDirectory
from unittest.mock import patch

from autopkglib import ProcessorError
from autopkglib.AppPkgCreator import AppPkgCreator


class TestAppPkgCreator(unittest.TestCase):
    """Test class for AppPkgCreator processor."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.app_path = os.path.join(self.tmp_dir.name, "TestApp.app")
        self.bundle_id = "com.example.testapp"
        self.version = "1.0.0"

        self.good_env = {
            "app_path": self.app_path,
            "RECIPE_CACHE_DIR": self.tmp_dir.name,
            "bundleid": self.bundle_id,
            "version": self.version,
        }

        self.processor = AppPkgCreator()
        self.processor.env = deepcopy(self.good_env)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _create_test_app(self, app_path, bundle_id=None, version=None):
        """Create a test app bundle with Info.plist."""
        if bundle_id is None:
            bundle_id = self.bundle_id
        if version is None:
            version = self.version

        contents_dir = os.path.join(app_path, "Contents")
        os.makedirs(contents_dir, exist_ok=True)

        info_plist = {
            "CFBundleIdentifier": bundle_id,
            "CFBundleShortVersionString": version,
            "CFBundleName": "TestApp",
            "CFBundleExecutable": "TestApp",
        }

        info_plist_path = os.path.join(contents_dir, "Info.plist")
        with open(info_plist_path, "wb") as f:
            plistlib.dump(info_plist, f)

        return app_path

    # Test read_info_plist() - unique to AppPkgCreator
    def test_read_info_plist_success(self):
        """Test successful reading of Info.plist."""
        app_path = self._create_test_app(self.app_path)

        result = self.processor.read_info_plist(app_path)

        self.assertEqual(result["CFBundleIdentifier"], self.bundle_id)
        self.assertEqual(result["CFBundleShortVersionString"], self.version)
        self.assertEqual(result["CFBundleName"], "TestApp")

    def test_read_info_plist_missing_file_raises(self):
        """Test that missing Info.plist raises an exception."""
        with self.assertRaisesRegex(ProcessorError, "Can't read.*Info.plist"):
            self.processor.read_info_plist(self.app_path)

    def test_read_info_plist_invalid_file_raises(self):
        """Test that invalid Info.plist raises an exception."""
        # Create app structure but with invalid plist
        contents_dir = os.path.join(self.app_path, "Contents")
        os.makedirs(contents_dir, exist_ok=True)
        info_plist_path = os.path.join(contents_dir, "Info.plist")

        with open(info_plist_path, "w") as f:
            f.write("invalid plist content")

        with self.assertRaisesRegex(ProcessorError, "Can't read.*Info.plist"):
            self.processor.read_info_plist(self.app_path)

    # Test main() logic - unique app path handling
    def test_main_missing_app_path_and_pathname_raises(self):
        """Test that main() raises exception when both app_path and pathname are missing."""
        self.processor.env = {"RECIPE_CACHE_DIR": self.tmp_dir.name}

        with self.assertRaisesRegex(
            ProcessorError, "No app_path or pathname specified"
        ):
            self.processor.main()

    # Test package_app() version and bundle ID extraction logic
    @patch.object(AppPkgCreator, "pkg_already_exists", return_value=True)
    def test_package_app_extracts_version_from_info_plist(self, mock_exists):
        """Test that package_app() extracts version from Info.plist when not provided."""
        app_path = self._create_test_app(self.app_path, version="2.1.0")

        # Remove version from environment
        del self.processor.env["version"]

        self.processor.package_app(app_path)

        self.assertEqual(self.processor.env["version"], "2.1.0")

    @patch.object(AppPkgCreator, "pkg_already_exists", return_value=True)
    def test_package_app_extracts_bundleid_from_info_plist(self, mock_exists):
        """Test that package_app() extracts bundle ID from Info.plist when not provided."""
        custom_bundle_id = "com.custom.app"
        app_path = self._create_test_app(self.app_path, bundle_id=custom_bundle_id)

        # Remove bundleid from environment
        del self.processor.env["bundleid"]

        self.processor.package_app(app_path)

        self.assertEqual(self.processor.env["bundleid"], custom_bundle_id)

    @patch.object(AppPkgCreator, "pkg_already_exists", return_value=True)
    def test_package_app_uses_custom_version_key(self, mock_exists):
        """Test that package_app() can use custom version key."""
        app_path = self._create_test_app(self.app_path)

        # Add custom version to Info.plist
        contents_dir = os.path.join(app_path, "Contents")
        info_plist_path = os.path.join(contents_dir, "Info.plist")

        with open(info_plist_path, "rb") as f:
            plist = plistlib.load(f)
        plist["CFBundleVersion"] = "3.0.0"
        with open(info_plist_path, "wb") as f:
            plistlib.dump(plist, f)

        # Configure to use custom version key
        del self.processor.env["version"]
        self.processor.env["version_key"] = "CFBundleVersion"

        self.processor.package_app(app_path)

        self.assertEqual(self.processor.env["version"], "3.0.0")

    def test_package_app_missing_version_key_raises(self):
        """Test that package_app() raises exception for missing version key."""
        app_path = self._create_test_app(self.app_path)

        del self.processor.env["version"]
        self.processor.env["version_key"] = "NonExistentKey"

        with self.assertRaisesRegex(
            ProcessorError, "The key 'NonExistentKey' does not exist"
        ):
            self.processor.package_app(app_path)

    def test_package_app_missing_bundle_id_in_plist_raises(self):
        """Test that package_app() raises exception when bundle ID missing from plist."""
        # Create app without bundle ID
        contents_dir = os.path.join(self.app_path, "Contents")
        os.makedirs(contents_dir, exist_ok=True)

        info_plist = {
            "CFBundleShortVersionString": self.version,
            "CFBundleName": "TestApp",
        }

        info_plist_path = os.path.join(contents_dir, "Info.plist")
        with open(info_plist_path, "wb") as f:
            plistlib.dump(info_plist, f)

        # Remove bundleid from environment
        del self.processor.env["bundleid"]

        with self.assertRaises(ProcessorError):
            self.processor.package_app(self.app_path)

    # Test pkg_path generation logic
    @patch.object(AppPkgCreator, "pkg_already_exists", return_value=True)
    def test_package_app_generates_default_pkg_path(self, mock_exists):
        """Test that package_app() generates correct default pkg path."""
        app_path = self._create_test_app(self.app_path)

        self.processor.package_app(app_path)

        expected_path = os.path.join(self.tmp_dir.name, "TestApp-1.0.0.pkg")
        self.assertEqual(self.processor.env["pkg_path"], expected_path)

    @patch.object(AppPkgCreator, "pkg_already_exists", return_value=True)
    def test_package_app_uses_custom_pkg_path(self, mock_exists):
        """Test that package_app() uses provided pkg_path."""
        app_path = self._create_test_app(self.app_path)
        custom_pkg_path = os.path.join(self.tmp_dir.name, "custom", "MyApp.pkg")

        self.processor.env["pkg_path"] = custom_pkg_path

        self.processor.package_app(app_path)

        self.assertEqual(self.processor.env["pkg_path"], custom_pkg_path)

    # Test package existence check
    @patch.object(AppPkgCreator, "pkg_already_exists", return_value=True)
    def test_package_app_skips_build_if_package_exists(self, mock_exists):
        """Test that package_app() skips build when package already exists."""
        app_path = self._create_test_app(self.app_path)

        self.processor.package_app(app_path)

        self.assertEqual(self.processor.env["new_package_request"], False)

    # Test summary result generation
    @patch.object(AppPkgCreator, "pkg_already_exists", return_value=False)
    @patch.object(AppPkgCreator, "connect")
    @patch.object(AppPkgCreator, "disconnect")
    @patch.object(AppPkgCreator, "send_request")
    def test_package_app_sets_summary_result(
        self, mock_send, mock_disconnect, mock_connect, mock_exists
    ):
        """Test that package_app() sets correct summary result."""
        app_path = self._create_test_app(self.app_path)
        expected_pkg_path = os.path.join(self.tmp_dir.name, "TestApp-1.0.0.pkg")
        mock_send.return_value = expected_pkg_path

        self.processor.package_app(app_path)

        summary = self.processor.env.get("app_pkg_creator_summary_result")
        self.assertIsNotNone(summary)
        self.assertEqual(summary["data"]["identifier"], self.bundle_id)
        self.assertEqual(summary["data"]["version"], self.version)
        self.assertEqual(summary["data"]["pkg_path"], expected_pkg_path)

    # Test error handling in pkgroot creation/cleanup
    @patch.object(AppPkgCreator, "pkg_already_exists", return_value=False)
    def test_package_app_pkgroot_creation_error_raises(self, mock_exists):
        """Test that package_app() handles pkgroot creation errors."""
        app_path = self._create_test_app(self.app_path)

        with patch("os.makedirs", side_effect=OSError("Permission denied")):
            with self.assertRaisesRegex(ProcessorError, "Could not create pkgroot"):
                self.processor.package_app(app_path)

    # Test exception handling ensures cleanup
    @patch.object(AppPkgCreator, "pkg_already_exists", return_value=False)
    @patch.object(AppPkgCreator, "connect")
    @patch.object(AppPkgCreator, "disconnect")
    @patch.object(AppPkgCreator, "send_request", side_effect=Exception("Network error"))
    def test_package_app_disconnect_called_on_exception(
        self, mock_send, mock_disconnect, mock_connect, mock_exists
    ):
        """Test that disconnect is called even when send_request fails."""
        app_path = self._create_test_app(self.app_path)

        with self.assertRaises(Exception):
            self.processor.package_app(app_path)

        mock_disconnect.assert_called_once()

    @patch.object(AppPkgCreator, "pkg_already_exists", return_value=True)
    def test_package_app_clears_existing_summary_result(self, mock_exists):
        """Test that package_app() clears pre-existing summary result before processing."""
        app_path = self._create_test_app(self.app_path)
        self.processor.env["app_pkg_creator_summary_result"] = {"dummy": "value"}

        self.processor.package_app(app_path)

        self.assertNotIn("app_pkg_creator_summary_result", self.processor.env)

    def test_package_app_nonkeyerror_exception_in_version_extraction(self):
        """Test that non-KeyError exceptions in version extraction become ProcessorError."""
        app_path = self._create_test_app(self.app_path)
        del self.processor.env["version"]

        # Return a dict-like object that raises ValueError (not KeyError) on access.
        class BadVersionMapping:
            def __getitem__(self, key):
                raise ValueError("plist corrupted")

            def get(self, key, default=None):
                return None

        with patch.object(
            AppPkgCreator, "read_info_plist", return_value=BadVersionMapping()
        ):
            with self.assertRaises(ProcessorError):
                self.processor.package_app(app_path)

    def test_package_app_nonkeyerror_exception_in_bundleid_extraction(self):
        """Test that non-KeyError exceptions in bundle ID extraction become ProcessorError."""
        app_path = self._create_test_app(self.app_path)
        # Remove bundleid so the processor tries to read it from the plist.
        del self.processor.env["bundleid"]

        # Return a plist-like object whose __getitem__ raises TypeError.
        class BadMapping:
            def __getitem__(self, key):
                raise TypeError("bad type")

            def get(self, key, default=None):
                return None

        with patch.object(AppPkgCreator, "read_info_plist", return_value=BadMapping()):
            with self.assertRaises(ProcessorError):
                self.processor.package_app(app_path)

    @patch("shutil.copytree")
    @patch.object(AppPkgCreator, "send_request")
    @patch.object(AppPkgCreator, "disconnect")
    @patch.object(AppPkgCreator, "connect")
    @patch.object(AppPkgCreator, "pkg_already_exists", return_value=False)
    def test_package_app_copy_directory_to_payload(
        self, mock_exists, mock_connect, mock_disconnect, mock_send, mock_copytree
    ):
        """Test that package_app() calls shutil.copytree for a directory source."""
        app_path = self._create_test_app(self.app_path)
        mock_send.return_value = os.path.join(self.tmp_dir.name, "TestApp-1.0.0.pkg")

        self.processor.package_app(app_path)

        mock_copytree.assert_called_once()
        _, kwargs = mock_copytree.call_args
        self.assertTrue(kwargs.get("symlinks", False))
        positional = mock_copytree.call_args[0]
        self.assertEqual(positional[0], app_path)

    @patch("shutil.copyfile")
    @patch.object(AppPkgCreator, "read_info_plist", return_value={})
    @patch.object(AppPkgCreator, "send_request")
    @patch.object(AppPkgCreator, "disconnect")
    @patch.object(AppPkgCreator, "connect")
    @patch.object(AppPkgCreator, "pkg_already_exists", return_value=False)
    def test_package_app_copy_file_when_dest_not_exists(
        self,
        mock_exists,
        mock_connect,
        mock_disconnect,
        mock_send,
        mock_read_plist,
        mock_copyfile,
    ):
        """package_app() calls shutil.copyfile when source is a regular file and dest absent."""
        open(self.app_path, "wb").close()
        mock_send.return_value = os.path.join(self.tmp_dir.name, "TestApp-1.0.0.pkg")

        self.processor.package_app(self.app_path)

        mock_copyfile.assert_called_once()

    @patch("shutil.copy")
    @patch("os.path.isdir")
    @patch.object(AppPkgCreator, "read_info_plist", return_value={})
    @patch.object(AppPkgCreator, "send_request")
    @patch.object(AppPkgCreator, "disconnect")
    @patch.object(AppPkgCreator, "connect")
    @patch.object(AppPkgCreator, "pkg_already_exists", return_value=False)
    def test_package_app_copy_fallback_when_dest_exists(
        self,
        mock_exists,
        mock_connect,
        mock_disconnect,
        mock_send,
        mock_read_plist,
        mock_isdir,
        mock_copy,
    ):
        """package_app() calls shutil.copy when source is a file and dest already exists as a dir."""
        open(self.app_path, "wb").close()
        mock_send.return_value = os.path.join(self.tmp_dir.name, "TestApp-1.0.0.pkg")
        # Return True only for dest_item (simulates an existing dir); False everywhere else.
        dest_item = os.path.join(
            self.tmp_dir.name,
            "payload",
            "Applications",
            os.path.basename(self.app_path),
        )
        mock_isdir.side_effect = lambda path: path == dest_item

        self.processor.package_app(self.app_path)

        mock_copy.assert_called_once()

    @patch("shutil.copytree", side_effect=OSError("Permission denied"))
    @patch.object(AppPkgCreator, "pkg_already_exists", return_value=False)
    def test_package_app_copy_oserror_raises(self, mock_exists, mock_copytree):
        """Test that OSError during copy raises ProcessorError with 'Can't copy'."""
        app_path = self._create_test_app(self.app_path)

        with self.assertRaisesRegex(ProcessorError, "Can't copy"):
            self.processor.package_app(app_path)

    @patch.object(AppPkgCreator, "package_app")
    @patch("autopkglib.AppPkgCreator.glob", return_value=["/some/dir/TestApp.app"])
    @patch.object(AppPkgCreator, "unmount_if_mounted")
    @patch.object(AppPkgCreator, "parsePathForDMG", return_value=(None, False, ""))
    def test_main_uses_app_path_from_env(
        self, mock_parse, mock_unmount, mock_glob, mock_pkg
    ):
        """Test that main() uses env['app_path'] directly when set."""
        self.processor.env["app_path"] = "/some/dir/TestApp.app"

        self.processor.main()

        mock_pkg.assert_called_once_with("/some/dir/TestApp.app")

    @patch.object(AppPkgCreator, "package_app")
    @patch("autopkglib.AppPkgCreator.glob", return_value=["/some/dir/MyApp.app"])
    @patch.object(AppPkgCreator, "unmount_if_mounted")
    @patch.object(AppPkgCreator, "parsePathForDMG", return_value=(None, False, ""))
    def test_main_constructs_glob_pattern_from_pathname(
        self, mock_parse, mock_unmount, mock_glob, mock_pkg
    ):
        """Test that main() builds a '*.app' glob from pathname when app_path absent."""
        self.processor.env = {
            "RECIPE_CACHE_DIR": self.tmp_dir.name,
            "pathname": "/some/dir",
        }

        self.processor.main()

        mock_glob.assert_called_once_with("/some/dir/*.app")
        mock_pkg.assert_called_once_with("/some/dir/MyApp.app")

    @patch("autopkglib.AppPkgCreator.glob", return_value=[])
    @patch.object(AppPkgCreator, "unmount_if_mounted")
    @patch.object(AppPkgCreator, "parsePathForDMG", return_value=(None, False, ""))
    def test_main_no_glob_matches_raises(self, mock_parse, mock_unmount, mock_glob):
        """Test that main() raises ProcessorError when glob returns no matches."""
        self.processor.env["app_path"] = "/some/dir/TestApp.app"

        with self.assertRaisesRegex(ProcessorError, "Error processing path"):
            self.processor.main()

    @patch.object(AppPkgCreator, "package_app")
    @patch.object(AppPkgCreator, "output")
    @patch(
        "autopkglib.AppPkgCreator.glob",
        return_value=["/path/App1.app", "/path/App2.app"],
    )
    @patch.object(AppPkgCreator, "unmount_if_mounted")
    @patch.object(AppPkgCreator, "parsePathForDMG", return_value=(None, False, ""))
    def test_main_warns_on_multiple_matches(
        self, mock_parse, mock_unmount, mock_glob, mock_output, mock_pkg
    ):
        """Test that main() outputs a warning when multiple paths match the glob."""
        self.processor.env["app_path"] = "/path/*.app"

        self.processor.main()

        mock_output.assert_any_call(
            "WARNING: Multiple paths match 'app_path' glob '/path/*.app':"
        )

    @patch.object(AppPkgCreator, "package_app")
    @patch.object(AppPkgCreator, "output")
    @patch("autopkglib.AppPkgCreator.glob", return_value=["/dir/MyApp.app"])
    @patch.object(AppPkgCreator, "unmount_if_mounted")
    @patch.object(AppPkgCreator, "parsePathForDMG", return_value=(None, False, ""))
    def test_main_outputs_glob_warning_when_pattern_contains_special_chars(
        self, mock_parse, mock_unmount, mock_glob, mock_output, mock_pkg
    ):
        """Test that main() outputs a 'Using path matched from globbed' message."""
        self.processor.env["app_path"] = "**/MyApp.app"

        self.processor.main()

        mock_output.assert_any_call(
            "Using path '/dir/MyApp.app' matched from globbed '**/MyApp.app'."
        )


if __name__ == "__main__":
    unittest.main()
