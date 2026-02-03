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
import plistlib
import unittest
from copy import deepcopy
from io import BytesIO
from tempfile import TemporaryDirectory
from typing import Any
from unittest import mock
from unittest.mock import patch

from autopkglib import ProcessorError
from autopkglib.AppDmgVersioner import AppDmgVersioner


def patch_open(data: bytes, **kwargs) -> mock._patch:
    def _new_mock():
        omock = mock.MagicMock(name="open", spec="open")
        omock.side_effect = lambda *args, **kwargs: BytesIO(data)
        return omock

    return patch("builtins.open", new_callable=_new_mock, **kwargs)


TEST_APP_NAME: str = "TestApp.app"
TEST_BUNDLE_ID: str = "com.example.testapp"
TEST_VERSION: str = "1.0.0"

TEST_INFO_PLIST: bytes = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key>
    <string>{TEST_BUNDLE_ID}</string>
    <key>CFBundleShortVersionString</key>
    <string>{TEST_VERSION}</string>
    <key>CFBundleName</key>
    <string>TestApp</string>
    <key>CFBundleExecutable</key>
    <string>TestApp</string>
</dict>
</plist>""".encode()

TEST_INCOMPLETE_INFO_PLIST: bytes = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>TestApp</string>
</dict>
</plist>"""


class TestAppDmgVersioner(unittest.TestCase):
    """Test class for AppDmgVersioner Processor."""

    def setUp(self):
        self.maxDiff: int = 100000
        self.tmp_dir = TemporaryDirectory()
        self.good_env: dict[str, Any] = {
            "dmg_path": "/path/to/test.dmg",
            "RECIPE_CACHE_DIR": self.tmp_dir.name,
        }
        self.bad_env: dict[str, Any] = {}
        self.processor = AppDmgVersioner(data=deepcopy(self.good_env))
        self.addCleanup(self.tmp_dir.cleanup)

    def tearDown(self):
        pass

    def _mkpath(self, *parts: str) -> str:
        """Returns a path into the per testcase temporary directory."""
        return os.path.join(self.tmp_dir.name, *parts)

    def test_missing_dmg_path_raises(self):
        """The processor should raise an exception if dmg_path is missing."""
        self.processor.env = self.bad_env
        with self.assertRaises(ProcessorError):
            self.processor.main()

    @patch("autopkglib.AppDmgVersioner.unmount")
    @patch("autopkglib.AppDmgVersioner.mount")
    @patch("glob.glob")
    @patch_open(TEST_INFO_PLIST)
    def test_no_fail_if_good_env(self, mock_plist, mock_glob, mock_mount, mock_unmount):
        """The processor should not raise any exceptions if run normally."""
        mount_point = self._mkpath("mount_point")
        app_path = os.path.join(mount_point, TEST_APP_NAME)

        mock_mount.return_value = mount_point
        mock_glob.return_value = [app_path]

        self.processor.main()

        mock_mount.assert_called_once_with(self.good_env["dmg_path"])
        mock_unmount.assert_called_once_with(self.good_env["dmg_path"])
        mock_glob.assert_called_once_with(os.path.join(mount_point, "*.app"))

    @patch("autopkglib.AppDmgVersioner.unmount")
    @patch("autopkglib.AppDmgVersioner.mount")
    @patch("glob.glob")
    @patch_open(TEST_INFO_PLIST)
    def test_extracts_bundle_info(
        self, mock_plist, mock_glob, mock_mount, mock_unmount
    ):
        """The processor should extract app name, bundle ID, and version."""
        mount_point = self._mkpath("mount_point")
        app_path = os.path.join(mount_point, TEST_APP_NAME)

        mock_mount.return_value = mount_point
        mock_glob.return_value = [app_path]

        self.processor.main()

        self.assertEqual(self.processor.env["app_name"], TEST_APP_NAME)
        self.assertEqual(self.processor.env["bundleid"], TEST_BUNDLE_ID)
        self.assertEqual(self.processor.env["version"], TEST_VERSION)

    @patch("autopkglib.AppDmgVersioner.unmount")
    @patch("autopkglib.AppDmgVersioner.mount")
    @patch("glob.glob")
    def test_no_app_found_raises(self, mock_glob, mock_mount, mock_unmount):
        """The processor should raise an exception if no app is found."""
        mount_point = self._mkpath("mount_point")

        mock_mount.return_value = mount_point
        mock_glob.return_value = []  # No apps found

        with self.assertRaisesRegex(ProcessorError, "No app found in dmg"):
            self.processor.main()

        mock_unmount.assert_called_once_with(self.good_env["dmg_path"])

    @patch("autopkglib.AppDmgVersioner.unmount")
    @patch("autopkglib.AppDmgVersioner.mount")
    @patch("glob.glob")
    def test_multiple_apps_uses_first(self, mock_glob, mock_mount, mock_unmount):
        """The processor should use the first app if multiple apps are found."""
        mount_point = self._mkpath("mount_point")
        app_path1 = os.path.join(mount_point, "FirstApp.app")
        app_path2 = os.path.join(mount_point, "SecondApp.app")

        mock_mount.return_value = mount_point
        mock_glob.return_value = [app_path1, app_path2]

        with patch_open(TEST_INFO_PLIST):
            self.processor.main()

        self.assertEqual(self.processor.env["app_name"], "FirstApp.app")

    @patch("autopkglib.AppDmgVersioner.unmount")
    @patch("autopkglib.AppDmgVersioner.mount")
    @patch("glob.glob")
    @patch("builtins.open", side_effect=FileNotFoundError("Info.plist not found"))
    def test_missing_info_plist_raises(
        self, mock_open, mock_glob, mock_mount, mock_unmount
    ):
        """The processor should raise an exception if Info.plist is missing."""
        mount_point = self._mkpath("mount_point")
        app_path = os.path.join(mount_point, TEST_APP_NAME)

        mock_mount.return_value = mount_point
        mock_glob.return_value = [app_path]

        with self.assertRaisesRegex(ProcessorError, "Can't read.*Info.plist"):
            self.processor.main()

        mock_unmount.assert_called_once_with(self.good_env["dmg_path"])

    @patch("autopkglib.AppDmgVersioner.unmount")
    @patch("autopkglib.AppDmgVersioner.mount")
    @patch("glob.glob")
    @patch_open(TEST_INCOMPLETE_INFO_PLIST)
    def test_missing_bundle_info_raises(
        self, mock_plist, mock_glob, mock_mount, mock_unmount
    ):
        """The processor should raise an exception if bundle info is incomplete."""
        mount_point = self._mkpath("mount_point")
        app_path = os.path.join(mount_point, TEST_APP_NAME)

        mock_mount.return_value = mount_point
        mock_glob.return_value = [app_path]

        with self.assertRaises(ProcessorError):
            self.processor.main()

        mock_unmount.assert_called_once_with(self.good_env["dmg_path"])

    @patch("autopkglib.AppDmgVersioner.unmount")
    @patch("autopkglib.AppDmgVersioner.mount")
    @patch("glob.glob")
    @patch_open(b"invalid plist data")
    def test_invalid_plist_raises(
        self, mock_plist, mock_glob, mock_mount, mock_unmount
    ):
        """The processor should raise an exception if Info.plist is invalid."""
        mount_point = self._mkpath("mount_point")
        app_path = os.path.join(mount_point, TEST_APP_NAME)

        mock_mount.return_value = mount_point
        mock_glob.return_value = [app_path]

        with self.assertRaisesRegex(ProcessorError, "Can't read.*Info.plist"):
            self.processor.main()

        mock_unmount.assert_called_once_with(self.good_env["dmg_path"])

    def test_find_app_method(self):
        """Test the find_app method directly."""
        # Create a temporary directory structure
        test_dir = self._mkpath("test_mount")
        os.makedirs(test_dir, exist_ok=True)

        # Test case: no apps
        with self.assertRaisesRegex(ProcessorError, "No app found in dmg"):
            self.processor.find_app(test_dir)

        # Test case: create a mock app directory
        app_dir = os.path.join(test_dir, "TestApp.app")
        os.makedirs(app_dir, exist_ok=True)

        result = self.processor.find_app(test_dir)
        self.assertEqual(result, app_dir)

    def test_read_bundle_info_method(self):
        """Test the read_bundle_info method directly."""
        # Create a temporary app bundle structure
        app_dir = self._mkpath("TestApp.app")
        contents_dir = os.path.join(app_dir, "Contents")
        os.makedirs(contents_dir, exist_ok=True)

        # Create Info.plist file
        info_plist_path = os.path.join(contents_dir, "Info.plist")
        test_info = plistlib.loads(TEST_INFO_PLIST)
        with open(info_plist_path, "wb") as f:
            plistlib.dump(test_info, f)

        result = self.processor.read_bundle_info(app_dir)
        self.assertEqual(result["CFBundleIdentifier"], TEST_BUNDLE_ID)
        self.assertEqual(result["CFBundleShortVersionString"], TEST_VERSION)

        # Test missing Info.plist
        os.remove(info_plist_path)
        with self.assertRaisesRegex(ProcessorError, "Can't read.*Info.plist"):
            self.processor.read_bundle_info(app_dir)

    @patch("autopkglib.AppDmgVersioner.mount", side_effect=Exception("Mount failed"))
    def test_mount_failure_raises(self, mock_mount):
        """The processor should raise an exception if mounting fails."""
        with self.assertRaisesRegex(Exception, "Mount failed"):
            self.processor.main()

    @patch("autopkglib.AppDmgVersioner.unmount")
    @patch("autopkglib.AppDmgVersioner.mount")
    @patch("glob.glob", side_effect=Exception("Glob failed"))
    def test_unmount_called_on_exception(self, mock_glob, mock_mount, mock_unmount):
        """The processor should always unmount even if an exception occurs."""
        mount_point = self._mkpath("mount_point")
        mock_mount.return_value = mount_point

        with self.assertRaisesRegex(Exception, "Glob failed"):
            self.processor.main()

        # Ensure unmount is called even when an exception occurs
        mock_unmount.assert_called_once_with(self.good_env["dmg_path"])


if __name__ == "__main__":
    unittest.main()
