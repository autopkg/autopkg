#!/usr/local/autopkg/python
#
# Copyright 2024 Elliot Jordan
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
import sys
import unittest
from unittest.mock import patch

from autopkglib.FileMover import FileMover

_FileMover_mod = sys.modules[FileMover.__module__]


class TestFileMover(unittest.TestCase):
    """Test class for FileMover Processor."""

    def setUp(self):
        self.good_env = {
            "source": "/path/to/source",
            "target": "/path/to/target",
        }
        self.input_plist = plistlib.dumps(self.good_env)
        self.processor = FileMover(infile=self.input_plist)
        self.processor.env = self.good_env.copy()

    def test_main_moves_file_and_outputs_message(self):
        """Test that main() renames source to target and outputs the correct message."""
        with patch.object(_FileMover_mod, "rename") as mock_rename, patch.object(
            self.processor, "output"
        ) as mock_output:
            self.processor.main()

        mock_rename.assert_called_once_with("/path/to/source", "/path/to/target")
        mock_output.assert_called_once()
        message = mock_output.call_args[0][0]
        self.assertIn("/path/to/source", message)
        self.assertIn("/path/to/target", message)

    def test_main_handles_rename_error(self):
        """Test that main() propagates OSError from os.rename()."""
        with patch.object(
            _FileMover_mod, "rename", side_effect=OSError("Permission denied")
        ):
            with self.assertRaises(OSError) as ctx:
                self.processor.main()
        self.assertIn("Permission denied", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
