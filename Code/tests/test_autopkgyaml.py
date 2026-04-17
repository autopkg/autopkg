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
"""Tests for autopkgyaml YAML serialization and Munki format support."""

import os
import plistlib
import sys
import tempfile
import unittest
from collections import OrderedDict
from datetime import datetime

# Ensure the Code directory is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from autopkglib.autopkgyaml import (
    STRING_KEYS,
    _clean_float_to_str,
    _normalize_yaml_types,
    _sorted_keys,
    _PKGINFO_HEAD_KEYS,
    _RECEIPT_HEAD_KEYS,
    _INSTALLS_HEAD_KEYS,
    detect_munki_format,
    dump_pkginfo_yaml,
    dumps_pkginfo_yaml,
    is_yaml_path,
    is_plist_path,
    load_munki_file,
    load_pkginfo_yaml,
    loads_pkginfo_yaml,
    parse_munki_data,
    save_munki_file,
)


class TestVersionStringQuoting(unittest.TestCase):
    """Version strings must survive yaml round-trip without becoming floats."""

    def test_version_string_roundtrip(self):
        """version: '126.0' should not become 126.0 float."""
        pkginfo = {"name": "Firefox", "version": "126.0", "display_name": "Firefox"}
        yaml_str = dumps_pkginfo_yaml(pkginfo)
        loaded = loads_pkginfo_yaml(yaml_str)
        self.assertIsInstance(loaded["version"], str)
        self.assertEqual(loaded["version"], "126.0")

    def test_integer_version_roundtrip(self):
        """version: '14' should not become int 14."""
        pkginfo = {"name": "Xcode", "version": "14", "display_name": "Xcode"}
        yaml_str = dumps_pkginfo_yaml(pkginfo)
        loaded = loads_pkginfo_yaml(yaml_str)
        self.assertIsInstance(loaded["version"], str)
        self.assertEqual(loaded["version"], "14")

    def test_minimum_os_version_roundtrip(self):
        pkginfo = {
            "name": "Test",
            "version": "1.0",
            "minimum_os_version": "10.15",
        }
        yaml_str = dumps_pkginfo_yaml(pkginfo)
        loaded = loads_pkginfo_yaml(yaml_str)
        self.assertIsInstance(loaded["minimum_os_version"], str)
        self.assertEqual(loaded["minimum_os_version"], "10.15")

    def test_receipt_version_roundtrip(self):
        pkginfo = {
            "name": "Test",
            "version": "2.0",
            "receipts": [
                {"packageid": "com.example.test", "version": "2.0"},
            ],
        }
        yaml_str = dumps_pkginfo_yaml(pkginfo)
        loaded = loads_pkginfo_yaml(yaml_str)
        self.assertIsInstance(loaded["receipts"][0]["version"], str)
        self.assertEqual(loaded["receipts"][0]["version"], "2.0")

    def test_unquoted_trailing_zero_version_preserved(self):
        """`version: 10.10` (UNQUOTED in source) must arrive as the string
        '10.10', not float 10.1. This is the canonical bug PR #1023 fixes
        for recipes; the same fix here covers Munki pkginfo and catalogs.
        Without AutoPkgYAMLLoader removing the float implicit resolver,
        Pyyaml collapses 10.10 to 10.1 before any post-parse normalization
        can recover the trailing zero."""
        # Note: deliberately UNQUOTED in the source yaml to exercise the
        # loader-level fix. Quoted '10.10' would be safe even without it.
        yaml_input = (
            "name: TestApp\n"
            "version: 10.10\n"
            "minimum_os_version: 10.10\n"
        )
        loaded = loads_pkginfo_yaml(yaml_input)
        self.assertIsInstance(loaded["version"], str)
        self.assertEqual(loaded["version"], "10.10")
        self.assertEqual(loaded["minimum_os_version"], "10.10")


class TestCleanFloat(unittest.TestCase):
    def test_float_no_trailing_zero(self):
        self.assertEqual(_clean_float_to_str(14.0), "14")

    def test_float_decimal(self):
        self.assertEqual(_clean_float_to_str(10.15), "10.15")

    def test_int(self):
        self.assertEqual(_clean_float_to_str(14), "14")


class TestNormalizeYamlTypes(unittest.TestCase):
    def test_normalizes_version_float(self):
        data = {"version": 10.15, "name": "Test"}
        _normalize_yaml_types(data)
        self.assertIsInstance(data["version"], str)
        self.assertEqual(data["version"], "10.15")

    def test_normalizes_nested_receipt_version(self):
        data = {"receipts": [{"packageid": "com.foo", "version": 2.0}]}
        _normalize_yaml_types(data)
        self.assertIsInstance(data["receipts"][0]["version"], str)

    def test_leaves_non_version_keys_alone(self):
        data = {"installer_item_size": 12345, "name": "Test"}
        _normalize_yaml_types(data)
        self.assertIsInstance(data["installer_item_size"], int)

    def test_skips_booleans(self):
        data = {"version": "1.0", "uninstallable": True}
        _normalize_yaml_types(data)
        self.assertIsInstance(data["uninstallable"], bool)


class TestKeyOrdering(unittest.TestCase):
    def test_pkginfo_key_order(self):
        d = {
            "_metadata": {},
            "catalogs": ["testing"],
            "version": "1.0",
            "name": "Firefox",
            "display_name": "Mozilla Firefox",
            "autoremove": False,
        }
        keys = _sorted_keys(d, _PKGINFO_HEAD_KEYS)
        # name, display_name, version first
        self.assertEqual(keys[0], "name")
        self.assertEqual(keys[1], "display_name")
        self.assertEqual(keys[2], "version")
        # _metadata last
        self.assertEqual(keys[-1], "_metadata")
        # alpha middle
        middle = keys[3:-1]
        self.assertEqual(middle, sorted(middle))

    def test_receipt_key_order(self):
        d = {
            "version": "1.0",
            "packageid": "com.example.test",
            "optional": False,
            "installed_size": 12345,
        }
        keys = _sorted_keys(d, _RECEIPT_HEAD_KEYS)
        self.assertEqual(keys[0], "packageid")

    def test_installs_key_order(self):
        d = {
            "CFBundleShortVersionString": "1.0",
            "type": "application",
            "path": "/Applications/Test.app",
        }
        keys = _sorted_keys(d, _INSTALLS_HEAD_KEYS)
        self.assertEqual(keys[0], "path")
        self.assertEqual(keys[1], "type")


class TestMultilineStrings(unittest.TestCase):
    def test_script_uses_literal_block(self):
        pkginfo = {
            "name": "Test",
            "version": "1.0",
            "postinstall_script": "#!/bin/bash\necho hello\nexit 0\n",
        }
        yaml_str = dumps_pkginfo_yaml(pkginfo)
        self.assertIn("postinstall_script: |", yaml_str)

    def test_description_uses_folded_block(self):
        pkginfo = {
            "name": "Test",
            "version": "1.0",
            "description": "This is a long\ndescription that spans\nmultiple lines.\n",
        }
        yaml_str = dumps_pkginfo_yaml(pkginfo)
        self.assertIn("description: >", yaml_str)


class TestNoneAndEmptyFiltering(unittest.TestCase):
    def test_none_values_omitted(self):
        pkginfo = {"name": "Test", "version": "1.0", "notes": None}
        yaml_str = dumps_pkginfo_yaml(pkginfo)
        self.assertNotIn("notes", yaml_str)

    def test_empty_string_values_preserved(self):
        """Empty strings round-trip as `key: ''` (matches Munki's
        yamlutils.swift behaviour). A key explicitly set to "" is not
        the same as an absent key — bare empty would re-parse as null
        and be filtered out, so emit explicitly quoted."""
        pkginfo = {
            "name": "Test",
            "version": "1.0",
            "description": "",
            "blocking_applications": "",
        }
        yaml_str = dumps_pkginfo_yaml(pkginfo)
        # Both empty-string keys must appear in output, explicitly quoted.
        self.assertIn("description: ''", yaml_str)
        self.assertIn("blocking_applications: ''", yaml_str)
        # Round-trip: re-parse must yield empty strings, not null/missing.
        parsed = loads_pkginfo_yaml(yaml_str)
        self.assertEqual(parsed["description"], "")
        self.assertEqual(parsed["blocking_applications"], "")


class TestDatetimeSerialization(unittest.TestCase):
    def test_datetime_iso8601(self):
        dt = datetime(2025, 8, 26, 7, 7, 3)
        pkginfo = {
            "name": "Test",
            "version": "1.0",
            "_metadata": {"creation_date": dt},
        }
        yaml_str = dumps_pkginfo_yaml(pkginfo)
        self.assertIn("2025-08-26T07:07:03Z", yaml_str)


class TestBytesSerialization(unittest.TestCase):
    def test_bytes_base64(self):
        pkginfo = {
            "name": "Test",
            "version": "1.0",
            "icon_data": b"\x89PNG\r\n",
        }
        yaml_str = dumps_pkginfo_yaml(pkginfo)
        # Should be base64-encoded
        self.assertNotIn("\\x89", yaml_str)
        self.assertIn("icon_data:", yaml_str)


class TestFormatDetection(unittest.TestCase):
    def test_yaml_extension(self):
        self.assertTrue(is_yaml_path("/repo/pkgsinfo/Firefox-126.0.yaml"))
        self.assertTrue(is_yaml_path("/repo/pkgsinfo/Firefox-126.0.yml"))

    def test_plist_extension(self):
        self.assertTrue(is_plist_path("/repo/pkgsinfo/Firefox-126.0.plist"))

    def test_detect_yaml_extension(self):
        self.assertEqual(detect_munki_format("/tmp/test.yaml"), "yaml")
        self.assertEqual(detect_munki_format("/tmp/test.yml"), "yaml")

    def test_detect_plist_extension(self):
        self.assertEqual(detect_munki_format("/tmp/test.plist"), "plist")

    def test_detect_xml_content(self):
        with tempfile.NamedTemporaryFile(suffix="", delete=False, mode="w") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write("<plist>\n<dict>\n</dict>\n</plist>\n")
            path = f.name
        try:
            self.assertEqual(detect_munki_format(path), "plist")
        finally:
            os.unlink(path)

    def test_detect_yaml_content(self):
        with tempfile.NamedTemporaryFile(suffix="", delete=False, mode="w") as f:
            f.write("---\nname: Firefox\nversion: '126.0'\n")
            path = f.name
        try:
            self.assertEqual(detect_munki_format(path), "yaml")
        finally:
            os.unlink(path)

    def test_detect_yaml_no_document_start(self):
        """yaml without --- should still be detected by key: value heuristic."""
        with tempfile.NamedTemporaryFile(suffix="", delete=False, mode="w") as f:
            f.write("name: Firefox\nversion: '126.0'\ncatalogs:\n- testing\n")
            path = f.name
        try:
            self.assertEqual(detect_munki_format(path), "yaml")
        finally:
            os.unlink(path)


class TestParseMunkiData(unittest.TestCase):
    def test_parse_plist_bytes(self):
        data = {"name": "Test", "version": "1.0"}
        plist_bytes = plistlib.dumps(data)
        result = parse_munki_data(plist_bytes)
        self.assertEqual(result["name"], "Test")
        self.assertEqual(result["version"], "1.0")

    def test_parse_yaml_bytes(self):
        yaml_str = "name: Test\nversion: '1.0'\n"
        result = parse_munki_data(yaml_str.encode("utf-8"))
        self.assertEqual(result["name"], "Test")
        self.assertEqual(result["version"], "1.0")


class TestFileRoundTrip(unittest.TestCase):
    """Full round-trip: dict -> file -> dict for both formats."""

    SAMPLE_PKGINFO = {
        "name": "Firefox",
        "display_name": "Mozilla Firefox",
        "version": "126.0",
        "catalogs": ["testing"],
        "minimum_os_version": "10.15",
        "description": "A web browser\nfor everyone.\n",
        "postinstall_script": "#!/bin/bash\necho done\n",
        "receipts": [
            {"packageid": "org.mozilla.firefox", "version": "126.0"},
        ],
        "installs": [
            {
                "path": "/Applications/Firefox.app",
                "type": "application",
                "CFBundleShortVersionString": "126.0",
            },
        ],
        "_metadata": {"created_by": "autopkg"},
    }

    def test_yaml_roundtrip(self):
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", delete=False, mode="w"
        ) as f:
            path = f.name
        try:
            save_munki_file(self.SAMPLE_PKGINFO, path)
            loaded = load_munki_file(path)
            self.assertEqual(loaded["name"], "Firefox")
            self.assertEqual(loaded["version"], "126.0")
            self.assertIsInstance(loaded["version"], str)
            self.assertEqual(loaded["minimum_os_version"], "10.15")
            self.assertIsInstance(loaded["minimum_os_version"], str)
            self.assertEqual(loaded["receipts"][0]["version"], "126.0")
            self.assertIsInstance(loaded["receipts"][0]["version"], str)
            self.assertEqual(loaded["catalogs"], ["testing"])
            self.assertIn("_metadata", loaded)
        finally:
            os.unlink(path)

    def test_plist_roundtrip(self):
        with tempfile.NamedTemporaryFile(
            suffix=".plist", delete=False, mode="wb"
        ) as f:
            path = f.name
        try:
            save_munki_file(self.SAMPLE_PKGINFO, path)
            loaded = load_munki_file(path)
            self.assertEqual(loaded["name"], "Firefox")
            self.assertEqual(loaded["version"], "126.0")
        finally:
            os.unlink(path)

    def test_yaml_key_order_in_output(self):
        yaml_str = dumps_pkginfo_yaml(self.SAMPLE_PKGINFO)
        lines = yaml_str.strip().splitlines()
        # First content key should be name
        first_keys = []
        for line in lines:
            if ":" in line and not line.startswith(" ") and not line.startswith("-"):
                first_keys.append(line.split(":")[0])
        self.assertEqual(first_keys[0], "name")
        self.assertEqual(first_keys[1], "display_name")
        self.assertEqual(first_keys[2], "version")
        # _metadata should be last
        self.assertEqual(first_keys[-1], "_metadata")


class TestAutoPkgLibYamlWrite(unittest.TestCase):
    """Test that AutoPkgLib.copy_pkginfo_to_repo writes yaml when extension is yaml."""

    def test_yaml_extension_writes_yaml(self):
        from autopkglib.autopkgyaml import detect_munki_format

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = tmpdir
            pkgsinfo_path = os.path.join(repo_path, "pkgsinfo")
            os.makedirs(pkgsinfo_path)

            from autopkglib.munkirepolibs.AutoPkgLib import AutoPkgLib

            lib = AutoPkgLib(repo_path, "")
            pkginfo = {"name": "Test", "version": "1.0", "catalogs": ["testing"]}
            result_path = lib.copy_pkginfo_to_repo(pkginfo, file_extension="yaml")

            self.assertTrue(result_path.endswith(".yaml"))
            self.assertTrue(os.path.exists(result_path))
            self.assertEqual(detect_munki_format(result_path), "yaml")
            loaded = load_munki_file(result_path)
            self.assertEqual(loaded["name"], "Test")
            self.assertEqual(loaded["version"], "1.0")

    def test_plist_extension_writes_plist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = tmpdir
            pkgsinfo_path = os.path.join(repo_path, "pkgsinfo")
            os.makedirs(pkgsinfo_path)

            from autopkglib.munkirepolibs.AutoPkgLib import AutoPkgLib

            lib = AutoPkgLib(repo_path, "")
            pkginfo = {"name": "Test", "version": "1.0", "catalogs": ["testing"]}
            result_path = lib.copy_pkginfo_to_repo(pkginfo, file_extension="plist")

            self.assertTrue(result_path.endswith(".plist"))
            self.assertTrue(os.path.exists(result_path))
            with open(result_path, "rb") as f:
                loaded = plistlib.load(f)
            self.assertEqual(loaded["name"], "Test")


class TestAutoPkgLibYamlCatalog(unittest.TestCase):
    """Test that AutoPkgLib.make_catalog_db reads yaml catalogs."""

    def test_read_yaml_catalog(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = tmpdir
            catalogs_path = os.path.join(repo_path, "catalogs")
            os.makedirs(catalogs_path)

            # Write a yaml catalog
            catalog = [
                {
                    "name": "Firefox",
                    "version": "126.0",
                    "installer_item_hash": "abc123",
                    "installer_item_location": "apps/Firefox-126.0.dmg",
                },
            ]
            import yaml

            # Munki writes yaml catalogs at the same extensionless path as
            # plist catalogs (see munki/munki#1261). Format is detected by
            # content inspection on read.
            with open(
                os.path.join(catalogs_path, "all"), "w", encoding="utf-8"
            ) as f:
                yaml.dump(catalog, f)

            from autopkglib.munkirepolibs.AutoPkgLib import AutoPkgLib

            lib = AutoPkgLib(repo_path, "")
            pkgdb = lib.make_catalog_db()
            self.assertIn("abc123", pkgdb["hashes"])
            self.assertEqual(len(pkgdb["items"]), 1)
            self.assertEqual(pkgdb["items"][0]["name"], "Firefox")

    def test_read_plist_catalog(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = tmpdir
            catalogs_path = os.path.join(repo_path, "catalogs")
            os.makedirs(catalogs_path)

            catalog = [
                {
                    "name": "Chrome",
                    "version": "100.0",
                    "installer_item_hash": "def456",
                    "installer_item_location": "apps/Chrome-100.0.dmg",
                },
            ]
            with open(os.path.join(catalogs_path, "all"), "wb") as f:
                plistlib.dump(catalog, f)

            from autopkglib.munkirepolibs.AutoPkgLib import AutoPkgLib

            lib = AutoPkgLib(repo_path, "")
            pkgdb = lib.make_catalog_db()
            self.assertIn("def456", pkgdb["hashes"])

    def test_empty_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from autopkglib.munkirepolibs.AutoPkgLib import AutoPkgLib

            lib = AutoPkgLib(tmpdir, "")
            pkgdb = lib.make_catalog_db()
            self.assertEqual(len(pkgdb["items"]), 0)


if __name__ == "__main__":
    unittest.main()
