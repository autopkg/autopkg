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

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Load packager module directly from file to avoid mocking issues
autopkgserver_path = Path(__file__).parent.parent / "autopkgserver" / "packager.py"
spec = importlib.util.spec_from_file_location("packager", autopkgserver_path)
packager_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager_module)
Packager = packager_module.Packager


class TestPackager(unittest.TestCase):
    """Test class for Packager."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a minimal Packager instance for testing
        self.mock_log = MagicMock()
        self.mock_request = {}
        self.packager = Packager(
            log=self.mock_log,
            request=self.mock_request,
            name="test",
            uid=501,
            gid=20,
        )

    def test_random_string_contains_only_hex_chars(self):
        """Should only contain valid hex characters (0-9, a-f)."""
        result = self.packager.random_string(16)
        self.assertRegex(
            result,
            r"^[0-9a-f]+$",
            f"random_string returned invalid hex characters: {result}",
        )

    def test_random_string_returns_correct_length(self):
        """Should return string of requested length."""
        for length in [8, 16, 32]:
            result = self.packager.random_string(length)
            self.assertEqual(
                len(result),
                length,
                f"Expected length {length}, got {len(result)}: {result}",
            )


if __name__ == "__main__":
    unittest.main()
