#!/usr/local/autopkg/python
#
# Copyright 2019 Nick McSpadden
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
from unittest.mock import patch

from autopkglib import ProcessorError
from autopkglib.PkgCopier import PkgCopier


class TestPkgCopier(unittest.TestCase):
    """Test class for PkgCopier Processor."""

    def setUp(self):
        self.good_env = {"source_pkg": "source.pkg", "pkg_path": "dest.pkg"}
        self.good_glob_dest_env = {"source_pkg": "source*", "pkg_path": "dest.pkg"}
        self.good_glob_env = {"source_pkg": "source*"}
        self.bad_env = {}
        self.input_plist = plistlib.dumps(self.good_env)
        self.processor = PkgCopier(infile=self.input_plist)

    def tearDown(self):
        pass

    @patch.object(PkgCopier, "copy")
    @patch("autopkglib.glob.glob")
    def test_no_pkgpath_uses_source_name(self, mock_glob, mock_copy):
        """If pkg_path is not specified, it should use the source name."""
        self.processor.env = self.good_glob_env
        self.processor.env["RECIPE_CACHE_DIR"] = "fake_cache_dir"
        mock_glob.return_value = ["source.pkg"]
        self.processor.main()
        mock_copy.assert_called_with(
            "source.pkg",
            os.path.join(self.processor.env["RECIPE_CACHE_DIR"], "source.pkg"),
            overwrite=True,
        )

    @patch.object(PkgCopier, "copy")
    @patch("autopkglib.glob.glob")
    def test_no_pkgpath_uses_dest_name(self, mock_glob, mock_copy):
        """If pkg_path is specified, it should be used."""
        self.processor.env = self.good_glob_dest_env
        mock_glob.return_value = ["source.pkg"]
        self.processor.main()
        mock_copy.assert_called_with(
            "source.pkg", self.processor.env["pkg_path"], overwrite=True
        )

    @patch.object(PkgCopier, "copy")
    @patch("autopkglib.glob.glob", return_value=[])
    def test_no_filesystem_matches_raises_processor_error(self, mock_glob, mock_copy):
        """An unmatched filesystem glob should report a processor error."""
        self.processor.env = self.good_glob_dest_env

        with self.assertRaisesRegex(
            ProcessorError,
            "Error processing path 'source\\*' with glob",
        ):
            self.processor.main()

        mock_copy.assert_not_called()

    def test_no_dmg_matches_raises_processor_error_and_unmounts(self):
        """An unmatched DMG glob should report an error and unmount the image."""
        self.processor.env = {
            "source_pkg": "source.dmg/*.pkg",
            "pkg_path": "dest.pkg",
        }

        with (
            patch.object(
                self.processor,
                "parsePathForDMG",
                return_value=("source.dmg", True, "*.pkg"),
            ),
            patch.object(self.processor, "mount", return_value="/Volumes/source"),
            patch.object(
                self.processor,
                "glob_paths_in_mount",
                return_value=("/Volumes/source/*.pkg", []),
            ),
            patch.object(self.processor, "unmount_if_mounted") as unmount,
            patch.object(self.processor, "copy") as copy,
            self.assertRaisesRegex(
                ProcessorError,
                "Error processing path '/Volumes/source/\\*\\.pkg' with glob",
            ),
        ):
            self.processor.main()

        copy.assert_not_called()
        unmount.assert_called_once_with("source.dmg")


if __name__ == "__main__":
    unittest.main()
