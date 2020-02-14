#!/usr/local/autopkg/python

import plistlib
import unittest
from textwrap import dedent
from unittest.mock import patch

from autopkglib.Versioner import NO_VERSION_MESSAGE, Versioner


class TestVersioner(unittest.TestCase):
    """Test class for Versioner Processor."""

    version_default_key = "CFBundleShortVersionString"
    version_default = "1.2.3"
    version_custom_key = "com.someapp.customversion"
    version_custom = "3.2.1"

    info_plist = dedent(
        f"""<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>CFBundleShortVersionString</key>
            <string>{version_default}</string>
            <key>{version_custom_key}</key>
            <string>{version_custom}</string>
        </dict>
        </plist>
    """
    ).encode()

    no_version_plist = dedent(
        """<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
        </dict>
        </plist>
    """
    ).encode()

    def setUp(self):
        self.good_env = {
            "input_plist_path": "dummy_path",
            "plist_version_key": self.version_default_key,
        }
        self.bad_env = {}
        self.input_plist = plistlib.dumps(self.good_env)
        self.processor = Versioner(infile=self.input_plist)
        self.processor.env = self.good_env

    def tearDown(self):
        pass

    def run_direct_plist(self, plist, mock_dmg, mock_plist):
        """Find version in specified plist file."""
        mock_dmg.return_value = (self.processor.env["input_plist_path"], "", "")
        mock_plist.return_value = plistlib.loads(plist)
        self.processor.main()

    @patch("autopkglib.Versioner.load_plist_from_file")
    @patch("autopkglib.Versioner.parsePathForDMG")
    def test_no_fail_if_good_env(self, mock_dmg, mock_plist):
        """The processor should not raise any exceptions if run normally."""
        self.run_direct_plist(self.info_plist, mock_dmg, mock_plist)

    @patch("autopkglib.Versioner.load_plist_from_file")
    @patch("autopkglib.Versioner.parsePathForDMG")
    def test_find_cfbundle_short_version(self, mock_dmg, mock_plist):
        """The processor should find version in default CFBundleShortVersionString."""
        self.run_direct_plist(self.info_plist, mock_dmg, mock_plist)
        self.assertEqual(self.processor.env["version"], self.version_default)

    @patch("autopkglib.Versioner.load_plist_from_file")
    @patch("autopkglib.Versioner.parsePathForDMG")
    def test_find_custom_version(self, mock_dmg, mock_plist):
        """The processor should find version under key specified by plist_version_key."""
        self.processor.env["plist_version_key"] = self.version_custom_key
        self.run_direct_plist(self.info_plist, mock_dmg, mock_plist)
        self.assertEqual(self.processor.env["version"], self.version_custom)

    @patch("autopkglib.Versioner.load_plist_from_file")
    @patch("autopkglib.Versioner.parsePathForDMG")
    def test_no_version_found(self, mock_dmg, mock_plist):
        """The processor should not find version if plist misses it."""
        self.run_direct_plist(self.no_version_plist, mock_dmg, mock_plist)
        self.assertEqual(self.processor.env["version"], NO_VERSION_MESSAGE)

    @patch("autopkglib.Versioner.unmount")
    @patch("autopkglib.Versioner.mount")
    @patch("autopkglib.Versioner.load_plist_from_file")
    @patch("autopkglib.Versioner.parsePathForDMG")
    def test_no_fail_if_dmg(self, mock_dmg, mock_plist, mock_mount, mock_unmount):
        """The processor should not raise any exceptions when plist is in the dmg image."""
        mock_dmg.return_value = ("path_to_dmg", ".dmg/", "path_to_plist")
        mock_plist.return_value = plistlib.loads(self.info_plist)
        mock_mount.return_value = "dmg_mount_point"
        self.processor.main()


if __name__ == "__main__":
    unittest.main()
