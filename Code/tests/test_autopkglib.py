#!/usr/local/autopkg/python

import importlib
import importlib.machinery
import importlib.util
import json
import os
import plistlib
import sys
import tempfile
import unittest
from textwrap import dedent
from types import SimpleNamespace
from unittest.mock import mock_open, patch

import autopkglib

autopkg_path = os.path.join(os.path.dirname(__file__), "..", "autopkg")
loader = importlib.machinery.SourceFileLoader("autopkg", autopkg_path)
autopkg = loader.load_module()
sys.modules["autopkg"] = autopkg


class TestAutoPkg(unittest.TestCase):
    """Test class for AutoPkglib itself."""

    # Some globals for mocking
    good_json = json.dumps({"CACHE_DIR": "/path/to/cache"})
    download_recipe = dedent("""\
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
    """)
    download_struct = plistlib.loads(download_recipe.encode("utf-8"))
    munki_recipe = dedent("""\
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
        """)
    munki_struct = plistlib.loads(munki_recipe.encode("utf-8"))

    def setUp(self):
        # This forces autopkglib to accept our patching of memoize
        importlib.reload(autopkglib)
        autopkglib.globalPreferences

    def tearDown(self):
        pass

    @patch("autopkglib.sys.platform", "Darwin-20.6.0")
    def test_is_mac_returns_true_on_mac(self):
        """On macOS, is_mac() should return True."""
        result = autopkglib.is_mac()
        self.assertTrue(result)

    @patch("autopkglib.sys.platform", "linux")
    def test_is_mac_returns_false_on_not_mac(self):
        """On not-macOS, is_mac() should return False."""
        result = autopkglib.is_mac()
        self.assertFalse(result)

    @patch("autopkglib.sys")
    def test_is_windows_returns_true_on_windows(self, mock_sys):
        """On Windows, is_windows() should return True."""
        mock_sys.platform = "Win32-somethingsomething"
        result = autopkglib.is_windows()
        self.assertEqual(result, True)

    @patch("autopkglib.sys")
    def test_is_windows_returns_false_on_not_windows(self, mock_sys):
        """On not-Windows, is_windows() should return False."""
        mock_sys.platform = "Darwin-somethingsomething"
        result = autopkglib.is_windows()
        self.assertEqual(result, False)

    @patch("autopkglib.sys")
    def test_is_linux_returns_true_on_linux(self, mock_sys):
        """On Linux, is_linux() should return True."""
        mock_sys.platform = "Linux-somethingsomething"
        result = autopkglib.is_linux()
        self.assertEqual(result, True)

    @patch("autopkglib.sys")
    def test_is_linux_returns_false_on_not_linux(self, mock_sys):
        """On not-Linux, is_linux() should return False."""
        mock_sys.platform = "Win32-somethingsomething"
        result = autopkglib.is_linux()
        self.assertEqual(result, False)

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


class TestPathContainment(unittest.TestCase):
    """Tests for filesystem path containment helpers."""

    def test_is_path_under_accepts_base_and_child(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            child = os.path.join(tmp_dir, "child")

            self.assertTrue(autopkglib.is_path_under(tmp_dir, tmp_dir))
            self.assertTrue(autopkglib.is_path_under(child, tmp_dir))

    def test_is_path_under_rejects_sibling_prefix(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = os.path.join(tmp_dir, "cache")
            sibling = os.path.join(tmp_dir, "cache-evil")

            self.assertFalse(autopkglib.is_path_under(sibling, base))

    def test_path_under_dirs_checks_each_declared_scope(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = os.path.join(tmp_dir, "recipes")
            child = os.path.join(base, "Shared.recipe")
            sibling = os.path.join(tmp_dir, "recipes-other", "Shared.recipe")

            self.assertTrue(autopkglib._path_under_dirs(child, [base]))
            self.assertFalse(autopkglib._path_under_dirs(sibling, [base]))

    def test_path_under_dirs_accepts_missing_scope(self):
        self.assertTrue(autopkglib._path_under_dirs("/outside/Shared.recipe", []))


class TestAutoPackagerRecipeCacheDir(unittest.TestCase):
    """Tests for AutoPackager RECIPE_CACHE_DIR creation."""

    def _packager(self, cache_dir):
        options = SimpleNamespace(verbose=0)
        return autopkglib.AutoPackager(options, {"CACHE_DIR": cache_dir})

    def _recipe(self, identifier):
        return {"Identifier": identifier, "Input": {}, "Process": []}

    def test_process_sets_recipe_cache_dir_under_cache_dir(self):
        with tempfile.TemporaryDirectory() as cache_dir:
            packager = self._packager(cache_dir)

            packager.process(self._recipe("com.example.safe"))

            expected = os.path.join(cache_dir, "com.example.safe")
            self.assertEqual(packager.env["CACHE_DIR"], cache_dir)
            self.assertEqual(packager.env["RECIPE_CACHE_DIR"], expected)
            self.assertTrue(os.path.isdir(expected))

    def test_process_expands_tilde_cache_dir(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            home_dir = os.path.join(tmp_dir, "home")
            expected_cache_dir = os.path.join(home_dir, "Library", "AutoPkg", "Cache")
            original_expanduser = os.path.expanduser

            def expanduser(path):
                if path.startswith("~"):
                    return path.replace("~", home_dir, 1)
                return original_expanduser(path)

            original_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                packager = self._packager("~/Library/AutoPkg/Cache")
                with patch.object(
                    autopkglib.os.path, "expanduser", side_effect=expanduser
                ):
                    packager.process(self._recipe("com.example.safe"))
            finally:
                os.chdir(original_cwd)

            expected = os.path.join(expected_cache_dir, "com.example.safe")
            self.assertEqual(packager.env["CACHE_DIR"], expected_cache_dir)
            self.assertEqual(packager.env["RECIPE_CACHE_DIR"], expected)
            self.assertTrue(os.path.isdir(expected))

    def test_process_makes_relative_cache_dir_absolute(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                cwd_cache_dir = os.path.join(os.getcwd(), "relative-cache")
                packager = self._packager("relative-cache")
                packager.process(self._recipe("com.example.safe"))
            finally:
                os.chdir(original_cwd)

            expected = os.path.join(cwd_cache_dir, "com.example.safe")
            self.assertEqual(packager.env["CACHE_DIR"], cwd_cache_dir)
            self.assertEqual(packager.env["RECIPE_CACHE_DIR"], expected)
            self.assertTrue(os.path.isdir(expected))

    def test_process_rejects_parent_directory_identifier_escape(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_dir = os.path.join(tmp_dir, "cache")
            packager = self._packager(cache_dir)

            with self.assertRaisesRegex(
                autopkglib.AutoPackagerError, "resolves outside CACHE_DIR"
            ):
                packager.process(self._recipe("../escape"))

            self.assertFalse(os.path.exists(os.path.join(tmp_dir, "escape")))

    def test_process_rejects_absolute_identifier_escape(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_dir = os.path.join(tmp_dir, "cache")
            outside_dir = os.path.join(tmp_dir, "outside")
            packager = self._packager(cache_dir)

            with self.assertRaisesRegex(
                autopkglib.AutoPackagerError, "resolves outside CACHE_DIR"
            ):
                packager.process(self._recipe(outside_dir))

            self.assertFalse(os.path.exists(outside_dir))


class TestUpdateData(unittest.TestCase):
    """Tests for update_data / getdata variable substitution."""

    def test_integer_value_substituted_as_string(self):
        """Integer values referenced via %KEY% must be coerced to str so
        RE_KEYREF.sub doesn't raise TypeError (regression fixed in #1038)."""
        env = {"BUILD": 42, "NAME": "MyApp-%BUILD%"}
        autopkglib.update_data(env, "NAME", env["NAME"])
        self.assertEqual(env["NAME"], "MyApp-42")

    def test_float_value_substituted_as_string(self):
        """Float values referenced via %KEY% must also be coerced to str."""
        env = {"VERSION": 1.5, "NAME": "App-%VERSION%"}
        autopkglib.update_data(env, "NAME", env["NAME"])
        self.assertEqual(env["NAME"], "App-1.5")

    def test_plain_string_substitution_unchanged(self):
        """String values are substituted as-is."""
        env = {"NAME": "Firefox", "PATH": "%NAME%.pkg"}
        autopkglib.update_data(env, "PATH", env["PATH"])
        self.assertEqual(env["PATH"], "Firefox.pkg")

    def test_missing_key_does_not_raise(self):
        """Reference to an undefined key is logged and left as-is, not raised."""
        env = {"PATH": "%UNDEFINED%.pkg"}
        autopkglib.update_data(env, "PATH", env["PATH"])
        self.assertIn("%UNDEFINED%", env["PATH"])


if __name__ == "__main__":
    unittest.main()
