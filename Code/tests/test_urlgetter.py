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

    def test_prepare_curl_cmd_includes_compressed_by_default(self):
        """prepare_curl_cmd includes --compressed outside Windows system curl."""
        with (
            patch("autopkglib.URLGetter.is_windows", return_value=False),
            patch.object(self.processor, "curl_binary", return_value="/usr/bin/curl"),
        ):
            self.assertEqual(
                self.processor.prepare_curl_cmd(),
                ["/usr/bin/curl", "--compressed", "--location"],
            )

    def test_prepare_curl_cmd_omits_compressed_for_windows_system_curl(self):
        """prepare_curl_cmd omits --compressed for Windows system curl."""
        with (
            patch("autopkglib.URLGetter.is_windows", return_value=True),
            patch.object(
                self.processor,
                "curl_binary",
                return_value=r"C:\Windows\System32\curl.exe",
            ),
        ):
            self.assertEqual(
                self.processor.prepare_curl_cmd(),
                [r"C:\Windows\System32\curl.exe", "--location"],
            )

    def test_add_curl_headers_appends_header_options(self):
        """add_curl_headers appends curl header flags for a header dict."""
        curl_cmd = ["curl"]

        self.processor.add_curl_headers(
            curl_cmd, {"Accept": "application/json", "User-Agent": "AutoPkg"}
        )

        self.assertEqual(
            curl_cmd,
            [
                "curl",
                "--header",
                "Accept: application/json",
                "--header",
                "User-Agent: AutoPkg",
            ],
        )

    def test_add_curl_headers_ignores_empty_headers(self):
        """add_curl_headers leaves curl_cmd unchanged for empty headers."""
        curl_cmd = ["curl"]

        self.processor.add_curl_headers(curl_cmd, {})
        self.processor.add_curl_headers(curl_cmd, None)

        self.assertEqual(curl_cmd, ["curl"])

    def test_add_curl_common_opts_appends_headers_and_options(self):
        """add_curl_common_opts appends request_headers and curl_opts."""
        curl_cmd = ["curl"]
        self.processor.env = {
            "request_headers": {"Accept": "application/xml"},
            "curl_opts": ["--fail", "--silent"],
        }

        self.processor.add_curl_common_opts(curl_cmd)

        self.assertEqual(
            curl_cmd,
            [
                "curl",
                "--header",
                "Accept: application/xml",
                "--fail",
                "--silent",
            ],
        )

    def test_clear_header_resets_fields_and_preserves_redirect(self):
        """clear_header resets header state and preserves http_redirected."""
        header = {
            "content-length": "123",
            "http_result_code": "200",
            "http_redirected": "https://example.com/redirect",
        }

        self.processor.clear_header(header)

        self.assertEqual(
            header,
            {
                "http_result_code": "000",
                "http_result_description": "",
                "http_redirected": "https://example.com/redirect",
            },
        )

    def test_parse_http_protocol_splits_result_code_and_description(self):
        """parse_http_protocol stores status code and description."""
        header = {}

        self.processor.parse_http_protocol("HTTP/2 200 OK", header)

        self.assertEqual(header["http_result_code"], "200")
        self.assertEqual(header["http_result_description"], "OK")

    def test_parse_http_protocol_ignores_short_line(self):
        """parse_http_protocol leaves header unchanged for a short line."""
        header = {"http_result_code": "000"}

        self.processor.parse_http_protocol("HTTP/2", header)

        self.assertEqual(header, {"http_result_code": "000"})

    def test_parse_http_header_with_value(self):
        """parse_http_header stores a lower-cased field name and value."""
        header = {}

        self.processor.parse_http_header("Content-Type: text/html", header)

        self.assertEqual(header, {"content-type": "text/html"})

    def test_parse_http_header_without_value(self):
        """parse_http_header stores an empty value for a header-only line."""
        header = {}

        self.processor.parse_http_header("ETag:", header)

        self.assertEqual(header, {"etag": ""})

    def test_parse_curl_error_returns_message(self):
        """parse_curl_error strips the curl prefix and error code."""
        self.assertEqual(
            self.processor.parse_curl_error("curl: (6) Could not resolve host\n"),
            "Could not resolve host",
        )

    def test_parse_curl_error_returns_raw_stderr_when_unparseable(self):
        """parse_curl_error returns raw stderr when it cannot parse a message."""
        self.assertEqual(self.processor.parse_curl_error("curl:"), "curl:")

    def test_parse_ftp_header_sets_content_length_for_size_response(self):
        """parse_ftp_header maps FTP SIZE responses to content-length."""
        header = {}

        self.processor.parse_ftp_header("213 12345", header)

        self.assertEqual(header, {"content-length": "12345"})

    def test_parse_ftp_header_maps_55x_responses_to_404(self):
        """parse_ftp_header maps 55x errors to a 404-like result."""
        header = {}

        self.processor.parse_ftp_header("550 File unavailable", header)

        self.assertEqual(header["http_result_code"], "404")
        self.assertEqual(header["http_result_description"], "550 File unavailable")

    def test_parse_ftp_header_maps_transfer_responses_to_200(self):
        """parse_ftp_header maps 125 and 150 responses to success."""
        for line in ("125 Data connection already open", "150 Opening data"):
            with self.subTest(line=line):
                header = {}

                self.processor.parse_ftp_header(line, header)

                self.assertEqual(header["http_result_code"], "200")
                self.assertEqual(header["http_result_description"], line)

    def test_parse_ftp_header_ignores_other_responses(self):
        """parse_ftp_header leaves unrelated response codes unchanged."""
        header = {"http_result_code": "000"}

        self.processor.parse_ftp_header("220 Service ready", header)

        self.assertEqual(header, {"http_result_code": "000"})


if __name__ == "__main__":
    unittest.main()
