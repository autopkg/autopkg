#!/usr/bin/env python

import imp
import plistlib
import unittest
from textwrap import dedent

from mock import patch


# DO NOT MOVE THIS! This needs to happen BEFORE importing autopkglib
patch("autopkglib.memoize", lambda x: x).start()
import autopkglib  # isort: skip

autopkg = imp.load_source("autopkg", "autopkg")


class TestAutoPkg(unittest.TestCase):
    """Test class for AutoPkglib itself."""

    def setUp(self):
        # This forces autopkglib to accept our patching of memoize
        imp.reload(autopkglib)
        self.download_recipe = dedent(
            """\
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
            <plist version="1.0">
            <dict>
                <key>Description</key>
                <string>Downloads latest Google Chrome disk image.</string>
                <key>Identifier</key>
                <string>com.github.autopkg.download.googlechrome</string>
                <key>Input</key>
                <dict>
                    <key>NAME</key>
                    <string>GoogleChrome</string>
                    <key>DOWNLOAD_URL</key>
                    <string>https://dl.google.com/chrome/mac/stable/GGRO/googlechrome.dmg</string>
                </dict>
                <key>MinimumVersion</key>
                <string>0.2.0</string>
                <key>Process</key>
                <array>
                    <dict>
                        <key>Processor</key>
                        <string>URLDownloader</string>
                        <key>Arguments</key>
                        <dict>
                            <key>url</key>
                            <string>%DOWNLOAD_URL%</string>
                            <key>filename</key>
                            <string>%NAME%.dmg</string>
                        </dict>
                    </dict>
                    <dict>
                        <key>Processor</key>
                        <string>EndOfCheckPhase</string>
                    </dict>
                    <dict>
                        <key>Processor</key>
                        <string>CodeSignatureVerifier</string>
                        <key>Arguments</key>
                        <dict>
                            <key>input_path</key>
                            <string>%pathname%/Google Chrome.app</string>
                            <key>strict_verification</key>
                            <false/>
                            <key>requirement</key>
                            <string>(identifier "com.google.Chrome" or identifier "com.google.Chrome.beta" or identifier "com.google.Chrome.dev" or identifier "com.google.Chrome.canary") and (certificate leaf = H"85cee8254216185620ddc8851c7a9fc4dfe120ef" or certificate leaf = H"c9a99324ca3fcb23dbcc36bd5fd4f9753305130a")</string>
                        </dict>
                    </dict>
                </array>
            </dict>
            </plist>
        """
        )
        self.munki_recipe = dedent(
            """\
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
            <plist version="1.0">
            <dict>
                <key>Description</key>
                <string>Downloads the latest Google Chrome disk image and imports into Munki.</string>
                <key>Identifier</key>
                <string>com.github.autopkg.munki.google-chrome</string>
                <key>Input</key>
                <dict>
                    <key>NAME</key>
                    <string>GoogleChrome</string>
                    <key>MUNKI_REPO_SUBDIR</key>
                    <string>apps</string>
                    <key>pkginfo</key>
                    <dict>
                        <key>catalogs</key>
                        <array>
                            <string>testing</string>
                        </array>
                        <key>description</key>
                        <string>Chrome is a fast, simple, and secure web browser, built for the modern web.</string>
                        <key>display_name</key>
                        <string>Google Chrome</string>
                        <key>name</key>
                        <string>%NAME%</string>
                        <key>unattended_install</key>
                        <true/>
                    </dict>
                </dict>
                <key>MinimumVersion</key>
                <string>0.2.0</string>
                <key>ParentRecipe</key>
                <string>com.github.autopkg.download.googlechrome</string>
                <key>Process</key>
                <array>
                    <dict>
                        <key>Arguments</key>
                        <dict>
                            <key>pkg_path</key>
                            <string>%pathname%</string>
                            <key>repo_subdirectory</key>
                            <string>%MUNKI_REPO_SUBDIR%</string>
                        </dict>
                        <key>Processor</key>
                        <string>MunkiImporter</string>
                    </dict>
                </array>
            </dict>
            </plist>
        """
        )

    def tearDown(self):
        pass

    @patch("autopkglib.platform.platform")
    def test_is_mac_returns_true_on_mac(self, mock_platform):
        """On macOS, is_mac() should return True."""
        mock_platform.return_value = "Darwin-somethingsomething"
        result = autopkglib.is_mac()
        self.assertEqual(result, True)

    @patch("autopkglib.platform.platform")
    def test_is_mac_returns_false_on_not_mac(self, mock_platform):
        """On not-macOS, is_mac() should return False."""
        mock_platform.return_value = "Windows-somethingsomething"
        result = autopkglib.is_mac()
        self.assertEqual(result, False)

    @patch("autopkglib.platform.platform")
    def test_is_windows_returns_true_on_windows(self, mock_platform):
        """On Windows, is_windows() should return True."""
        mock_platform.return_value = "Windows-somethingsomething"
        result = autopkglib.is_windows()
        self.assertEqual(result, True)

    @patch("autopkglib.platform.platform")
    def test_is_windows_returns_false_on_not_windows(self, mock_platform):
        """On not-Windows, is_windows() should return False."""
        mock_platform.return_value = "Darwin-somethingsomething"
        result = autopkglib.is_windows()
        self.assertEqual(result, False)

    @patch("autopkglib.platform.platform")
    def test_is_linux_returns_true_on_linux(self, mock_platform):
        """On Linux, is_linux() should return True."""
        mock_platform.return_value = "Linux-somethingsomething"
        result = autopkglib.is_linux()
        self.assertEqual(result, True)

    @patch("autopkglib.platform.platform")
    def test_is_linux_returns_false_on_not_linux(self, mock_platform):
        """On not-Linux, is_linux() should return False."""
        mock_platform.return_value = "Windows-somethingsomething"
        result = autopkglib.is_linux()
        self.assertEqual(result, False)

    def test_get_identifier_returns_identifier(self):
        """get_identifier should return the identifier."""
        recipe = plistlib.readPlistFromString(self.download_recipe)
        id = autopkglib.get_identifier(recipe)
        self.assertEqual(id, "com.github.autopkg.download.googlechrome")

    def test_get_identifier_returns_none(self):
        """get_identifier should return None if no identifier is found."""
        recipe = plistlib.readPlistFromString(self.download_recipe)
        del recipe["Identifier"]
        id = autopkglib.get_identifier(recipe)
        self.assertIsNone(id)

    @patch("autopkg.FoundationPlist.readPlist")
    def test_get_identifier_from_recipe_file_returns_identifier(self, mock_read):
        """get_identifier_from_recipe-file should return identifier."""
        mock_read.return_value = plistlib.readPlistFromString(self.download_recipe)
        id = autopkglib.get_identifier_from_recipe_file("fake")
        self.assertEqual(id, "com.github.autopkg.download.googlechrome")

    @patch("autopkg.FoundationPlist.readPlist")
    def test_get_identifier_from_recipe_file_returns_none(self, mock_read):
        """get_identifier_from_recipe-file should return None if no identifier."""
        mock_read.return_value = plistlib.readPlistFromString(self.download_recipe)
        del mock_read.return_value["Identifier"]
        id = autopkglib.get_identifier_from_recipe_file("fake")
        self.assertIsNone(id)


if __name__ == "__main__":
    unittest.main()
