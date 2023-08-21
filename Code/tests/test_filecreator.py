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
from unittest.mock import mock_open, patch

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

    @patch("builtins.open", new_callable=mock_open, read_data="Hello world")
    @patch("autopkglib.FileCreator")
    def test_file_content(self, mock_load, mock_file):
        """The file created by the processor should have the expected contents."""
        self.processor.env = self.good_env
        self.processor.main()
        with open(mock_file, "rb") as openfile:
            result = openfile.read()
        self.assertEqual(self.processor.env["file_content"], result)


if __name__ == "__main__":
    unittest.main()
