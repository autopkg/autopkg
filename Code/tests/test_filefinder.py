#!/usr/bin/env python

import plistlib
import StringIO
import unittest

import mock
from autopkglib import ProcessorError
from autopkglib.FileFinder import FileFinder


class TestFileFinder(unittest.TestCase):
    """Test class for FileFinder Processor."""

    def setUp(self):
        self.good_env = {"find_method": "glob", "pattern": "test"}
        self.bad_env = {"find_method": "fake"}
        self.input_plist = StringIO.StringIO(plistlib.writePlistToString(self.good_env))
        self.processor = FileFinder(infile=self.input_plist)

    def tearDown(self):
        self.input_plist.close()

    def test_raise_if_not_glob(self):
        """Raise an exception if glob is not passed to find_method."""
        self.processor.env = self.bad_env
        with self.assertRaises(ProcessorError):
            self.processor.main()

    @mock.patch("autopkglib.FileFinder.globfind")
    def test_no_fail_if_good_env(self, mock_glob):
        """The processor should not raise any exceptions if run normally."""
        self.processor.env = self.good_env
        mock_glob.return_value = "test"
        self.processor.main()

    @mock.patch("autopkglib.FileFinder.globfind")
    def test_found_a_match(self, mock_glob):
        """If we find a match, it should be in the env."""
        self.processor.env = self.good_env
        mock_glob.return_value = "test"
        self.processor.main()
        self.assertEqual(self.processor.env["found_filename"], "test")

    @mock.patch("autopkglib.FileFinder.unmount")
    @mock.patch("autopkglib.FileFinder.mount")
    @mock.patch("autopkglib.FileFinder.globfind")
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
