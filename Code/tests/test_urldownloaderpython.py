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

import io
import json
import os
import tempfile
import unittest
from hashlib import md5, sha1, sha256
from unittest.mock import patch

from autopkglib.URLDownloaderPython import URLDownloaderPython
from tests import get_processor_module

URLDOWNLOADERPYTHON_MODULE = get_processor_module("URLDownloaderPython")


class CaseInsensitiveHeaders:
    def __init__(self, headers):
        self.headers = {
            str(key).lower(): (str(key), str(value)) for key, value in headers.items()
        }

    def get(self, key, default=None):
        return self.headers.get(str(key).lower(), (None, default))[1]

    def __getitem__(self, key):
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __str__(self):
        return str({name: value for name, value in self.headers.values()})


class FakeHTTPResponse:
    def __init__(self, body, headers):
        self.body = io.BytesIO(body)
        self.headers = CaseInsensitiveHeaders(headers)

    def info(self):
        return self.headers

    def read(self, size=-1):
        return self.body.read(size)


class TestURLDownloaderPython(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.processor = URLDownloaderPython()
        self.processor.env = {
            "url": "https://example.com/download.bin",
            "RECIPE_CACHE_DIR": self.temp_dir.name,
            "CHECK_FILESIZE_ONLY": False,
            "HEADERS_TO_TEST": ["ETag", "Last-Modified", "Content-Length"],
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_download(self, body, headers):
        response = FakeHTTPResponse(body, headers)
        with (
            patch.object(URLDOWNLOADERPYTHON_MODULE, "urlopen", return_value=response),
            patch.object(self.processor, "store_headers"),
        ):
            self.processor.main()

    def test_size_only_check_uses_real_cached_file_size(self):
        cached_path = os.path.join(self.temp_dir.name, "cached.bin")
        with open(cached_path, "wb") as outfile:
            outfile.write(b"short")
        with open(cached_path + ".info.json", "w", encoding="utf-8") as outfile:
            json.dump(
                {
                    "file_size": 100,
                    "http_headers": {"Content-Length": 100},
                },
                outfile,
            )

        self.processor.env["pathname"] = cached_path
        self.processor.env["HEADERS_TO_TEST"] = ["Content-Length"]

        changed = self.processor.download_changed(
            CaseInsensitiveHeaders({"Content-Length": "100"})
        )

        self.assertTrue(changed)

    def test_fresh_download_populates_hash_outputs(self):
        body = b"fresh download content"
        self.processor.env["COMPUTE_HASHES"] = True

        self.run_download(
            body,
            {
                "Content-Length": str(len(body)),
                "ETag": '"fresh"',
                "Last-Modified": "Mon, 01 Jan 2024 00:00:00 GMT",
            },
        )

        self.assertEqual(self.processor.env["file_sha1"], sha1(body).hexdigest())
        self.assertEqual(self.processor.env["file_sha256"], sha256(body).hexdigest())
        self.assertEqual(self.processor.env["file_md5"], md5(body).hexdigest())
        self.assertIn("file_sha1", self.processor.output_variables)
        self.assertIn("file_sha256", self.processor.output_variables)
        self.assertIn("file_md5", self.processor.output_variables)

        info_path = self.processor.env["pathname"] + ".info.json"
        with open(info_path, encoding="utf-8") as infile:
            metadata = json.load(infile)
        self.assertEqual(metadata["file_sha256"], sha256(body).hexdigest())

    def test_cache_hit_populates_hash_outputs(self):
        cached_body = b"cached download content"
        download_dir = os.path.join(self.temp_dir.name, "downloads")
        os.makedirs(download_dir)
        cached_path = os.path.join(download_dir, "download.bin")
        with open(cached_path, "wb") as outfile:
            outfile.write(cached_body)
        with open(cached_path + ".info.json", "w", encoding="utf-8") as outfile:
            json.dump(
                {
                    "file_size": len(cached_body),
                    "http_headers": {"Content-Length": len(cached_body)},
                },
                outfile,
            )

        self.processor.env["CHECK_FILESIZE_ONLY"] = True
        self.processor.env["COMPUTE_HASHES"] = True

        self.run_download(
            b"ignored response body",
            {"Content-Length": str(len(cached_body))},
        )

        self.assertFalse(self.processor.env["download_changed"])
        self.assertEqual(self.processor.env["file_sha1"], sha1(cached_body).hexdigest())
        self.assertEqual(
            self.processor.env["file_sha256"], sha256(cached_body).hexdigest()
        )
        self.assertEqual(self.processor.env["file_md5"], md5(cached_body).hexdigest())
        with open(cached_path, "rb") as infile:
            self.assertEqual(infile.read(), cached_body)

    def test_missing_validator_headers_preserve_download(self):
        body = b"download without validators"

        self.run_download(body, {"Content-Length": str(len(body))})

        self.assertTrue(os.path.exists(self.processor.env["pathname"]))
        with open(self.processor.env["pathname"], "rb") as infile:
            self.assertEqual(infile.read(), body)

        info_path = self.processor.env["pathname"] + ".info.json"
        with open(info_path, encoding="utf-8") as infile:
            metadata = json.load(infile)
        self.assertEqual(metadata["http_headers"]["ETag"], "")
        self.assertEqual(metadata["http_headers"]["Last-Modified"], "")


if __name__ == "__main__":
    unittest.main()
