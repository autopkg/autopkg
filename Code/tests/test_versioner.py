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
import posixpath
import unittest
import zipfile
from copy import deepcopy
from io import BytesIO
from tempfile import TemporaryDirectory
from typing import Any
from unittest import mock
from unittest.mock import patch

from autopkglib import VarDict
from autopkglib.Versioner import UNKNOWN_VERSION, ProcessorError, Versioner


def patch_open(data: bytes, **kwargs) -> mock._patch:
    def _new_mock():
        omock = mock.MagicMock(name="open", spec="open")
        omock.side_effect = lambda *args, **kwargs: BytesIO(data)
        return omock

    return patch("builtins.open", new_callable=_new_mock, **kwargs)


TEST_VERSION_DEFAULT_KEY: str = "CFBundleShortVersionString"
TEST_VERSION_DEFAULT: str = "1.2.3"
TEST_VERSION_CUSTOM_KEY: str = "com.someapp.customversion"
TEST_VERSION_CUSTOM: str = "3.2.1"

TEST_VERSION_PLIST: bytes = (
    f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleShortVersionString</key>
    <string>{TEST_VERSION_DEFAULT}</string>
    <key>{TEST_VERSION_CUSTOM_KEY}</key>
    <string>{TEST_VERSION_CUSTOM}</string>
</dict>
</plist>""".encode()
)

TEST_NO_VERSION_PLIST: bytes = (
    b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
</dict>
</plist>"""
)


class TestVersioner(unittest.TestCase):
    """Test class for Versioner Processor."""

    def setUp(self):
        self.maxDiff: int = 100000
        self.tmp_dir = TemporaryDirectory()
        self.good_env: dict[str, Any] = {
            "input_plist_path": "dummy_path",
            "plist_version_key": TEST_VERSION_DEFAULT_KEY,
            "RECIPE_CACHE_DIR": self.tmp_dir.name,
        }
        self.bad_env: dict[str, Any] = {}
        self.processor = Versioner(data=deepcopy(self.good_env))
        self.addCleanup(self.tmp_dir.cleanup)

    def tearDown(self):
        pass

    def _mkpath(self, *parts: str) -> str:
        """Returns a path into the per testcase temporary directory.
        On POSIX-y platforms the paths are sensible. On Windows they will non-standard
        because they will use the format `C:/path/to/tmpdir/file.txt` instead of the
        conventional `C:\\path\\...`. This is due to the interaction of code written
        only for macOS and code written to be cross-platform."""
        return posixpath.normpath(os.path.join(self.tmp_dir.name, *parts))

    def _run_direct_plist(
        self, plist: bytes, mock_dmg: mock.Mock, mock_plist: mock.Mock
    ):
        """Find version in specified plist file."""
        mock_dmg.return_value = (self.processor.env["input_plist_path"], "", "")
        mock_plist.return_value = plistlib.loads(plist)
        with patch("os.path.exists", return_value=True):
            self.processor.process()

    @patch("autopkglib.Versioner.load_plist_from_file")
    @patch("autopkglib.Versioner.parsePathForDMG")
    def test_no_fail_if_good_env(self, mock_dmg, mock_plist):
        """The processor should not raise any exceptions if run normally."""
        self._run_direct_plist(TEST_VERSION_PLIST, mock_dmg, mock_plist)

    @patch("autopkglib.Versioner.load_plist_from_file")
    @patch("autopkglib.Versioner.parsePathForDMG")
    def test_find_cfbundle_short_version(self, mock_dmg, mock_plist):
        """The processor should find version in default `CFBundleShortVersionString`."""
        self._run_direct_plist(TEST_VERSION_PLIST, mock_dmg, mock_plist)
        self.assertEqual(self.processor.env["version"], TEST_VERSION_DEFAULT)

    @patch("autopkglib.Versioner.load_plist_from_file")
    @patch("autopkglib.Versioner.parsePathForDMG")
    def test_find_custom_version(self, mock_dmg, mock_plist):
        """The processor should find version under key specified by `plist_version_key`."""
        self.processor.env["plist_version_key"] = TEST_VERSION_CUSTOM_KEY
        self._run_direct_plist(TEST_VERSION_PLIST, mock_dmg, mock_plist)
        self.assertEqual(self.processor.env["version"], TEST_VERSION_CUSTOM)

    @patch("autopkglib.Versioner.load_plist_from_file")
    @patch("autopkglib.Versioner.parsePathForDMG")
    def test_no_version_found(self, mock_dmg, mock_plist):
        """The processor should not find version if plist misses it."""
        self._run_direct_plist(TEST_NO_VERSION_PLIST, mock_dmg, mock_plist)
        self.assertEqual(self.processor.env["version"], UNKNOWN_VERSION)

    @patch("os.path.exists", return_value=True)
    @patch.object(Versioner, "_read_from_zip", return_value={})
    @patch.object(Versioner, "_read_from_dmg", return_value={})
    def test_read_auto_detect(self, mock_dmg, mock_zip, mock_exists):
        """File type auto detection"""
        mock_deserializer = mock.MagicMock()

        zip_inner_path = self._mkpath("archive.zip", "dummy", "file.txt")
        dmg_inner_path = self._mkpath("image.dmg", "dummy", "file2.txt")
        real_path = self._mkpath("regular", "dummy", "file3.txt")
        for path in (
            real_path,
            zip_inner_path,
            dmg_inner_path,
        ):
            with self.subTest(path=path):
                self.processor._read_auto_detect(
                    path=path,
                    skip_single_root_dir=False,
                    deserializer=mock_deserializer,
                )
        mock_deserializer.assert_called_once_with(real_path)
        mock_exists.assert_called_once_with(real_path)
        mock_zip.assert_called_once_with(
            zip_inner_path, False, mock_deserializer, self.processor.ZIP_EXTENSIONS
        )
        mock_dmg.assert_called_once_with(dmg_inner_path, mock_deserializer)

    def test_version_from_image(self):
        """Inner image-like (DMG/ISO) paths work"""

        @patch("os.path.exists", return_value=True)
        @patch.object(Versioner, "_read_from_zip")
        @patch.object(Versioner, "unmount")
        @patch.object(Versioner, "mount")
        # @patch("autopkglib.Versioner.load_plist_from_file")
        @patch_open(TEST_VERSION_PLIST)
        def test_for_extension(
            ext: str, mock_plist, mock_mount, mock_unmount, mock_zip, mock_exists
        ):
            mount_path: str = self._mkpath("dmg_mount")
            plist_path: str = self._mkpath(f"fake{ext}/dir/version.plist")
            dmg_path: str = self._mkpath(f"fake{ext}")
            mock_mount.return_value = mount_path
            self.processor.env["input_plist_path"] = plist_path
            result: dict[str, Any] = self.processor.process()
            mock_zip.assert_not_called()
            mock_exists.assert_called_once_with(
                os.path.normpath(os.path.join(mount_path, "dir/version.plist"))
            )
            mock_mount.assert_called_once_with(dmg_path)
            mock_unmount.assert_called_once_with(dmg_path)
            mock_plist.assert_called_once_with(
                os.path.normpath(os.path.join(mount_path, "dir/version.plist")), "rb"
            )
            self.assertIn("version", result)
            self.assertEqual(TEST_VERSION_DEFAULT, result["version"])

        for ext_case in self.processor.DMG_EXTENSIONS:
            with self.subTest(image_extension=ext_case):
                test_for_extension(ext_case)

    @patch("os.path.exists", return_value=False)
    @patch("autopkglib.Versioner._read_from_dmg")
    def test_version_from_zip(self, mock_dmg, mock_exists):
        multi_subdir = list(
            map(
                zipfile.ZipInfo,
                (
                    "subdir/",
                    "subdir/version.plist",
                    "root_level_file.txt",
                    "subdir2/",
                    "subdir2/boring_file.txt",
                ),
            )
        )
        single_subdir = list(
            map(
                zipfile.ZipInfo,
                (
                    "subdir/",
                    "subdir/version.plist",
                    "root_level_file.txt",
                ),
            )
        )
        for skip_single_root_dir, plist_file, expected_plist_file, filelist in (
            (False, "subdir/version.plist", "subdir/version.plist", multi_subdir),
            (True, "version.plist", "subdir/version.plist", single_subdir),
        ):
            zip_path = self._mkpath("test.zip")
            plist_path = self._mkpath(f"test.zip/{plist_file}")
            self.processor.env["input_plist_path"] = plist_path
            self.processor.env["skip_single_root_dir"] = skip_single_root_dir
            with patch("zipfile.ZipFile") as mock_zipfile:
                mock_zinst = mock_zipfile.return_value
                mock_zinst.open.return_value = BytesIO(TEST_VERSION_PLIST)
                mock_zinst.filelist = filelist
                mock_zinst.infolist.return_value = filelist
                mock_zinst.namelist.return_value = [zi.filename for zi in filelist]
                with self.subTest(
                    skip_single_root_dir=skip_single_root_dir,
                    plist_file=plist_file,
                    filelist=[zi.filename for zi in filelist],
                ):
                    result: VarDict = self.processor.process()
                    mock_zipfile.assert_called_once_with(zip_path)
                    mock_zinst.open.assert_called_once_with(expected_plist_file)
                    mock_exists.assert_not_called()
                    mock_dmg.assert_not_called()
                    self.assertIn("version", result)
                    self.assertEqual(TEST_VERSION_DEFAULT, result["version"])

    @patch("os.path.exists", return_value=False)
    @patch.object(Versioner, "_read_from_dmg")
    @patch("zipfile.ZipFile", autospec=True)
    def test_multi_root_zip(self, mock_zipfile, mock_dmg, mock_exists):
        """Raises ProcessorError when skip_single_root_dir=True and extra dir exists"""
        zip_path = self._mkpath("test.zip")
        plist_path = self._mkpath("test.zip/version.plist")
        self.processor.env["input_plist_path"] = plist_path
        self.processor.env["skip_single_root_dir"] = True
        mock_zinst = mock_zipfile.return_value
        mock_zinst.infolist.return_value = [
            zipfile.ZipInfo("subdir/"),
            zipfile.ZipInfo("subdir/version.plist"),
            zipfile.ZipInfo("subdir2/"),
            zipfile.ZipInfo("subdir2/file.txt"),
        ]
        for zi in mock_zinst.infolist.return_value:
            zi.file_size = 0
            zi.compress_size = 0
        mock_zinst.open.return_value.read.return_value = TEST_VERSION_PLIST
        result: dict[str, Any] = {}
        with self.assertRaisesRegex(
            ProcessorError, r".*rchive.*has more than one.*at root"
        ):
            result = self.processor.process()

        mock_zipfile.assert_called_once_with(zip_path)
        mock_zinst.open.assert_not_called()
        mock_exists.assert_not_called()
        mock_dmg.assert_not_called()
        self.assertNotIn("version", result)

    def test_path_missing_raises(self):
        """Raises ProcessorError when the provided path does not exist."""
        for path in self._mkpath(
            "not_real_version.plist", "archive.zip/nope.txt", "image.dmg/darn.json"
        ):
            with self.subTest(path=path):
                with self.assertRaisesRegex(
                    ProcessorError,
                    f"File.*{self.processor.env['input_plist_path']}.*not found",
                ):
                    self.processor.process()


if __name__ == "__main__":
    unittest.main()
