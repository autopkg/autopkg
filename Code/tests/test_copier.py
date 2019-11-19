#!/usr/local/autopkg/python

import plistlib
import unittest
from unittest.mock import patch

from autopkglib import ProcessorError
from autopkglib.Copier import Copier


class TestCopier(unittest.TestCase):
    """Test class for FileFinder Processor."""

    def setUp(self):
        self.good_env = {
            "source_path": "source",
            "destination_path": "dest",
            "overwrite": True,
        }
        self.glob_env = {
            "source_path": "dir/source*",
            "destination_path": "dest",
            "overwrite": True,
        }
        self.dmg_env = {
            "source_path": "mydmg.dmg/source",
            "destination_path": "dest",
            "overwrite": True,
        }
        self.dmg_glob_env = {
            "source_path": "mydmg.dmg/source*",
            "destination_path": "dest",
            "overwrite": True,
        }
        self.bad_env = {"source_path": "source"}
        self.input_plist = plistlib.dumps(self.good_env)
        self.processor = Copier(infile=self.input_plist)

    def tearDown(self):
        pass

    def test_raise_if_no_dest(self):
        """Raise an exception if missing a critical input variable."""
        self.processor.env = self.bad_env
        with self.assertRaises(ProcessorError):
            self.processor.main()

    @patch("autopkglib.glob.glob")
    @patch("autopkglib.Copier.copy")
    def test_no_fail_if_good_env(self, mock_copy, mock_glob):
        """The processor should not raise any exceptions if run normally."""
        self.processor.env = self.good_env
        mock_glob.return_value = ["source"]
        mock_copy.return_value = True
        self.processor.main()
        mock_copy.assert_called_once()

    @patch("autopkglib.glob.glob")
    @patch("autopkglib.Copier.copy")
    def test_no_fail_if_glob_env(self, mock_copy, mock_glob):
        """The processor should not raise any exceptions if run with a glob."""
        self.processor.env = self.glob_env
        mock_glob.return_value = ["source"]
        mock_copy.return_value = True
        self.processor.main()
        mock_copy.assert_called_once()

    @patch("autopkglib.Copier.unmount")
    @patch("autopkglib.Copier.mount")
    @patch("autopkglib.glob.glob")
    @patch("autopkglib.Copier.copy")
    def test_no_fail_if_dmg_env(self, mock_copy, mock_glob, mock_mount, mock_unmount):
        """The processor should not raise any exceptions if run with a DMG."""
        self.processor.env = self.dmg_env
        mock_glob.return_value = ["source"]
        mock_copy.return_value = True
        mock_mount.return_value = "/fake/mount"
        self.processor.main()
        mock_copy.assert_called_once()
        mock_unmount.assert_called_once()

    @patch("autopkglib.Copier.unmount")
    @patch("autopkglib.Copier.mount")
    @patch("autopkglib.glob.glob")
    @patch("autopkglib.Copier.copy")
    def test_no_fail_if_dmg_glob_env(
        self, mock_copy, mock_glob, mock_mount, mock_unmount
    ):
        """The processor should not raise any exceptions if run with a DMG and glob."""
        self.processor.env = self.dmg_glob_env
        mock_glob.return_value = ["source"]
        mock_copy.return_value = True
        mock_mount.return_value = "/fake/mount"
        self.processor.main()
        mock_copy.assert_called_once()
        mock_unmount.assert_called_once()

    @patch("autopkglib.glob.glob")
    @patch("autopkglib.Copier.copy")
    def test_multiple_matches(self, mock_copy, mock_glob):
        """The processor should not raise any exceptions if run with a glob."""
        self.processor.env = self.glob_env
        mock_glob.return_value = ["source1", "source2"]
        mock_copy.return_value = True
        self.processor.main()
        mock_copy.assert_called_once_with(
            "source1", self.glob_env["destination_path"], overwrite=True
        )


if __name__ == "__main__":
    unittest.main()
