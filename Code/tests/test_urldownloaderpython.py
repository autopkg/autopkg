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
import ssl
import tempfile
import unittest
from hashlib import md5, sha1, sha256
from unittest.mock import patch

from autopkglib import ProcessorError
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
    def __init__(self, body, headers, url=None):
        self.body = io.BytesIO(body)
        self.headers = CaseInsensitiveHeaders(headers)
        self.url = url

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

    def test_store_hashes_in_env_sets_env_vars(self):
        self.processor.env = {}

        self.processor.store_hashes_in_env(
            {"sha1": "abc123", "sha256": "def456", "md5": "ghi789"}
        )

        self.assertEqual(self.processor.env["file_sha1"], "abc123")
        self.assertEqual(self.processor.env["file_sha256"], "def456")
        self.assertEqual(self.processor.env["file_md5"], "ghi789")

    def test_ssl_context_certifi_uses_certifi_ca_bundle(self):
        with patch.object(
            URLDOWNLOADERPYTHON_MODULE.os.environ, "get", return_value=None
        ):
            context = self.processor.ssl_context_certifi()

        self.assertIsInstance(context, ssl.SSLContext)

    def test_ssl_context_certifi_missing_custom_cert_raises(self):
        with (
            patch.dict(os.environ, {"SSL_CERT_FILE": "/nonexistent/cert.pem"}),
            patch.object(
                URLDOWNLOADERPYTHON_MODULE.os.path, "isfile", return_value=False
            ),
        ):
            with self.assertRaisesRegex(ProcessorError, "does not exist"):
                self.processor.ssl_context_certifi()

    def test_ssl_context_certifi_unreadable_cert_raises(self):
        with (
            patch.dict(os.environ, {"SSL_CERT_FILE": "/some/cert.pem"}),
            patch.object(
                URLDOWNLOADERPYTHON_MODULE.os.path, "isfile", return_value=True
            ),
            patch.object(URLDOWNLOADERPYTHON_MODULE.os, "access", return_value=False),
        ):
            with self.assertRaisesRegex(ProcessorError, "not readable"):
                self.processor.ssl_context_certifi()

    def test_store_download_info_json_writes_valid_json(self):
        download_info = {
            "download_url": "https://example.com/download.bin",
            "file_name": "download.bin",
            "file_size": 12,
            "http_headers": {"ETag": "test-tag"},
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            pathname = os.path.join(temp_dir, "download.bin")
            self.processor.env["pathname"] = pathname

            self.processor.store_download_info_json(download_info)

            info_path = pathname + ".info.json"
            self.assertTrue(os.path.exists(info_path))
            with open(info_path, encoding="utf-8") as infile:
                contents = infile.read()
            self.assertIn("\n    ", contents)
            self.assertEqual(json.loads(contents), download_info)

    def test_get_download_info_json_returns_parsed_dict(self):
        expected_info = {
            "download_url": "https://example.com/download.bin",
            "file_name": "download.bin",
            "file_size": 12,
            "http_headers": {"ETag": "test-tag"},
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            pathname = os.path.join(temp_dir, "download.bin")
            with open(pathname + ".info.json", "w", encoding="utf-8") as outfile:
                json.dump(expected_info, outfile)
            self.processor.env["pathname"] = pathname

            download_info = self.processor.get_download_info_json()

        self.assertEqual(download_info, expected_info)

    def test_get_download_info_json_missing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.processor.env["pathname"] = os.path.join(temp_dir, "download.bin")

            with patch.object(self.processor, "output") as mock_output:
                download_info = self.processor.get_download_info_json()

        self.assertIsNone(download_info)
        mock_output.assert_called_once()
        self.assertIn("WARNING: missing download info", mock_output.call_args.args[0])

    def test_download_changed_returns_true_when_file_missing(self):
        self.processor.env["pathname"] = os.path.join(
            self.temp_dir.name, "missing-download.bin"
        )

        changed = self.processor.download_changed(
            CaseInsensitiveHeaders({"Content-Length": "10"})
        )

        self.assertTrue(changed)

    def test_download_changed_content_length_mismatch_returns_true(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pathname = os.path.join(temp_dir, "download.bin")
            with open(pathname, "wb") as outfile:
                outfile.write(b"x" * 100)
            self.processor.env["pathname"] = pathname

            changed = self.processor.download_changed(
                CaseInsensitiveHeaders({"Content-Length": "200"})
            )

        self.assertTrue(changed)

    def test_download_changed_etag_mismatch_returns_true(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pathname = os.path.join(temp_dir, "download.bin")
            with open(pathname, "wb") as outfile:
                outfile.write(b"test data")
            with open(pathname + ".info.json", "w", encoding="utf-8") as outfile:
                json.dump({"http_headers": {"ETag": "cached-tag"}}, outfile)
            self.processor.env["pathname"] = pathname
            self.processor.env["HEADERS_TO_TEST"] = ["ETag"]

            changed = self.processor.download_changed(
                CaseInsensitiveHeaders({"ETag": "response-tag"})
            )

        self.assertTrue(changed)

    def test_download_changed_missing_content_length_header_warns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pathname = os.path.join(temp_dir, "download.bin")
            with open(pathname, "wb") as outfile:
                outfile.write(b"test data")
            self.processor.env["pathname"] = pathname
            self.processor.env["HEADERS_TO_TEST"] = ["Content-Length"]

            with patch.object(self.processor, "output") as mock_output:
                self.processor.download_changed(CaseInsensitiveHeaders({"ETag": "tag"}))

        self.assertTrue(
            any(
                "Content-Length' missing" in call.args[0]
                for call in mock_output.call_args_list
            )
        )

    def test_download_and_hash_computes_hashes_when_enabled(self):
        body = b"hash this content"
        response = FakeHTTPResponse(body, {"Content-Length": str(len(body))})
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = os.path.join(temp_dir, "temporary-download")
            pathname = os.path.join(temp_dir, "download.bin")
            self.processor.env["pathname"] = pathname
            self.processor.env["COMPUTE_HASHES"] = True

            with (
                patch.object(
                    URLDOWNLOADERPYTHON_MODULE, "urlopen", return_value=response
                ),
                patch.object(self.processor, "ssl_context_certifi", return_value=None),
                patch.object(self.processor, "store_headers"),
            ):
                download_info = self.processor.download_and_hash(temp_path)

        self.assertEqual(download_info["file_sha1"], sha1(body).hexdigest())
        self.assertEqual(download_info["file_sha256"], sha256(body).hexdigest())
        self.assertEqual(download_info["file_md5"], md5(body).hexdigest())

    def test_download_and_hash_handles_invalid_request_headers_type(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.processor.env["pathname"] = os.path.join(temp_dir, "download.bin")
            self.processor.env["request_headers"] = "not-a-dict"
            temp_path = os.path.join(temp_dir, "temporary-download")

            with self.assertRaisesRegex(ProcessorError, "must be a dictionary"):
                self.processor.download_and_hash(temp_path)

    def test_download_and_hash_normalizes_header_keys_to_string(self):
        body = b"header string data"
        response = FakeHTTPResponse(body, {"Content-Length": str(len(body))})
        captured_request = None

        def fake_urlopen(request_obj, context=None):
            nonlocal captured_request
            captured_request = request_obj
            return response

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = os.path.join(temp_dir, "temporary-download")
            self.processor.env["pathname"] = os.path.join(temp_dir, "download.bin")
            self.processor.env["request_headers"] = {123: 456}

            with (
                patch.object(
                    URLDOWNLOADERPYTHON_MODULE, "urlopen", side_effect=fake_urlopen
                ),
                patch.object(self.processor, "ssl_context_certifi", return_value=None),
                patch.object(self.processor, "store_headers"),
            ):
                self.processor.download_and_hash(temp_path)

        self.assertEqual(captured_request.headers["123"], "456")

    def test_download_and_hash_skips_none_header_values(self):
        body = b"header none data"
        response = FakeHTTPResponse(body, {"Content-Length": str(len(body))})
        captured_request = None

        def fake_urlopen(request_obj, context=None):
            nonlocal captured_request
            captured_request = request_obj
            return response

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = os.path.join(temp_dir, "temporary-download")
            self.processor.env["pathname"] = os.path.join(temp_dir, "download.bin")
            self.processor.env["request_headers"] = {
                "Header1": "value",
                "Header2": None,
            }

            with (
                patch.object(
                    URLDOWNLOADERPYTHON_MODULE, "urlopen", side_effect=fake_urlopen
                ),
                patch.object(self.processor, "ssl_context_certifi", return_value=None),
                patch.object(self.processor, "store_headers"),
            ):
                self.processor.download_and_hash(temp_path)

        self.assertEqual(captured_request.headers["Header1"], "value")
        self.assertNotIn("Header2", captured_request.headers)

    def test_main_raises_when_download_metadata_missing_on_changed(self):
        self.processor.env["download_changed"] = True

        with patch.object(self.processor, "download_and_hash", return_value=None):
            with self.assertRaisesRegex(ProcessorError, "metadata"):
                self.processor.main()


if __name__ == "__main__":
    unittest.main()
