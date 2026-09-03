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

import email.message
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from autopkglib.URLDownloaderPython import URLDownloaderPython

# autopkglib re-exports the class under the module's own name, so patch the
# module object directly rather than by dotted path.
URLDOWNLOADERPYTHON = sys.modules[URLDownloaderPython.__module__]


def build_response(payload, headers):
    """Return a stand-in for the object urlopen() hands back."""
    message = email.message.Message()
    for key, value in headers.items():
        message[key] = value

    class FakeResponse:
        """Minimal urlopen() response exposing read() and headers."""

        def __init__(self):
            self._chunks = [payload, b""]

        def read(self, _size=None):
            return self._chunks.pop(0)

        @property
        def headers(self):
            return message

        def info(self):
            return message

    return FakeResponse()


class TestURLDownloaderPython(unittest.TestCase):
    """Test class for URLDownloaderPython Processor."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.payload = b"downloaded package contents"
        self.processor = URLDownloaderPython()
        self.processor.env = {
            "url": "http://example.com/file.pkg",
            "filename": "file.pkg",
            "RECIPE_CACHE_DIR": self.temp_dir,
            "download_dir": self.temp_dir,
            "pathname": os.path.join(self.temp_dir, "file.pkg"),
        }

    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def download(self, headers):
        """Run download_and_hash() against a response with the given headers."""
        temp_file = os.path.join(self.temp_dir, "tempfile")
        with patch.object(URLDOWNLOADERPYTHON, "urlopen") as mock_urlopen, patch.object(
            self.processor, "download_changed", return_value=True
        ), patch.object(self.processor, "store_headers"), patch.object(
            self.processor, "move_temp_file"
        ) as mock_move:
            mock_urlopen.return_value = build_response(self.payload, headers)
            result = self.processor.download_and_hash(temp_file)
        return result, mock_move

    def test_download_moved_into_place_with_all_headers(self):
        """A response carrying every validator is moved into place and recorded."""
        result, mock_move = self.download(
            {
                "Content-Length": str(len(self.payload)),
                "ETag": 'W/"abc123"',
                "Last-Modified": "Tue, 21 Jul 2026 09:11:48 GMT",
            }
        )

        mock_move.assert_called_once()
        self.assertIsNotNone(result)
        self.assertEqual(
            result["http_headers"],
            {
                "Content-Length": len(self.payload),
                "ETag": 'W/"abc123"',
                "Last-Modified": "Tue, 21 Jul 2026 09:11:48 GMT",
            },
        )

    def test_download_moved_into_place_without_content_length(self):
        """A chunked response has no Content-Length, but the download still lands.

        Regression test: the missing header used to raise TypeError and return
        early, abandoning a complete download in its temp file while leaving a
        stale artefact at pathname.
        """
        result, mock_move = self.download(
            {
                "ETag": 'W/"abc123"',
                "Last-Modified": "Tue, 21 Jul 2026 09:11:48 GMT",
                "Transfer-Encoding": "chunked",
            }
        )

        mock_move.assert_called_once()
        self.assertIsNotNone(result)
        self.assertNotIn("Content-Length", result["http_headers"])
        self.assertEqual(result["http_headers"]["ETag"], 'W/"abc123"')
        self.assertEqual(result["file_size"], len(self.payload))

    def test_download_moved_into_place_without_any_validators(self):
        """A response with no cache validators at all still lands the download."""
        result, mock_move = self.download({})

        mock_move.assert_called_once()
        self.assertIsNotNone(result)
        self.assertEqual(result["http_headers"], {})


if __name__ == "__main__":
    unittest.main()
