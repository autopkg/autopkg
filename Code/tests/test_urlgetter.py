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

import subprocess
import unittest
from unittest.mock import patch

from autopkglib import ProcessorError
from autopkglib.URLGetter import URLGetter


class TestURLGetter(unittest.TestCase):
    """Test class for URLGetter Processor."""

    def setUp(self):
        self.processor = URLGetter()

    def test_execute_curl_reports_text_stderr(self):
        """execute_curl raises ProcessorError with text stderr."""
        curl_error = subprocess.CalledProcessError(
            6,
            ["curl", "https://example.invalid"],
            stderr="curl: Could not resolve host\n",
        )

        with (
            patch("subprocess.run", side_effect=curl_error),
            patch.object(self.processor, "output") as mock_output,
            self.assertRaisesRegex(ProcessorError, "curl: Could not resolve host"),
        ):
            self.processor.execute_curl(["curl", "https://example.invalid"])

        mock_output.assert_called_once_with("ERROR: Could not resolve host\n")

    def test_execute_curl_reports_bytes_stderr(self):
        """execute_curl raises ProcessorError with decoded bytes stderr."""
        curl_error = subprocess.CalledProcessError(
            6,
            ["curl", "https://example.invalid"],
            stderr=b"curl: Could not resolve host \xff\n",
        )

        with (
            patch("subprocess.run", side_effect=curl_error),
            patch.object(self.processor, "output") as mock_output,
            self.assertRaisesRegex(ProcessorError, "curl: Could not resolve host .\n"),
        ):
            self.processor.execute_curl(["curl", "https://example.invalid"], text=False)

        mock_output.assert_called_once_with("ERROR: Could not resolve host \ufffd\n")

    def test_execute_curl_reports_missing_stderr(self):
        """execute_curl raises ProcessorError when stderr is missing."""
        curl_error = subprocess.CalledProcessError(
            1, ["curl", "https://example.invalid"], stderr=None
        )

        with (
            patch("subprocess.run", side_effect=curl_error),
            patch.object(self.processor, "output") as mock_output,
            self.assertRaisesRegex(
                ProcessorError, "curl failed without diagnostic output"
            ),
        ):
            self.processor.execute_curl(["curl", "https://example.invalid"])

        mock_output.assert_called_once_with(
            "ERROR: curl failed without diagnostic output"
        )


if __name__ == "__main__":
    unittest.main()
