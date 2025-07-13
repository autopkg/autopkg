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

import plistlib
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from autopkglib import ProcessorError
from autopkglib.MunkiInstallsItemsCreator import MunkiInstallsItemsCreator

try:
    HAS_FOUNDATION = True
except ImportError:
    HAS_FOUNDATION = False


class TestMunkiInstallsItemsCreator(unittest.TestCase):
    """Test cases for MunkiInstallsItemsCreator processor."""

    def setUp(self):
        """Set up test fixtures."""
        self.tmp_dir = TemporaryDirectory()
        self.processor = MunkiInstallsItemsCreator()
        self.processor.env = {
            "installs_item_paths": ["/Applications/TestApp.app"],
        }

    def tearDown(self):
        """Clean up after tests."""
        self.tmp_dir.cleanup()

    def _create_mock_process(self, returncode=0, stdout=b"", stderr=b""):
        """Create a mock subprocess.Popen for testing."""
        mock_proc = Mock()
        mock_proc.returncode = returncode
        mock_proc.communicate.return_value = (stdout, stderr)
        return mock_proc

    def _create_sample_makepkginfo_output(
        self, include_minosversion=False, minosversion="10.15"
    ):
        """Create sample makepkginfo output for testing."""
        installs_item = {
            "CFBundleIdentifier": "com.example.testapp",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "100",
            "path": "/Applications/TestApp.app",
            "type": "application",
        }

        if include_minosversion:
            installs_item["minosversion"] = minosversion

        pkginfo = {"installs": [installs_item]}

        return plistlib.dumps(pkginfo)

    # Test main functionality
    def test_main_calls_create_installs_items(self):
        """Test that main() calls create_installs_items."""
        with patch.object(self.processor, "create_installs_items") as mock_create:
            self.processor.main()

        mock_create.assert_called_once()

    # Test create_installs_items basic functionality
    def test_create_installs_items_basic(self):
        """Test basic create_installs_items functionality."""
        mock_output = self._create_sample_makepkginfo_output()
        mock_proc = self._create_mock_process(returncode=0, stdout=mock_output)

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(self.processor, "output"):
                self.processor.create_installs_items()

        # Should create additional_pkginfo with installs array
        self.assertIn("additional_pkginfo", self.processor.env)
        self.assertIn("installs", self.processor.env["additional_pkginfo"])
        installs = self.processor.env["additional_pkginfo"]["installs"]
        self.assertEqual(len(installs), 1)
        self.assertEqual(installs[0]["path"], "/Applications/TestApp.app")

    def test_create_installs_items_with_faux_root(self):
        """Test create_installs_items with faux_root."""
        self.processor.env["faux_root"] = "/tmp/expanded"
        self.processor.env["installs_item_paths"] = ["/Applications/TestApp.app"]

        # Mock makepkginfo output with faux_root path
        installs_item = {
            "CFBundleIdentifier": "com.example.testapp",
            "path": "/tmp/expanded/Applications/TestApp.app",
            "type": "application",
        }
        pkginfo = {"installs": [installs_item]}
        mock_output = plistlib.dumps(pkginfo)
        mock_proc = self._create_mock_process(returncode=0, stdout=mock_output)

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(self.processor, "output") as mock_log:
                self.processor.create_installs_items()

        # Path should be stripped of faux_root
        installs = self.processor.env["additional_pkginfo"]["installs"]
        self.assertEqual(installs[0]["path"], "/Applications/TestApp.app")
        mock_log.assert_any_call("Created installs item for /Applications/TestApp.app")

    def test_create_installs_items_faux_root_trailing_slash(self):
        """Test that faux_root trailing slash is handled correctly."""
        self.processor.env["faux_root"] = "/tmp/expanded/"

        mock_output = self._create_sample_makepkginfo_output()
        mock_proc = self._create_mock_process(returncode=0, stdout=mock_output)

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            with patch.object(self.processor, "output"):
                self.processor.create_installs_items()

        # Should call makepkginfo with faux_root without trailing slash
        call_args = mock_popen.call_args[0][0]
        self.assertIn("/tmp/expanded/Applications/TestApp.app", call_args)

    # Test makepkginfo command construction
    def test_create_installs_items_command_args(self):
        """Test that makepkginfo is called with correct arguments."""
        self.processor.env["installs_item_paths"] = [
            "/Applications/App1.app",
            "/Applications/App2.app",
        ]

        mock_output = self._create_sample_makepkginfo_output()
        mock_proc = self._create_mock_process(returncode=0, stdout=mock_output)

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            with patch.object(self.processor, "output"):
                self.processor.create_installs_items()

        # Verify makepkginfo was called with correct args
        call_args = mock_popen.call_args[0][0]
        expected_args = [
            "/usr/local/munki/makepkginfo",
            "-f",
            "/Applications/App1.app",
            "-f",
            "/Applications/App2.app",
        ]
        self.assertEqual(call_args, expected_args)

    # Test error handling
    def test_create_installs_items_makepkginfo_oserror(self):
        """Test handling of OSError from makepkginfo."""
        with patch(
            "subprocess.Popen", side_effect=OSError(2, "No such file or directory")
        ):
            with self.assertRaises(ProcessorError) as context:
                self.processor.create_installs_items()

            self.assertIn(
                "makepkginfo execution failed with error code 2", str(context.exception)
            )

    def test_create_installs_items_makepkginfo_failure(self):
        """Test handling of makepkginfo non-zero return code."""
        error_message = b"makepkginfo: error: invalid file"
        mock_proc = self._create_mock_process(returncode=1, stderr=error_message)

        with patch("subprocess.Popen", return_value=mock_proc):
            with self.assertRaises(ProcessorError) as context:
                self.processor.create_installs_items()

            self.assertIn("creating pkginfo failed", str(context.exception))

    # Test minimum OS version derivation
    def test_derive_minimum_os_version_basic(self):
        """Test basic minimum OS version derivation."""
        self.processor.env["derive_minimum_os_version"] = True
        self.processor.env["faux_root"] = "/tmp/root"

        # Create installs output with faux_root path
        installs_item = {
            "path": "/tmp/root/Applications/TestApp.app",
            "type": "application",
            "minosversion": "10.15",
        }
        pkginfo = {"installs": [installs_item]}
        mock_output = plistlib.dumps(pkginfo)
        mock_proc = self._create_mock_process(returncode=0, stdout=mock_output)

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(self.processor, "output") as mock_log:
                self.processor.create_installs_items()

        # Should set minimum_os_version
        self.assertEqual(self.processor.env["minimum_os_version"], "10.15")
        self.assertEqual(
            self.processor.env["additional_pkginfo"]["minimum_os_version"], "10.15"
        )
        mock_log.assert_any_call("Derived minimum os version as: 10.15")

    def test_derive_minimum_os_version_multiple_items_higher(self):
        """Test minimum OS version derivation with multiple items, higher version."""
        self.processor.env["derive_minimum_os_version"] = True
        self.processor.env["minimum_os_version"] = "10.13"
        self.processor.env["faux_root"] = "/tmp/root"

        # Create installs output with higher minosversion
        installs_item = {
            "path": "/tmp/root/Applications/TestApp.app",
            "type": "application",
            "minosversion": "10.15",
        }
        pkginfo = {"installs": [installs_item]}
        mock_output = plistlib.dumps(pkginfo)
        mock_proc = self._create_mock_process(returncode=0, stdout=mock_output)

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(self.processor, "output") as mock_log:
                self.processor.create_installs_items()

        # Should update to higher version
        self.assertEqual(self.processor.env["minimum_os_version"], "10.15")
        mock_log.assert_any_call(
            "Setting minimum os version to: 10.15, as greater than prior value of: 10.13"
        )

    def test_derive_minimum_os_version_multiple_items_lower(self):
        """Test minimum OS version derivation with multiple items, lower version."""
        self.processor.env["derive_minimum_os_version"] = True
        self.processor.env["minimum_os_version"] = "10.15"
        self.processor.env["faux_root"] = "/tmp/root"

        # Create installs output with lower minosversion
        installs_item = {
            "path": "/tmp/root/Applications/TestApp.app",
            "type": "application",
            "minosversion": "10.13",
        }
        pkginfo = {"installs": [installs_item]}
        mock_output = plistlib.dumps(pkginfo)
        mock_proc = self._create_mock_process(returncode=0, stdout=mock_output)

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(self.processor, "output") as mock_log:
                self.processor.create_installs_items()

        # Should keep existing higher version
        self.assertEqual(self.processor.env["minimum_os_version"], "10.15")
        mock_log.assert_any_call(
            "Minimum os version: 10.13, is lower than prior value of: 10.15... skipping..."
        )

    def test_derive_minimum_os_version_disabled(self):
        """Test that minimum OS version is not derived when disabled."""
        # Don't set derive_minimum_os_version
        self.processor.env["faux_root"] = "/tmp/root"

        # Create installs output with faux_root path and minosversion
        installs_item = {
            "path": "/tmp/root/Applications/TestApp.app",
            "type": "application",
            "minosversion": "10.15",
        }
        pkginfo = {"installs": [installs_item]}
        mock_output = plistlib.dumps(pkginfo)
        mock_proc = self._create_mock_process(returncode=0, stdout=mock_output)

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(self.processor, "output"):
                self.processor.create_installs_items()

        # Should not set minimum_os_version
        self.assertNotIn("minimum_os_version", self.processor.env)
        self.assertNotIn("minimum_os_version", self.processor.env["additional_pkginfo"])

    def test_derive_minimum_os_version_no_faux_root(self):
        """Test that minimum OS version is not derived without faux_root."""
        self.processor.env["derive_minimum_os_version"] = True
        # Don't set faux_root

        mock_output = self._create_sample_makepkginfo_output(include_minosversion=True)
        mock_proc = self._create_mock_process(returncode=0, stdout=mock_output)

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(self.processor, "output"):
                self.processor.create_installs_items()

        # Should not set minimum_os_version without faux_root
        self.assertNotIn("minimum_os_version", self.processor.env)
        self.assertNotIn("minimum_os_version", self.processor.env["additional_pkginfo"])

    # Test version comparison key
    def test_version_comparison_key_string(self):
        """Test setting version_comparison_key as string for all items."""
        self.processor.env["version_comparison_key"] = "CFBundleVersion"

        mock_output = self._create_sample_makepkginfo_output()
        mock_proc = self._create_mock_process(returncode=0, stdout=mock_output)

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(self.processor, "output"):
                self.processor.create_installs_items()

        # Should set version_comparison_key
        installs = self.processor.env["additional_pkginfo"]["installs"]
        self.assertEqual(installs[0]["version_comparison_key"], "CFBundleVersion")

    @unittest.skipUnless(HAS_FOUNDATION, "Foundation not available")
    def test_version_comparison_key_dict(self):
        """Test setting version_comparison_key as dictionary for specific paths."""
        from Foundation import NSDictionary

        version_keys = NSDictionary.dictionaryWithDictionary_(
            {"/Applications/TestApp.app": "CFBundleShortVersionString"}
        )
        self.processor.env["version_comparison_key"] = version_keys

        mock_output = self._create_sample_makepkginfo_output()
        mock_proc = self._create_mock_process(returncode=0, stdout=mock_output)

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(self.processor, "output"):
                self.processor.create_installs_items()

        # Should set version_comparison_key for matching path
        installs = self.processor.env["additional_pkginfo"]["installs"]
        self.assertEqual(
            installs[0]["version_comparison_key"], "CFBundleShortVersionString"
        )

    def test_version_comparison_key_missing_raises_error(self):
        """Test that missing version_comparison_key raises error."""
        self.processor.env["version_comparison_key"] = "NonexistentKey"

        mock_output = self._create_sample_makepkginfo_output()
        mock_proc = self._create_mock_process(returncode=0, stdout=mock_output)

        with patch("subprocess.Popen", return_value=mock_proc):
            with self.assertRaises(ProcessorError) as context:
                self.processor.create_installs_items()

            self.assertIn(
                "version_comparison_key 'NonexistentKey' could not be found",
                str(context.exception),
            )

    @unittest.skipUnless(HAS_FOUNDATION, "Foundation not available")
    def test_version_comparison_key_dict_no_match(self):
        """Test version_comparison_key dictionary with no matching path."""
        from Foundation import NSDictionary

        version_keys = NSDictionary.dictionaryWithDictionary_(
            {"/Applications/OtherApp.app": "CFBundleVersion"}
        )
        self.processor.env["version_comparison_key"] = version_keys

        mock_output = self._create_sample_makepkginfo_output()
        mock_proc = self._create_mock_process(returncode=0, stdout=mock_output)

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(self.processor, "output"):
                self.processor.create_installs_items()

        # Should not set version_comparison_key for non-matching path
        installs = self.processor.env["additional_pkginfo"]["installs"]
        self.assertNotIn("version_comparison_key", installs[0])

    # Test additional_pkginfo handling
    def test_existing_additional_pkginfo_preserved(self):
        """Test that existing additional_pkginfo is preserved."""
        self.processor.env["additional_pkginfo"] = {"existing_key": "existing_value"}

        mock_output = self._create_sample_makepkginfo_output()
        mock_proc = self._create_mock_process(returncode=0, stdout=mock_output)

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(self.processor, "output"):
                self.processor.create_installs_items()

        # Should preserve existing keys and add installs
        additional_pkginfo = self.processor.env["additional_pkginfo"]
        self.assertEqual(additional_pkginfo["existing_key"], "existing_value")
        self.assertIn("installs", additional_pkginfo)

    def test_empty_installs_array(self):
        """Test handling of empty installs array."""
        pkginfo = {"installs": []}
        mock_output = plistlib.dumps(pkginfo)
        mock_proc = self._create_mock_process(returncode=0, stdout=mock_output)

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(self.processor, "output"):
                self.processor.create_installs_items()

        # Should handle empty array gracefully
        installs = self.processor.env["additional_pkginfo"]["installs"]
        self.assertEqual(len(installs), 0)

    # Test complex scenarios
    def test_multiple_paths_with_complex_config(self):
        """Test multiple paths with complex configuration."""
        self.processor.env.update(
            {
                "installs_item_paths": [
                    "/Applications/App1.app",
                    "/Applications/App2.app",
                ],
                "faux_root": "/tmp/root",
                "derive_minimum_os_version": True,
                "version_comparison_key": "CFBundleVersion",
            }
        )

        # Create complex makepkginfo output
        installs_items = [
            {
                "CFBundleVersion": "100",
                "path": "/tmp/root/Applications/App1.app",
                "type": "application",
                "minosversion": "10.14",
            },
            {
                "CFBundleVersion": "200",
                "path": "/tmp/root/Applications/App2.app",
                "type": "application",
                "minosversion": "10.15",
            },
        ]
        pkginfo = {"installs": installs_items}
        mock_output = plistlib.dumps(pkginfo)
        mock_proc = self._create_mock_process(returncode=0, stdout=mock_output)

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(self.processor, "output"):
                self.processor.create_installs_items()

        # Verify all configurations are applied
        installs = self.processor.env["additional_pkginfo"]["installs"]
        self.assertEqual(len(installs), 2)

        # Check paths stripped of faux_root
        self.assertEqual(installs[0]["path"], "/Applications/App1.app")
        self.assertEqual(installs[1]["path"], "/Applications/App2.app")

        # Check version comparison keys set
        self.assertEqual(installs[0]["version_comparison_key"], "CFBundleVersion")
        self.assertEqual(installs[1]["version_comparison_key"], "CFBundleVersion")

        # Check minimum OS version derived (should be highest)
        self.assertEqual(self.processor.env["minimum_os_version"], "10.15")
        self.assertEqual(
            self.processor.env["additional_pkginfo"]["minimum_os_version"], "10.15"
        )

    def test_plist_parsing_error_handling(self):
        """Test handling of invalid plist output from makepkginfo."""
        invalid_plist = b"invalid plist data"
        mock_proc = self._create_mock_process(returncode=0, stdout=invalid_plist)

        with patch("subprocess.Popen", return_value=mock_proc):
            with self.assertRaises(Exception):  # plistlib will raise an exception
                self.processor.create_installs_items()

    # Test edge cases
    def test_faux_root_path_not_matching(self):
        """Test faux_root with paths that don't start with faux_root."""
        self.processor.env["faux_root"] = "/different/root"

        # Path doesn't start with faux_root
        installs_item = {"path": "/Applications/TestApp.app", "type": "application"}
        pkginfo = {"installs": [installs_item]}
        mock_output = plistlib.dumps(pkginfo)
        mock_proc = self._create_mock_process(returncode=0, stdout=mock_output)

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(self.processor, "output") as mock_log:
                self.processor.create_installs_items()

        # Path should remain unchanged
        installs = self.processor.env["additional_pkginfo"]["installs"]
        self.assertEqual(installs[0]["path"], "/Applications/TestApp.app")
        mock_log.assert_any_call("Created installs item for /Applications/TestApp.app")

    def test_no_minosversion_in_item(self):
        """Test derive_minimum_os_version with item that has no minosversion."""
        self.processor.env["derive_minimum_os_version"] = True
        self.processor.env["faux_root"] = "/tmp/root"

        # Create installs item without minosversion
        installs_item = {
            "path": "/tmp/root/Applications/TestApp.app",
            "type": "application",
            # No minosversion key
        }
        pkginfo = {"installs": [installs_item]}
        mock_output = plistlib.dumps(pkginfo)
        mock_proc = self._create_mock_process(returncode=0, stdout=mock_output)

        with patch("subprocess.Popen", return_value=mock_proc):
            with patch.object(self.processor, "output"):
                self.processor.create_installs_items()

        # Should not set minimum_os_version
        self.assertNotIn("minimum_os_version", self.processor.env)


if __name__ == "__main__":
    unittest.main()
