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

import plistlib
import unittest
from unittest.mock import MagicMock, patch

from autopkglib import ProcessorError
from autopkglib.MunkiInfoCreator import MunkiInfoCreator


class TestMunkiInfoCreator(unittest.TestCase):
    """Test class for MunkiInfoCreator Processor."""

    def setUp(self):
        self.processor = MunkiInfoCreator()
        # A dmg path avoids the pkg-to-temp-directory copy in main().
        self.processor.env = {"pkg_path": "/munki/repo/pkgs/Test.dmg"}

    def _mock_makepkginfo(self, stdout, stderr=b"", returncode=0):
        """Patch subprocess.Popen so makepkginfo returns canned output."""
        proc = MagicMock()
        proc.communicate.return_value = (stdout, stderr)
        proc.returncode = returncode
        return patch("subprocess.Popen", return_value=proc)

    def test_valid_output_is_parsed(self):
        """A well-formed pkginfo plist should populate munki_info."""
        pkginfo = plistlib.dumps({"name": "Test", "version": "1.0"})

        with self._mock_makepkginfo(pkginfo):
            with patch.object(self.processor, "output"):
                self.processor.main()

        self.assertEqual(self.processor.env["munki_info"]["name"], "Test")

    def test_unparseable_output_raises_processor_error(self):
        """Malformed makepkginfo output should raise ProcessorError."""
        with self._mock_makepkginfo(b"not a plist at all"):
            with patch.object(self.processor, "output"):
                with self.assertRaisesRegex(
                    ProcessorError, "could not be parsed as a plist"
                ):
                    self.processor.main()

    def test_failure_with_undecodable_stderr(self):
        """Non-UTF-8 stderr should still produce a readable ProcessorError."""
        with self._mock_makepkginfo(b"", stderr=b"bad \xff byte", returncode=1):
            with patch.object(self.processor, "output"):
                with self.assertRaisesRegex(ProcessorError, "failed:"):
                    self.processor.main()


if __name__ == "__main__":
    unittest.main()
