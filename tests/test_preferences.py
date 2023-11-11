#!/usr/local/autopkg/python

import json
import plistlib
import unittest
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest import mock
from unittest.mock import patch

from autopkg.autopkglib import Preferences

TEST_JSON_PREFS = b"""{"CACHE_DIR": "/path/to/cache"}"""
TEST_PLIST_PREFS = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
<key>CACHE_DIR</key>
<string>/path/to/cache</string>
</dict>
</plist>
"""


def patch_open(data: bytes, **kwargs) -> mock._patch:
    """Patches `open` to return return a `BytesIO` object.

    This is similar to calling `patch("builtins.open, new_callable=mock_open, ...)`,
    but returns a real IO-type object that supports everything that the usual
    file object returned by open supports, ensuring greater compatibility with
    arbitrary libraries at the cost of not resetting itself each time its called."""

    def _new_mock():
        omock = mock.MagicMock(name="open", spec="open")
        omock.side_effect = lambda *args, **kwargs: BytesIO(data)
        return omock

    return patch("builtins.open", new_callable=_new_mock, **kwargs)


class TestPreferences(unittest.TestCase):
    """Test Preferences class"""

    PRIMARY_NON_MACOS_PLATFORMS = ["Linux", "Windows"]

    def setUp(self):
        self._workdir = TemporaryDirectory()
        self.mock_platform = patch("autopkg.autopkglib.sys.platform").start()
        # Force loading to go through the file-backed path by default.
        self.mock_platform.return_value = "__HighlyUnlikely-Platform-Name__"

        # Mock all of these for all tests to help ensure we do not accidentally
        # use the real macOS preference store.
        self.mock_copykeylist = patch(
            "autopkg.autopkglib.CFPreferencesCopyKeyList"
        ).start()
        # Return an empty list of preference keys by default. Makes a new list on
        # every call to ensure no false sharing.
        self.mock_copykeylist.side_effect = lambda *_, **_kw: list()
        self.mock_copyappvalue = patch(
            "autopkg.autopkglib.CFPreferencesCopyAppValue"
        ).start()
        self.mock_setappvalue = patch(
            "autopkg.autopkglib.CFPreferencesSetAppValue"
        ).start()
        self.mock_appsynchronize = patch(
            "autopkg.autopkglib.CFPreferencesAppSynchronize"
        ).start()

        self.mock_appdirs = patch("autopkg.autopkglib.appdirs").start()
        # Ensure we don't accidentally load real config and muck up tests.
        self.mock_appdirs.user_config_dir.return_value = self._workdir.name

        self.addCleanup(patch.stopall)
        self.addCleanup(self._workdir.cleanup)

    def tearDown(self):
        pass

    def test_new_prefs_object_is_empty(self):
        """A new Preferences object should be empty with no config."""
        test_platforms = ["Darwin"]
        test_platforms += self.PRIMARY_NON_MACOS_PLATFORMS
        for platform in test_platforms:
            with self.subTest(platform=platform):
                self.mock_platform.return_value = platform
                fake_prefs = Preferences()
                self.assertEqual(fake_prefs.file_path, None)
                self.assertEqual(fake_prefs.type, None)
                self.assertEqual(fake_prefs.get_all_prefs(), {})

    def test_get_macos_pref_returns_value(self):
        """get_macos_pref should return a value."""
        self.mock_copyappvalue.return_value = "FakeValue"
        fake_prefs = Preferences()
        value = fake_prefs._get_macos_pref("fake")
        self.assertEqual(value, "FakeValue")

    def test_parse_file_is_empty_by_default(self):
        """Parsing a non-existent file should return an empty dict."""
        fake_prefs = Preferences()
        value = fake_prefs._parse_json_or_plist_file("fake_filepath")
        self.assertEqual(value, {})

    @patch_open(TEST_JSON_PREFS)
    def test_parse_file_reads_json(self, _mock_file):
        """Parsing a JSON file should produce a dictionary."""
        fake_prefs = Preferences()
        value = fake_prefs._parse_json_or_plist_file("fake_filepath")
        self.assertEqual(value, json.loads(TEST_JSON_PREFS))

    @patch_open(TEST_PLIST_PREFS)
    def test_parse_file_reads_plist(self, _mock_file):
        """Parsing a PList file should produce a dictionary."""
        fake_prefs = Preferences()
        value = fake_prefs._parse_json_or_plist_file("fake_filepath")
        self.assertEqual(value, plistlib.loads(TEST_PLIST_PREFS))

    @patch_open(TEST_PLIST_PREFS)
    def test_read_file_fills_prefs(self, _mock_file):
        """read_file should populate the prefs object."""
        fake_prefs = Preferences()
        fake_prefs.read_file("fake_filepath")
        value = fake_prefs.get_all_prefs()
        self.assertEqual(value, plistlib.loads(TEST_PLIST_PREFS))
        self.assertEqual(fake_prefs.type, "plist")

    @patch.object(Preferences, "write_file")
    @patch.object(Preferences, "_set_macos_pref")
    def test_set_pref_no_file(self, mock_write_file, mock_set_macos_pref):
        """set_pref should change the prefs object, but not write when no file loaded"""
        fake_prefs = Preferences()
        fake_prefs.set_pref("TEST_KEY", "fake_value")
        mock_write_file.assert_not_called()
        mock_set_macos_pref.assert_not_called()
        value = fake_prefs.get_pref("TEST_KEY")
        self.assertEqual(value, "fake_value")

    @patch_open(TEST_JSON_PREFS)
    def test_init_prefs_files(self, _mock_open):
        """Preferences should load file-backed config on primary platforms."""
        for actual_platform in self.PRIMARY_NON_MACOS_PLATFORMS:
            with self.subTest(platform=actual_platform):
                self.mock_platform.return_value = actual_platform
                prefs = Preferences()
                self.assertNotEqual(prefs.file_path, None)
                value = prefs.get_all_prefs()
                self.assertEqual(value, json.loads(TEST_JSON_PREFS))
                self.assertEqual(prefs.type, "json")

    @patch_open(b"{}")
    @patch.object(Preferences, "write_file")
    def test_set_pref_files(self, mock_write_file, mock_open):
        """Preferences().set_pref should write file on file-backed config platforms"""
        for actual_platform in self.PRIMARY_NON_MACOS_PLATFORMS:
            with self.subTest(platform=actual_platform):
                self.mock_platform.return_value = actual_platform
                fake_prefs = Preferences()
                self.assertNotEqual(fake_prefs.file_path, None)
                fake_prefs.set_pref("TEST_KEY", "fake_value")
                mock_write_file.assert_called()
                value = fake_prefs.get_pref("TEST_KEY")
                self.assertEqual(value, "fake_value")
                mock_write_file.reset_mock()

    @patch.object(Preferences, "_set_macos_pref")
    def test_set_pref_mac(self, mock_set_macos_pref):
        """Preferences().set_pref should write macOS preference store on macOS."""
        self.mock_platform.lower.return_value = "darwin"
        fake_prefs = Preferences()
        fake_prefs.set_pref("TEST_KEY", "fake_value")
        value = fake_prefs.get_pref("TEST_KEY")
        self.assertEqual(value, "fake_value")
        mock_set_macos_pref.assert_called()

    @patch.object(Preferences, "_set_macos_pref")
    @patch.object(Preferences, "write_file")
    @patch_open(TEST_JSON_PREFS)
    def test_set_pref_mac_files(self, mock_open, mock_write_file, mock_set_macos_pref):
        """Preferences().set_pref should write file on macOS and read_file() used."""
        self.mock_platform.return_value = "darwin"
        fake_prefs = Preferences()
        fake_prefs.read_file("fake_config_file")
        mock_open.assert_called()
        fake_prefs.set_pref("TEST_KEY", "fake_value")
        mock_write_file.assert_called()
        mock_set_macos_pref.assert_not_called()
        value = fake_prefs.get_pref("TEST_KEY")
        self.assertEqual(value, "fake_value")
