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

import plistlib
import unittest
from unittest.mock import patch

from autopkglib import ProcessorError
from autopkglib.FileFinder import FileFinder


class TestFileFinder(unittest.TestCase):
    """Test class for FileFinder Processor."""

    def setUp(self):
        self.good_env = {"find_method": "glob", "pattern": "test"}
        self.bad_env = {"find_method": "fake"}
        self.input_plist = plistlib.dumps(self.good_env)
        self.processor = FileFinder(infile=self.input_plist)

    def tearDown(self):
        pass

    def test_raise_if_not_glob(self):
        """Raise an exception if glob is not passed to find_method."""
        self.processor.env = self.bad_env
        with self.assertRaises(ProcessorError):
            self.processor.main()

    @patch.object(FileFinder, "globfind")
    def test_found_a_match(self, mock_glob):
        """If we find a match, it should be in the env."""
        self.processor.env = self.good_env
        mock_glob.return_value = "test"
        self.processor.main()
        self.assertEqual(self.processor.env["found_filename"], "test")

    @patch.object(FileFinder, "unmount")
    @patch.object(FileFinder, "mount")
    @patch("glob.glob")
    def test_found_a_dmg_match(self, mock_glob, mock_mount, mock_unmount):
        """If we find a match inside a DMG, it should be in the env."""
        self.processor.env = {
            "find_method": "glob",
            "pattern": "fake.dmg/whatever",
        }
        mock_mount.return_value = "fake_dmg_mount"
        mock_glob.return_value = ["fake_dmg_mount/whatever"]
        mock_unmount.return_value = None
        self.processor.main()
        self.assertEqual(
            self.processor.env["found_filename"], mock_glob.return_value[0]
        )
        self.assertEqual(self.processor.env["dmg_found_filename"], "whatever")

    @patch("autopkglib.FileFinder.glob")
    def test_globfind_returns_last_alphanumeric_match(self, mock_glob):
        """globfind() returns the last alphanumerically sorted match."""
        mock_glob.return_value = ["file1.txt", "file3.txt", "file2.txt"]

        result = self.processor.globfind("file*.txt")

        self.assertEqual(result, "file3.txt")

    @patch("autopkglib.FileFinder.glob")
    def test_globfind_raises_when_no_matches(self, mock_glob):
        """globfind() raises ProcessorError when glob returns no matches."""
        mock_glob.return_value = []

        with self.assertRaisesRegex(ProcessorError, "No matching filename found"):
            self.processor.globfind("file*.txt")

    @patch.object(FileFinder, "globfind")
    def test_found_basename_with_trailing_slash(self, mock_globfind):
        """found_basename uses the directory name when the match ends in a slash."""
        self.processor.env = self.good_env
        mock_globfind.return_value = "some_dir/"

        self.processor.main()

        self.assertEqual(self.processor.env["found_basename"], "some_dir")

    def test_dmg_no_matching_filename_inside(self):
        """main() raises ProcessorError when a DMG glob has no matches."""
        self.processor.env = {
            "find_method": "glob",
            "pattern": "test.dmg/pattern*",
        }

        with (
            patch.object(self.processor, "mount", return_value="test_mount"),
            patch.object(
                self.processor,
                "glob_paths_in_mount",
                return_value=("test_mount/pattern*", []),
            ),
        ):
            with self.assertRaisesRegex(ProcessorError, "No matching filename found"):
                self.processor.main()


if __name__ == "__main__":
    unittest.main()
