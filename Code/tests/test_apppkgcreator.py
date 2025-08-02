#!/usr/local/autopkg/python

import os
import plistlib
import tempfile
import unittest
from copy import deepcopy
from unittest.mock import patch

from autopkglib import ProcessorError
from autopkglib.AppPkgCreator import AppPkgCreator


class TestAppPkgCreator(unittest.TestCase):
    """Test class for AppPkgCreator processor."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.app_path = os.path.join(self.tempdir.name, "TestApp.app")
        self.bundle_id = "com.example.testapp"
        self.version = "1.0.0"

        self.good_env = {
            "app_path": self.app_path,
            "RECIPE_CACHE_DIR": self.tempdir.name,
            "bundleid": self.bundle_id,
            "version": self.version,
        }

        self.processor = AppPkgCreator()
        self.processor.env = deepcopy(self.good_env)

    def tearDown(self):
        self.tempdir.cleanup()

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
        self.processor.env = {"RECIPE_CACHE_DIR": self.tempdir.name}

        with self.assertRaisesRegex(
            ProcessorError, "No app_path or pathname specified"
        ):
            self.processor.main()

    # Test package_app() version and bundle ID extraction logic
    @patch("autopkglib.AppPkgCreator.pkg_already_exists", return_value=True)
    def test_package_app_extracts_version_from_info_plist(self, mock_exists):
        """Test that package_app() extracts version from Info.plist when not provided."""
        app_path = self._create_test_app(self.app_path, version="2.1.0")

        # Remove version from environment
        del self.processor.env["version"]

        self.processor.package_app(app_path)

        self.assertEqual(self.processor.env["version"], "2.1.0")

    @patch("autopkglib.AppPkgCreator.pkg_already_exists", return_value=True)
    def test_package_app_extracts_bundleid_from_info_plist(self, mock_exists):
        """Test that package_app() extracts bundle ID from Info.plist when not provided."""
        custom_bundle_id = "com.custom.app"
        app_path = self._create_test_app(self.app_path, bundle_id=custom_bundle_id)

        # Remove bundleid from environment
        del self.processor.env["bundleid"]

        self.processor.package_app(app_path)

        self.assertEqual(self.processor.env["bundleid"], custom_bundle_id)

    @patch("autopkglib.AppPkgCreator.pkg_already_exists", return_value=True)
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
    @patch("autopkglib.AppPkgCreator.pkg_already_exists", return_value=True)
    def test_package_app_generates_default_pkg_path(self, mock_exists):
        """Test that package_app() generates correct default pkg path."""
        app_path = self._create_test_app(self.app_path)

        self.processor.package_app(app_path)

        expected_path = os.path.join(self.tempdir.name, "TestApp-1.0.0.pkg")
        self.assertEqual(self.processor.env["pkg_path"], expected_path)

    @patch("autopkglib.AppPkgCreator.pkg_already_exists", return_value=True)
    def test_package_app_uses_custom_pkg_path(self, mock_exists):
        """Test that package_app() uses provided pkg_path."""
        app_path = self._create_test_app(self.app_path)
        custom_pkg_path = os.path.join(self.tempdir.name, "custom", "MyApp.pkg")

        self.processor.env["pkg_path"] = custom_pkg_path

        self.processor.package_app(app_path)

        self.assertEqual(self.processor.env["pkg_path"], custom_pkg_path)

    # Test package existence check
    @patch("autopkglib.AppPkgCreator.pkg_already_exists", return_value=True)
    def test_package_app_skips_build_if_package_exists(self, mock_exists):
        """Test that package_app() skips build when package already exists."""
        app_path = self._create_test_app(self.app_path)

        self.processor.package_app(app_path)

        self.assertEqual(self.processor.env["new_package_request"], False)

    # Test summary result generation
    @patch("autopkglib.AppPkgCreator.pkg_already_exists", return_value=False)
    @patch("autopkglib.AppPkgCreator.connect")
    @patch("autopkglib.AppPkgCreator.disconnect")
    @patch("autopkglib.AppPkgCreator.send_request")
    def test_package_app_sets_summary_result(
        self, mock_send, mock_disconnect, mock_connect, mock_exists
    ):
        """Test that package_app() sets correct summary result."""
        app_path = self._create_test_app(self.app_path)
        expected_pkg_path = os.path.join(self.tempdir.name, "TestApp-1.0.0.pkg")
        mock_send.return_value = expected_pkg_path

        self.processor.package_app(app_path)

        summary = self.processor.env.get("app_pkg_creator_summary_result")
        self.assertIsNotNone(summary)
        self.assertEqual(summary["data"]["identifier"], self.bundle_id)
        self.assertEqual(summary["data"]["version"], self.version)
        self.assertEqual(summary["data"]["pkg_path"], expected_pkg_path)

    # Test error handling in pkgroot creation/cleanup
    @patch("autopkglib.AppPkgCreator.pkg_already_exists", return_value=False)
    def test_package_app_pkgroot_creation_error_raises(self, mock_exists):
        """Test that package_app() handles pkgroot creation errors."""
        app_path = self._create_test_app(self.app_path)

        with patch("os.makedirs", side_effect=OSError("Permission denied")):
            with self.assertRaisesRegex(ProcessorError, "Could not create pkgroot"):
                self.processor.package_app(app_path)

    # Test exception handling ensures cleanup
    @patch("autopkglib.AppPkgCreator.pkg_already_exists", return_value=False)
    @patch("autopkglib.AppPkgCreator.connect")
    @patch("autopkglib.AppPkgCreator.disconnect")
    @patch(
        "autopkglib.AppPkgCreator.send_request", side_effect=Exception("Network error")
    )
    def test_package_app_disconnect_called_on_exception(
        self, mock_send, mock_disconnect, mock_connect, mock_exists
    ):
        """Test that disconnect is called even when send_request fails."""
        app_path = self._create_test_app(self.app_path)

        with self.assertRaises(Exception):
            self.processor.package_app(app_path)

        mock_disconnect.assert_called_once()


if __name__ == "__main__":
    unittest.main()
