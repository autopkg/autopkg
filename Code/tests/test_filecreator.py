#!/local/autopkg/python

import os
import plistlib
import unittest
from unittest.mock import patch

from autopkglib.FileCreator import FileCreator


class TestFileCreator(unittest.TestCase):
    """Test class for FileCreator Processor."""

    def setUp(self):
        self.good_env = {"file_content": "Hello world", "file_path": "testfile"}
        self.bad_env = {"file_path": ""}
        self.input_plist = plistlib.dumps(self.good_env)
        self.processor = FileCreator(infile=self.input_plist)

    def tearDown(self):
        pass

    @patch("autopkglib.FileCreator")
    def test_no_fail_if_good_env(self, _):
        """The processor should not raise any exceptions if run normally."""
        self.processor.env = self.good_env
        self.processor.main()
        with open(self.processor.env["file_path"], "r") as openfile:
            test_content = openfile.read()
        self.assertEqual(self.processor.env["file_content"], test_content)
        os.remove(self.processor.env["file_path"])


if __name__ == "__main__":
    unittest.main()
