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
from xml.etree import ElementTree

from autopkglib import ProcessorError
from autopkglib.PkgInfoCreator import PkgInfoCreator


class TestPkgInfoCreator(unittest.TestCase):
    """Test cases for PkgInfoCreator processor."""

    def setUp(self):
        """Set up test fixtures."""
        self.tmp_dir = TemporaryDirectory()
        self.processor = PkgInfoCreator()
        self.processor.env = {
            "version": "1.0.0",
            "pkgtype": "flat",
            "RECIPE_DIR": self.tmp_dir.name,
        }

        # Create a minimal pkgroot structure
        self.pkgroot = os.path.join(self.tmp_dir.name, "pkgroot")
        os.makedirs(self.pkgroot)
        self.processor.env["pkgroot"] = self.pkgroot

        # Set up info file path
        self.infofile = os.path.join(self.tmp_dir.name, "PackageInfo")
        self.processor.env["infofile"] = self.infofile

    def tearDown(self):
        """Clean up after tests."""
        self.tmp_dir.cleanup()

    def _create_plist_template(self, filename="Info.plist", **kwargs):
        """Create a bundle-style Info.plist template."""
        template_data = {
            "CFBundleIdentifier": "com.example.testapp",
            "CFBundleShortVersionString": "1.0",
            "IFPkgFlagDefaultLocation": "/Applications",
            "IFPkgFlagAuthorizationAction": "RootAuthorization",
            "IFPkgFlagRestartAction": "None",
            "IFPkgFlagInstalledSize": 1024,
        }
        template_data.update(kwargs)

        template_path = os.path.join(self.tmp_dir.name, filename)
        with open(template_path, "wb") as f:
            plistlib.dump(template_data, f)

        self.processor.env["template_path"] = template_path
        return template_path

    def _create_xml_template(self, filename="PackageInfo"):
        """Create a flat-style PackageInfo template."""
        root = ElementTree.Element("pkg-info")
        root.set("format-version", "2")
        root.set("identifier", "com.example.testapp")
        root.set("version", "1.0")
        root.set("install-location", "/Applications")
        root.set("auth", "root")

        payload = ElementTree.SubElement(root, "payload")
        payload.set("installKBytes", "1024")
        payload.set("numberOfFiles", "10")

        template_path = os.path.join(self.tmp_dir.name, filename)
        tree = ElementTree.ElementTree(root)
        tree.write(template_path)

        self.processor.env["template_path"] = template_path
        return template_path

    def _create_test_files(self, num_files=3, file_size=4096):
        """Create test files in pkgroot."""
        for i in range(num_files):
            file_path = os.path.join(self.pkgroot, f"test_file_{i}.txt")
            with open(file_path, "w") as f:
                f.write("x" * file_size)

    # Test main functionality
    def test_main_calls_create_flat_info(self):
        """Test that main() calls create_flat_info for flat packages."""
        self._create_xml_template()

        with patch.object(self.processor, "create_flat_info") as mock_create:
            self.processor.main()

        mock_create.assert_called_once()

    def test_main_invalid_pkgtype(self):
        """Test that invalid pkgtype raises ProcessorError."""
        self.processor.env["pkgtype"] = "invalid"
        self._create_xml_template()

        with self.assertRaises(ProcessorError) as context:
            self.processor.main()

        self.assertIn("Unknown pkgtype invalid", str(context.exception))

    def test_main_bundle_pkgtype_raises_error(self):
        """Test that bundle pkgtype raises ProcessorError."""
        self.processor.env["pkgtype"] = "bundle"
        self._create_plist_template()

        with self.assertRaises(ProcessorError) as context:
            self.processor.main()

        self.assertIn(
            "Bundle package creation no longer supported", str(context.exception)
        )

    # Test template finding
    def test_find_template_absolute_path_exists(self):
        """Test finding template with absolute path that exists."""
        template_path = self._create_xml_template()

        found_path = self.processor.find_template()
        self.assertEqual(found_path, template_path)

    def test_find_template_absolute_path_not_exists(self):
        """Test finding template with absolute path that doesn't exist."""
        self.processor.env["template_path"] = "/nonexistent/path/PackageInfo"

        with self.assertRaises(ProcessorError) as context:
            self.processor.find_template()

        self.assertIn(
            "Can't find /nonexistent/path/PackageInfo", str(context.exception)
        )

    def test_find_template_relative_path_in_recipe_dir(self):
        """Test finding template with relative path in recipe directory."""
        template_path = self._create_xml_template("template.xml")
        self.processor.env["template_path"] = "template.xml"

        found_path = self.processor.find_template()
        self.assertEqual(found_path, template_path)

    def test_find_template_relative_path_in_parent_recipe_dir(self):
        """Test finding template in parent recipe directory."""
        parent_dir = os.path.join(self.tmp_dir.name, "parent")
        os.makedirs(parent_dir)

        template_path = os.path.join(parent_dir, "parent_template.xml")
        self._create_xml_template("parent_template.xml")
        # Move the template to parent directory
        os.rename(os.path.join(self.tmp_dir.name, "parent_template.xml"), template_path)

        self.processor.env["template_path"] = "parent_template.xml"
        self.processor.env["PARENT_RECIPES"] = [os.path.join(parent_dir, "recipe.py")]

        found_path = self.processor.find_template()
        self.assertEqual(found_path, template_path)

    def test_find_template_relative_path_not_found(self):
        """Test finding template with relative path that doesn't exist."""
        self.processor.env["template_path"] = "nonexistent_template.xml"

        with self.assertRaises(ProcessorError) as context:
            self.processor.find_template()

        self.assertIn("Can't find nonexistent_template.xml", str(context.exception))

    # Test template loading
    def test_load_template_plist_flat_conversion(self):
        """Test loading plist template for flat package."""
        self._create_plist_template()

        template = self.processor.load_template(
            self.processor.env["template_path"], "flat"
        )

        # Should return ElementTree for flat format
        self.assertIsInstance(template, ElementTree.ElementTree)
        root = template.getroot()
        self.assertEqual(root.tag, "pkg-info")
        self.assertEqual(root.get("identifier"), "com.example.testapp")

    def test_load_template_plist_bundle_unsupported(self):
        """Test loading plist template for bundle package returns info dict."""
        self._create_plist_template()

        # Bundle packages return the plist data, but conversion will fail later
        template = self.processor.load_template(
            self.processor.env["template_path"], "bundle"
        )

        # Should return a dictionary for bundle type
        self.assertIsInstance(template, dict)
        self.assertEqual(template["CFBundleIdentifier"], "com.example.testapp")

    def test_load_template_xml_flat(self):
        """Test loading XML template for flat package."""
        self._create_xml_template()

        template = self.processor.load_template(
            self.processor.env["template_path"], "flat"
        )

        self.assertIsInstance(template, ElementTree.ElementTree)
        root = template.getroot()
        self.assertEqual(root.tag, "pkg-info")

    def test_load_template_xml_bundle_unsupported(self):
        """Test loading XML template for bundle package raises error."""
        self._create_xml_template()

        # XML templates for bundle type should raise an error since we only support flat
        with self.assertRaises(ProcessorError):
            self.processor.load_template(self.processor.env["template_path"], "bundle")

    def test_load_template_malformed_plist(self):
        """Test loading malformed plist template raises error."""
        template_path = os.path.join(self.tmp_dir.name, "bad.plist")
        with open(template_path, "w") as f:
            f.write("not a valid plist")

        self.processor.env["template_path"] = template_path

        with self.assertRaises(ProcessorError) as context:
            self.processor.load_template(template_path, "flat")

        self.assertIn("Malformed Info.plist template", str(context.exception))

    def test_load_template_malformed_xml(self):
        """Test loading malformed XML template raises error."""
        template_path = os.path.join(self.tmp_dir.name, "bad.xml")
        with open(template_path, "w") as f:
            f.write("<invalid>xml")

        self.processor.env["template_path"] = template_path

        with self.assertRaises(ProcessorError) as context:
            self.processor.load_template(template_path, "flat")

        self.assertIn("Malformed PackageInfo template", str(context.exception))

    # Test bundle to flat conversion
    def test_convert_bundle_info_to_flat_basic(self):
        """Test basic bundle to flat conversion."""
        bundle_info = {
            "CFBundleIdentifier": "com.example.app",
            "CFBundleShortVersionString": "2.0",
            "IFPkgFlagDefaultLocation": "/Applications",
            "IFPkgFlagAuthorizationAction": "RootAuthorization",
            "IFPkgFlagRestartAction": "None",
            "IFPkgFlagInstalledSize": 2048,
        }

        flat_tree = self.processor.convert_bundle_info_to_flat(bundle_info)
        root = flat_tree.getroot()

        self.assertEqual(root.tag, "pkg-info")
        self.assertEqual(root.get("format-version"), "2")
        self.assertEqual(root.get("identifier"), "com.example.app")
        self.assertEqual(root.get("version"), "2.0")
        self.assertEqual(root.get("install-location"), "/Applications")
        self.assertEqual(root.get("auth"), "root")
        self.assertEqual(root.get("postinstall-action"), "none")

        payload = root.find("payload")
        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("installKBytes"), "2048")

    def test_convert_bundle_info_to_flat_restart_actions(self):
        """Test bundle to flat conversion with different restart actions."""
        restart_actions = {
            "None": "none",
            "RecommendRestart": "restart",
            "RequireLogout": "logout",
            "RequireRestart": "restart",
            "RequireShutdown": "shutdown",
        }

        for bundle_action, expected_flat in restart_actions.items():
            with self.subTest(bundle_action=bundle_action):
                bundle_info = {
                    "CFBundleIdentifier": "com.example.app",
                    "IFPkgFlagRestartAction": bundle_action,
                }

                flat_tree = self.processor.convert_bundle_info_to_flat(bundle_info)
                root = flat_tree.getroot()

                self.assertEqual(root.get("postinstall-action"), expected_flat)

    def test_convert_bundle_info_to_flat_auth_none(self):
        """Test bundle to flat conversion with non-root authorization."""
        bundle_info = {
            "CFBundleIdentifier": "com.example.app",
            "IFPkgFlagAuthorizationAction": "NoAuthorization",
        }

        flat_tree = self.processor.convert_bundle_info_to_flat(bundle_info)
        root = flat_tree.getroot()

        self.assertEqual(root.get("auth"), "none")

    def test_convert_flat_info_to_bundle_raises_error(self):
        """Test that flat to bundle conversion raises error."""
        with self.assertRaises(ProcessorError) as context:
            self.processor.convert_flat_info_to_bundle({})

        self.assertIn(
            "Bundle package creation no longer supported", str(context.exception)
        )

    # Test pkgroot size calculation
    def test_get_pkgroot_size_empty(self):
        """Test size calculation of empty pkgroot."""
        size, nfiles = self.processor.get_pkgroot_size(self.pkgroot)

        # Empty directory should have 1 file (the directory itself) and 0 KB
        self.assertEqual(size, 0)
        self.assertEqual(nfiles, 1)

    def test_get_pkgroot_size_with_files(self):
        """Test size calculation with files."""
        # Create files of specific sizes
        self._create_test_files(num_files=3, file_size=4096)  # Each file is 1 KB

        size, nfiles = self.processor.get_pkgroot_size(self.pkgroot)

        # 1 directory + 3 files = 4 total files
        # Each 4KB file rounds up to 1 KB
        self.assertEqual(nfiles, 4)
        self.assertEqual(size, 3)  # 3 files * 1 KB each

    def test_get_pkgroot_size_rounding(self):
        """Test that file sizes are rounded up to nearest 4KB."""
        # Create a file that's slightly larger than 4KB
        file_path = os.path.join(self.pkgroot, "test.txt")
        with open(file_path, "w") as f:
            f.write("x" * 4097)  # Just over 4KB

        size, nfiles = self.processor.get_pkgroot_size(self.pkgroot)

        # Should round up to 2 KB (next 4KB boundary)
        self.assertEqual(size, 2)
        self.assertEqual(nfiles, 2)  # 1 directory + 1 file

    def test_get_pkgroot_size_subdirectories(self):
        """Test size calculation with subdirectories."""
        # Create subdirectory with files
        subdir = os.path.join(self.pkgroot, "subdir")
        os.makedirs(subdir)

        # Add files to both root and subdirectory
        with open(os.path.join(self.pkgroot, "root_file.txt"), "w") as f:
            f.write("x" * 4096)
        with open(os.path.join(subdir, "sub_file.txt"), "w") as f:
            f.write("x" * 4096)

        size, nfiles = self.processor.get_pkgroot_size(self.pkgroot)

        # 2 directories + 2 files = 4 total files
        self.assertEqual(nfiles, 4)
        self.assertEqual(size, 2)  # 2 files * 1 KB each

    # Test flat info creation
    def test_create_flat_info_basic(self):
        """Test basic flat info creation."""
        self._create_xml_template()
        template = self.processor.load_template(
            self.processor.env["template_path"], "flat"
        )
        self._create_test_files(num_files=2, file_size=4096)

        self.processor.create_flat_info(template)

        # Verify the file was created
        self.assertTrue(os.path.exists(self.infofile))

        # Parse and verify the content
        tree = ElementTree.parse(self.infofile)
        root = tree.getroot()

        self.assertEqual(root.get("version"), "1.0.0")

        payload = root.find("payload")
        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("installKBytes"), "2")  # 2 files * 1 KB
        self.assertEqual(payload.get("numberOfFiles"), "3")  # 1 dir + 2 files

    def test_create_flat_info_updates_existing_payload(self):
        """Test that create_flat_info updates existing payload element."""
        # Create template with existing payload
        root = ElementTree.Element("pkg-info")
        root.set("identifier", "com.example.app")

        payload = ElementTree.SubElement(root, "payload")
        payload.set("installKBytes", "999")
        payload.set("numberOfFiles", "999")

        template = ElementTree.ElementTree(root)
        self._create_test_files(num_files=1, file_size=4096)

        self.processor.create_flat_info(template)

        # Verify payload was updated
        tree = ElementTree.parse(self.infofile)
        root = tree.getroot()
        payload = root.find("payload")

        self.assertEqual(payload.get("installKBytes"), "1")
        self.assertEqual(payload.get("numberOfFiles"), "2")

    def test_create_flat_info_creates_payload_if_missing(self):
        """Test that create_flat_info creates payload element if missing."""
        # Create template without payload
        root = ElementTree.Element("pkg-info")
        root.set("identifier", "com.example.app")

        template = ElementTree.ElementTree(root)
        self._create_test_files(num_files=1, file_size=4096)

        self.processor.create_flat_info(template)

        # Verify payload was created
        tree = ElementTree.parse(self.infofile)
        root = tree.getroot()
        payload = root.find("payload")

        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("installKBytes"), "1")
        self.assertEqual(payload.get("numberOfFiles"), "2")

    def test_create_flat_info_invalid_root_tag(self):
        """Test that invalid root tag raises ProcessorError."""
        root = ElementTree.Element("invalid-root")
        template = ElementTree.ElementTree(root)

        with self.assertRaises(ProcessorError) as context:
            self.processor.create_flat_info(template)

        self.assertIn("PackageInfo root should be pkg-info", str(context.exception))

    def test_create_bundle_info_raises_error(self):
        """Test that create_bundle_info raises error."""
        with self.assertRaises(ProcessorError) as context:
            self.processor.create_bundle_info({})

        self.assertIn(
            "Bundle package creation no longer supported", str(context.exception)
        )

    # Test edge cases and error conditions
    def test_main_with_plist_template_flat_package(self):
        """Test main with plist template for flat package (conversion)."""
        self._create_plist_template()
        self._create_test_files(num_files=1, file_size=4096)

        self.processor.main()

        # Should successfully create PackageInfo from plist template
        self.assertTrue(os.path.exists(self.infofile))

        tree = ElementTree.parse(self.infofile)
        root = tree.getroot()
        self.assertEqual(root.tag, "pkg-info")
        self.assertEqual(root.get("version"), "1.0.0")

    def test_main_with_xml_template_flat_package(self):
        """Test main with XML template for flat package."""
        self._create_xml_template()
        self._create_test_files(num_files=1, file_size=4096)

        self.processor.main()

        # Should successfully create PackageInfo
        self.assertTrue(os.path.exists(self.infofile))

        tree = ElementTree.parse(self.infofile)
        root = tree.getroot()
        self.assertEqual(root.get("version"), "1.0.0")

    def test_complex_bundle_to_flat_conversion(self):
        """Test complex bundle info with all possible fields."""
        bundle_info = {
            "CFBundleIdentifier": "com.example.complex_app",
            "CFBundleShortVersionString": "3.2.1",
            "IFPkgFlagDefaultLocation": "/usr/local/bin",
            "IFPkgFlagAuthorizationAction": "RootAuthorization",
            "IFPkgFlagRestartAction": "RequireRestart",
            "IFPkgFlagInstalledSize": 4096,
            "ExtraField": "should_be_ignored",  # This should not appear in flat format
        }

        flat_tree = self.processor.convert_bundle_info_to_flat(bundle_info)
        root = flat_tree.getroot()

        # Verify all expected conversions
        self.assertEqual(root.get("identifier"), "com.example.complex_app")
        self.assertEqual(root.get("version"), "3.2.1")
        self.assertEqual(root.get("install-location"), "/usr/local/bin")
        self.assertEqual(root.get("auth"), "root")
        self.assertEqual(root.get("postinstall-action"), "restart")

        payload = root.find("payload")
        self.assertEqual(payload.get("installKBytes"), "4096")

        # Verify extra field is not included
        self.assertIsNone(root.get("ExtraField"))

    def test_pkgroot_with_symlinks(self):
        """Test pkgroot size calculation with symbolic links."""
        # Create a regular file
        regular_file = os.path.join(self.pkgroot, "regular.txt")
        with open(regular_file, "w") as f:
            f.write("x" * 4096)

        # Create a symbolic link
        symlink_path = os.path.join(self.pkgroot, "symlink.txt")
        os.symlink(regular_file, symlink_path)

        size, nfiles = self.processor.get_pkgroot_size(self.pkgroot)

        # Should count both regular file and symlink
        # Directory + regular file + symlink = 3 files
        self.assertEqual(nfiles, 3)
        # Size should include regular file (1 KB) but symlink size may vary
        self.assertGreaterEqual(size, 1)


if __name__ == "__main__":
    unittest.main()
