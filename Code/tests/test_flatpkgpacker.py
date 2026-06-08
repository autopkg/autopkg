#!/usr/local/autopkg/python
#
# Copyright 2026 Elliot Jordan
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

import sys
import unittest
from unittest.mock import patch

from autopkglib import ProcessorError
from autopkglib.FlatPkgPacker import FlatPkgPacker


@unittest.skipUnless(sys.platform == "darwin", "Requires macOS")
class TestFlatPkgPacker(unittest.TestCase):
    def test_flatten_wraps_launch_error(self):
        processor = FlatPkgPacker()

        with patch("subprocess.check_call", side_effect=OSError(2, "missing")):
            with self.assertRaisesRegex(ProcessorError, "pkgutil execution failed"):
                processor.flatten("/path/to/source", "/path/to/dest.pkg")


if __name__ == "__main__":
    unittest.main()
