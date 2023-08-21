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

import imp
import json
import os
import plistlib
import sys
import unittest
from textwrap import dedent
from unittest.mock import mock_open, patch

import autopkglib

autopkg = imp.load_source(
    "autopkg", os.path.join(os.path.dirname(__file__), "..", "autopkg")
)


class TestAutoPkg(unittest.TestCase):
    """Test class for AutoPkglib itself."""

    # Some globals for mocking
    good_json = json.dumps({"CACHE_DIR": "/path/to/cache"})
    download_recipe = dedent(
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
    download_struct = plistlib.loads(download_recipe.encode("utf-8"))
    munki_recipe = dedent(
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
    munki_struct = plistlib.loads(munki_recipe.encode("utf-8"))

    def setUp(self):
        # This forces autopkglib to accept our patching of memoize
        imp.reload(autopkglib)
        autopkglib.globalPreferences

    def tearDown(self):
        pass

    @unittest.skipUnless("win32" in sys.platform.lower(), "requires Windows")
    @patch("autopkglib.sys")
    @patch("autopkglib.is_executable")
    @patch("autopkglib.os.get_exec_path")
    @patch("autopkglib.os.path")
    def test_find_binary_windows(self, mock_ospath, mock_getpath, mock_isexe, mock_sys):
        # Forcibly use ntpath regardless of platform to test "windows" anywhere.
        import ntpath

        mock_ospath.join = ntpath.join
        mock_sys.platform = "Win32"
        mock_getpath.return_value = [r"C:\Windows\system32", r"C:\CurlInstall"]
        mock_isexe.side_effect = [False, True]
        result = autopkglib.find_binary("curl")
        self.assertEqual(result, r"C:\CurlInstall\curl.exe")

    @patch("autopkglib.sys")
    @patch("autopkglib.is_executable")
    @patch("autopkglib.os.get_exec_path")
    @patch("autopkglib.os.path")
    def test_find_binary_posixy(self, mock_ospath, mock_getpath, mock_isexe, mock_sys):
        # Forcibly use posixpath regardless of platform to test "linux/mac" anywhere.
        import posixpath

        mock_ospath.join = posixpath.join
        mock_sys.platform = "Darwin"
        mock_getpath.return_value = ["/usr/bin", "/usr/local/bin"]
        mock_isexe.side_effect = [True, False]
        result = autopkglib.find_binary("curl")
        self.assertEqual(result, "/usr/bin/curl")

    def test_get_identifier_returns_identifier(self):
        """get_identifier should return the identifier."""
        recipe = plistlib.loads(self.download_recipe.encode("utf-8"))
        id = autopkglib.get_identifier(recipe)
        self.assertEqual(id, "com.github.autopkg.download.googlechrome")

    def test_get_identifier_returns_none(self):
        """get_identifier should return None if no identifier is found."""
        recipe = plistlib.loads(self.download_recipe.encode("utf-8"))
        del recipe["Identifier"]
        id = autopkglib.get_identifier(recipe)
        self.assertIsNone(id)

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data=download_recipe.encode("utf-8"),
    )
    @patch("autopkg.plistlib.load")
    @patch("os.path.isfile")
    def test_get_identifier_from_recipe_file_returns_identifier(
        self, mock_isfile, mock_load, mock_file
    ):
        """get_identifier_from_recipe_file should return identifier."""
        mock_isfile.return_value = True
        mock_load.return_value = self.download_struct
        id = autopkglib.get_identifier_from_recipe_file("fake")
        self.assertEqual(id, "com.github.autopkg.download.googlechrome")

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data=download_recipe.encode("utf-8"),
    )
    @patch("autopkg.plistlib.load")
    def test_get_identifier_from_recipe_file_returns_none(self, mock_load, mock_read):
        """get_identifier_from_recipe_file should return None if no identifier."""
        mock_read.return_value = self.download_struct
        del mock_read.return_value["Identifier"]
        id = autopkglib.get_identifier_from_recipe_file("fake")
        self.assertIsNone(id)


if __name__ == "__main__":
    unittest.main()
