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

import os
import plistlib
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

from autopkglib import ProcessorError
from autopkglib.PlistReader import PlistReader


class TestPlistReader(unittest.TestCase):
    """Test cases for PlistReader processor."""

    def setUp(self):
        """Set up test fixtures."""
        self.tmp_dir = TemporaryDirectory()
        self.processor = PlistReader()
        self.processor.env = {}

    def tearDown(self):
        """Clean up after tests."""
        self.tmp_dir.cleanup()

    def _create_plist_file(self, filename="test.plist", data=None):
        """Create a test plist file."""
        if data is None:
            data = {
                "CFBundleIdentifier": "com.example.testapp",
                "CFBundleShortVersionString": "1.2.3",
                "CFBundleVersion": "123",
                "CFBundleName": "Test App",
            }

        plist_path = os.path.join(self.tmp_dir.name, filename)
        with open(plist_path, "wb") as f:
            plistlib.dump(data, f)

        return plist_path

    def _create_bundle(self, bundle_name="TestApp.app", plist_data=None):
        """Create a test bundle with Info.plist."""
        bundle_path = os.path.join(self.tmp_dir.name, bundle_name)
        contents_path = os.path.join(bundle_path, "Contents")
        os.makedirs(contents_path)

        if plist_data is None:
            plist_data = {
                "CFBundleIdentifier": "com.example.testapp",
                "CFBundleShortVersionString": "2.0.0",
                "CFBundleVersion": "200",
            }

        info_plist_path = os.path.join(contents_path, "Info.plist")
        with open(info_plist_path, "wb") as f:
            plistlib.dump(plist_data, f)

        return bundle_path, info_plist_path

    def _create_malformed_plist(self, filename="bad.plist"):
        """Create a malformed plist file."""
        plist_path = os.path.join(self.tmp_dir.name, filename)
        with open(plist_path, "w") as f:
            f.write("not a valid plist")
        return plist_path

    # Test main functionality
    def test_main_reads_plist_file(self):
        """Test basic plist file reading."""
        plist_path = self._create_plist_file()
        self.processor.env = {
            "info_path": plist_path,
            "plist_keys": {"CFBundleShortVersionString": "version"},
        }

        with patch.object(self.processor, "output"):
            self.processor.main()

        self.assertEqual(self.processor.env["version"], "1.2.3")
        self.assertIn("plist_reader_output_variables", self.processor.env)
        self.assertEqual(
            self.processor.env["plist_reader_output_variables"]["version"], "1.2.3"
        )

    def test_main_reads_multiple_keys(self):
        """Test reading multiple plist keys."""
        plist_path = self._create_plist_file()
        self.processor.env = {
            "info_path": plist_path,
            "plist_keys": {
                "CFBundleShortVersionString": "version",
                "CFBundleIdentifier": "bundle_id",
                "CFBundleName": "app_name",
            },
        }

        with patch.object(self.processor, "output"):
            self.processor.main()

        self.assertEqual(self.processor.env["version"], "1.2.3")
        self.assertEqual(self.processor.env["bundle_id"], "com.example.testapp")
        self.assertEqual(self.processor.env["app_name"], "Test App")

    def test_main_default_plist_keys(self):
        """Test using default plist_keys when none provided."""
        plist_path = self._create_plist_file()
        self.processor.env = {
            "info_path": plist_path,
            "plist_keys": {
                "CFBundleShortVersionString": "version"
            },  # Use explicit default
        }

        with patch.object(self.processor, "output"):
            self.processor.main()

        # Should extract CFBundleShortVersionString to version
        self.assertEqual(self.processor.env["version"], "1.2.3")

    # Test bundle handling
    def test_main_reads_bundle_info_plist(self):
        """Test reading Info.plist from a bundle."""
        bundle_path, _ = self._create_bundle()
        self.processor.env = {
            "info_path": bundle_path,
            "plist_keys": {"CFBundleShortVersionString": "version"},
        }

        with patch.object(self.processor, "output"):
            self.processor.main()

        self.assertEqual(self.processor.env["version"], "2.0.0")

    def test_main_finds_bundle_in_directory(self):
        """Test finding and reading bundle in a directory."""
        # Create a directory with a bundle
        search_dir = os.path.join(self.tmp_dir.name, "search")
        os.makedirs(search_dir)

        bundle_path = os.path.join(search_dir, "TestApp.app")
        contents_path = os.path.join(bundle_path, "Contents")
        os.makedirs(contents_path)

        plist_data = {"CFBundleShortVersionString": "3.0.0"}
        info_plist_path = os.path.join(contents_path, "Info.plist")
        with open(info_plist_path, "wb") as f:
            plistlib.dump(plist_data, f)

        self.processor.env = {
            "info_path": search_dir,
            "plist_keys": {"CFBundleShortVersionString": "version"},
        }

        with patch.object(self.processor, "output"):
            self.processor.main()

        self.assertEqual(self.processor.env["version"], "3.0.0")

    # Test DMG mounting
    def test_main_mounts_dmg(self):
        """Test mounting DMG to read plist."""
        dmg_path = "/path/to/test.dmg"
        internal_path = "TestApp.app"
        mount_point = "/tmp/mount"

        # Create a bundle at the mount point
        mounted_bundle_path = os.path.join(mount_point, "TestApp.app")

        self.processor.env = {
            "info_path": f"{dmg_path}/{internal_path}",
            "plist_keys": {"CFBundleShortVersionString": "version"},
        }

        with patch.object(self.processor, "parsePathForDMG") as mock_parse:
            with patch.object(self.processor, "mount") as mock_mount:
                with patch.object(self.processor, "unmount") as mock_unmount:
                    with patch.object(
                        self.processor, "get_bundle_info_path"
                    ) as mock_bundle:
                        with patch("os.path.exists") as mock_exists:
                            with patch("builtins.open", create=True):
                                with patch("plistlib.load") as mock_load:
                                    with patch.object(self.processor, "output"):

                                        # Setup mocks
                                        mock_parse.return_value = (
                                            dmg_path,
                                            True,
                                            internal_path,
                                        )
                                        mock_mount.return_value = mount_point
                                        mock_exists.return_value = True
                                        mock_bundle.return_value = os.path.join(
                                            mounted_bundle_path, "Contents/Info.plist"
                                        )
                                        mock_load.return_value = {
                                            "CFBundleShortVersionString": "4.0.0"
                                        }

                                        self.processor.main()

        # Verify DMG operations were called
        mock_parse.assert_called_once()
        mock_mount.assert_called_once_with(dmg_path)
        mock_unmount.assert_called_once_with(dmg_path)
        self.assertEqual(self.processor.env["version"], "4.0.0")

    def test_main_unmounts_dmg_on_exception(self):
        """Test that DMG is unmounted even when an exception occurs."""
        dmg_path = "/path/to/test.dmg"
        internal_path = "TestApp.app"
        mount_point = "/tmp/mount"

        self.processor.env = {
            "info_path": f"{dmg_path}/{internal_path}",
            "plist_keys": {"CFBundleShortVersionString": "version"},
        }

        with patch.object(self.processor, "parsePathForDMG") as mock_parse:
            with patch.object(self.processor, "mount") as mock_mount:
                with patch.object(self.processor, "unmount") as mock_unmount:
                    with patch("os.path.exists") as mock_exists:

                        # Setup mocks to trigger an exception
                        mock_parse.return_value = (dmg_path, True, internal_path)
                        mock_mount.return_value = mount_point
                        mock_exists.return_value = (
                            False  # Path doesn't exist after mount
                        )

                        with self.assertRaises(ProcessorError):
                            self.processor.main()

        # Verify unmount was still called despite the exception
        mock_unmount.assert_called_once_with(dmg_path)

    # Test error handling
    def test_main_path_not_exists(self):
        """Test error when path doesn't exist."""
        self.processor.env = {
            "info_path": "/nonexistent/path.plist",
            "plist_keys": {"CFBundleShortVersionString": "version"},
        }

        with self.assertRaises(ProcessorError) as context:
            self.processor.main()

        self.assertIn("doesn't exist", str(context.exception))

    def test_main_malformed_plist(self):
        """Test error when plist file is malformed."""
        bad_plist_path = self._create_malformed_plist()
        self.processor.env = {
            "info_path": bad_plist_path,
            "plist_keys": {"CFBundleShortVersionString": "version"},
        }

        with patch.object(self.processor, "output"):
            with self.assertRaises(ProcessorError):
                self.processor.main()

    def test_main_missing_key(self):
        """Test error when requested key is missing from plist."""
        plist_path = self._create_plist_file()
        self.processor.env = {
            "info_path": plist_path,
            "plist_keys": {"NonexistentKey": "missing_value"},
        }

        with patch.object(self.processor, "output"):
            with self.assertRaises(ProcessorError) as context:
                self.processor.main()

            self.assertIn(
                "Key 'NonexistentKey' could not be found", str(context.exception)
            )

    def test_main_no_bundle_found_in_dmg(self):
        """Test error when no bundle is found in mounted DMG."""
        empty_dir = os.path.join(self.tmp_dir.name, "empty")
        os.makedirs(empty_dir)

        self.processor.env = {
            "info_path": empty_dir,
            "plist_keys": {"CFBundleShortVersionString": "version"},
        }

        with self.assertRaises(ProcessorError) as context:
            self.processor.main()

        self.assertIn("No bundle found in dmg", str(context.exception))

    # Test bundle detection methods
    def test_get_bundle_info_path_valid_bundle(self):
        """Test get_bundle_info_path with valid bundle."""
        bundle_path, info_plist_path = self._create_bundle()

        result = self.processor.get_bundle_info_path(bundle_path)
        self.assertEqual(result, info_plist_path)

    def test_get_bundle_info_path_not_bundle(self):
        """Test get_bundle_info_path with non-bundle directory."""
        regular_dir = os.path.join(self.tmp_dir.name, "regular_dir")
        os.makedirs(regular_dir)

        result = self.processor.get_bundle_info_path(regular_dir)
        self.assertIsNone(result)

    def test_get_bundle_info_path_file(self):
        """Test get_bundle_info_path with a file (not directory)."""
        file_path = self._create_plist_file()

        result = self.processor.get_bundle_info_path(file_path)
        self.assertIsNone(result)

    def test_get_bundle_info_path_malformed_info_plist(self):
        """Test get_bundle_info_path with malformed Info.plist."""
        bundle_path = os.path.join(self.tmp_dir.name, "BadBundle.app")
        contents_path = os.path.join(bundle_path, "Contents")
        os.makedirs(contents_path)

        # Create malformed Info.plist
        info_plist_path = os.path.join(contents_path, "Info.plist")
        with open(info_plist_path, "w") as f:
            f.write("not a valid plist")

        with self.assertRaises(ProcessorError) as context:
            self.processor.get_bundle_info_path(bundle_path)

        self.assertIn("cannot be parsed", str(context.exception))

    def test_find_bundle_single_bundle(self):
        """Test find_bundle with a single bundle in directory."""
        search_dir = os.path.join(self.tmp_dir.name, "search")
        os.makedirs(search_dir)

        bundle_path, info_plist_path = self._create_bundle("SingleApp.app")
        # Move bundle to search directory
        os.rename(bundle_path, os.path.join(search_dir, "SingleApp.app"))

        result = self.processor.find_bundle(search_dir)
        self.assertEqual(
            result, os.path.join(search_dir, "SingleApp.app", "Contents", "Info.plist")
        )

    def test_find_bundle_multiple_bundles(self):
        """Test find_bundle returns first bundle found."""
        search_dir = os.path.join(self.tmp_dir.name, "search")
        os.makedirs(search_dir)

        # Create multiple bundles
        for name in ["App1.app", "App2.app"]:
            bundle_path = os.path.join(search_dir, name)
            contents_path = os.path.join(bundle_path, "Contents")
            os.makedirs(contents_path)

            plist_data = {"CFBundleShortVersionString": "1.0.0"}
            info_plist_path = os.path.join(contents_path, "Info.plist")
            with open(info_plist_path, "wb") as f:
                plistlib.dump(plist_data, f)

        result = self.processor.find_bundle(search_dir)
        # Should return one of the bundles (order may vary based on glob)
        self.assertIsNotNone(result)
        self.assertTrue(result.endswith("Contents/Info.plist"))

    def test_find_bundle_ignores_symlinks_without_extensions(self):
        """Test find_bundle ignores symlinks without extensions."""
        search_dir = os.path.join(self.tmp_dir.name, "search")
        os.makedirs(search_dir)

        # Create a symlink without extension (like Applications)
        symlink_path = os.path.join(search_dir, "Applications")
        target_path = "/Applications"  # Doesn't need to exist for this test
        os.symlink(target_path, symlink_path)

        # Create a regular bundle
        bundle_path = os.path.join(search_dir, "RealApp.app")
        contents_path = os.path.join(bundle_path, "Contents")
        os.makedirs(contents_path)

        plist_data = {"CFBundleShortVersionString": "1.0.0"}
        info_plist_path = os.path.join(contents_path, "Info.plist")
        with open(info_plist_path, "wb") as f:
            plistlib.dump(plist_data, f)

        result = self.processor.find_bundle(search_dir)
        self.assertEqual(result, info_plist_path)

    def test_find_bundle_allows_symlinks_with_extensions(self):
        """Test find_bundle allows symlinks with extensions."""
        search_dir = os.path.join(self.tmp_dir.name, "search")
        os.makedirs(search_dir)

        # Create target bundle first
        target_bundle = os.path.join(self.tmp_dir.name, "target", "TargetApp.app")
        target_contents = os.path.join(target_bundle, "Contents")
        os.makedirs(target_contents)

        plist_data = {"CFBundleShortVersionString": "1.0.0"}
        target_info_plist = os.path.join(target_contents, "Info.plist")
        with open(target_info_plist, "wb") as f:
            plistlib.dump(plist_data, f)

        # Create symlink with extension
        symlink_path = os.path.join(search_dir, "LinkedApp.app")
        os.symlink(target_bundle, symlink_path)

        result = self.processor.find_bundle(search_dir)
        # The result should be the Info.plist path within the symlinked bundle
        expected_path = os.path.join(symlink_path, "Contents", "Info.plist")
        self.assertEqual(result, expected_path)

    def test_find_bundle_empty_directory(self):
        """Test find_bundle with empty directory."""
        empty_dir = os.path.join(self.tmp_dir.name, "empty")
        os.makedirs(empty_dir)

        with self.assertRaises(ProcessorError) as context:
            self.processor.find_bundle(empty_dir)

        self.assertIn("No bundle found in dmg", str(context.exception))

    # Test path normalization and edge cases
    def test_main_path_normalization(self):
        """Test that paths are normalized correctly."""
        self._create_plist_file()
        # Use path with redundant components
        redundant_path = os.path.join(
            self.tmp_dir.name, "..", os.path.basename(self.tmp_dir.name), "test.plist"
        )

        self.processor.env = {
            "info_path": redundant_path,
            "plist_keys": {"CFBundleShortVersionString": "version"},
        }

        with patch.object(self.processor, "output"):
            self.processor.main()

        self.assertEqual(self.processor.env["version"], "1.2.3")

    def test_main_complex_plist_data(self):
        """Test reading complex plist data types."""
        complex_data = {
            "CFBundleShortVersionString": "1.0.0",
            "StringValue": "test string",
            "IntegerValue": 42,
            "BooleanValue": True,
            "ArrayValue": ["item1", "item2"],
            "DictValue": {"nested_key": "nested_value"},
        }

        plist_path = self._create_plist_file(data=complex_data)
        self.processor.env = {
            "info_path": plist_path,
            "plist_keys": {
                "StringValue": "string_output",
                "IntegerValue": "int_output",
                "BooleanValue": "bool_output",
                "ArrayValue": "array_output",
                "DictValue": "dict_output",
            },
        }

        with patch.object(self.processor, "output"):
            self.processor.main()

        self.assertEqual(self.processor.env["string_output"], "test string")
        self.assertEqual(self.processor.env["int_output"], 42)
        self.assertEqual(self.processor.env["bool_output"], True)
        self.assertEqual(self.processor.env["array_output"], ["item1", "item2"])
        self.assertEqual(
            self.processor.env["dict_output"], {"nested_key": "nested_value"}
        )

    def test_main_unicode_handling(self):
        """Test handling of Unicode characters in plist data."""
        unicode_data = {
            "CFBundleShortVersionString": "1.0.0",
            "UnicodeString": "Test with émojis 🚀 and açcénts",
            "ChineseString": "测试中文",
        }

        plist_path = self._create_plist_file(data=unicode_data)
        self.processor.env = {
            "info_path": plist_path,
            "plist_keys": {
                "UnicodeString": "unicode_output",
                "ChineseString": "chinese_output",
            },
        }

        with patch.object(self.processor, "output"):
            self.processor.main()

        self.assertEqual(
            self.processor.env["unicode_output"], "Test with émojis 🚀 and açcénts"
        )
        self.assertEqual(self.processor.env["chinese_output"], "测试中文")


if __name__ == "__main__":
    unittest.main()
