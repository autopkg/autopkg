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

    @patch("autopkglib.FileFinder.globfind")
    def test_no_fail_if_good_env(self, mock_glob):
        """The processor should not raise any exceptions if run normally."""
        self.processor.env = self.good_env
        mock_glob.return_value = "test"
        self.processor.main()

    @patch("autopkglib.FileFinder.globfind")
    def test_found_a_match(self, mock_glob):
        """If we find a match, it should be in the env."""
        self.processor.env = self.good_env
        mock_glob.return_value = "test"
        self.processor.main()
        self.assertEqual(self.processor.env["found_filename"], "test")

    @patch("autopkglib.FileFinder.unmount")
    @patch("autopkglib.FileFinder.mount")
    @patch("autopkglib.FileFinder.globfind")
    def test_found_a_dmg_match(self, mock_glob, mock_mount, mock_unmount):
        """If we find a match inside a DMG, it should be in the env."""
        self.processor.env = {
            "find_method": "glob",
            "pattern": "/tmp/fake.dmg/whatever",
        }
        mock_mount.return_value = "/tmp/fake_dmg_mount"
        mock_glob.return_value = "/tmp/fake_dmg_mount/whatever"
        mock_unmount.return_value = None
        self.processor.main()
        self.assertEqual(self.processor.env["found_filename"], mock_glob.return_value)
        self.assertEqual(self.processor.env["dmg_found_filename"], "whatever")


if __name__ == "__main__":
    unittest.main()
