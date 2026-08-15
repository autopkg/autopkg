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
from email.message import Message
from hashlib import md5, sha1, sha256
from unittest.mock import patch

from autopkglib import ProcessorError
from autopkglib.URLDownloaderPython import URLDownloaderPython
from tests import get_processor_module

URLDOWNLOADERPYTHON_MODULE = get_processor_module("URLDownloaderPython")


def case_insensitive_headers(headers):
    message = Message()
    for name, value in headers.items():
        message[name] = str(value)
    return message


class FakeHTTPResponse:
    def __init__(self, body, headers, url=None):
        self.body = io.BytesIO(body)
        self.headers = case_insensitive_headers(headers)
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
            case_insensitive_headers({"Content-Length": "100"})
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
        self.assertEqual(self.processor.env["download_info"], metadata)

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

    def _write_info_json(self, extra=None):
        """Create downloads/download.bin.info.json with matching size, no file."""
        download_dir = os.path.join(self.temp_dir.name, "downloads")
        os.makedirs(download_dir, exist_ok=True)
        pathname = os.path.join(download_dir, "download.bin")
        metadata = {"file_size": 4, "http_headers": {"Content-Length": 4}}
        if extra:
            metadata.update(extra)
        with open(pathname + ".info.json", "w", encoding="utf-8") as outfile:
            json.dump(metadata, outfile)
        return pathname

    def test_missing_file_rematerializes_without_marking_changed(self):
        """Missing file + unchanged version + download_missing_file default:
        re-fetch the file but keep download_changed False."""
        pathname = self._write_info_json()
        self.processor.env["CHECK_FILESIZE_ONLY"] = True

        with patch.object(self.processor, "output") as mock_output:
            self.run_download(b"data", {"Content-Length": "4"})

        self.assertFalse(self.processor.env["download_changed"])
        self.assertTrue(os.path.isfile(pathname))
        with open(pathname, "rb") as infile:
            self.assertEqual(infile.read(), b"data")
        with open(pathname + ".info.json", encoding="utf-8") as infile:
            metadata = json.load(infile)
        self.assertEqual(metadata["download_url"], self.processor.env["url"])
        self.assertIn("url_downloader_summary_result", self.processor.env)
        self.assertTrue(
            any(
                "Re-downloaded missing file" in call.args[0]
                for call in mock_output.call_args_list
            )
        )

    def test_headers_to_test_does_not_leak_from_size_only_check(self):
        self.processor.env["CHECK_FILESIZE_ONLY"] = True
        self.processor.env["HEADERS_TO_TEST"] = ["ETag"]

        self.run_download(b"data", {"Content-Length": "4"})

        self.assertEqual(self.processor.env["HEADERS_TO_TEST"], ["ETag"])

    def test_custom_header_is_stored_for_next_run(self):
        self.processor.env["HEADERS_TO_TEST"] = ["X-Release"]

        self.run_download(b"data", {"Content-Length": "4", "X-Release": "2026.08"})

        with open(
            self.processor.env["pathname"] + ".info.json", encoding="utf-8"
        ) as infile:
            metadata = json.load(infile)
        self.assertEqual(metadata["http_headers"]["X-Release"], "2026.08")

    def test_missing_file_metadata_only_skip_when_dmf_false(self):
        """Missing file + unchanged + download_missing_file=false: skip; the
        file stays absent and download_changed is False."""
        pathname = self._write_info_json()
        self.processor.env["CHECK_FILESIZE_ONLY"] = True
        self.processor.env["download_missing_file"] = "false"

        self.run_download(b"data", {"Content-Length": "4"})

        self.assertFalse(self.processor.env["download_changed"])
        self.assertFalse(os.path.isfile(pathname))

    def test_missing_file_skip_reuses_stored_hashes(self):
        """download_missing_file=false + COMPUTE_HASHES + missing file: no crash;
        hashes come from .info.json."""
        pathname = self._write_info_json(
            {"file_sha1": "aaa", "file_sha256": "bbb", "file_md5": "ccc"}
        )
        self.processor.env["CHECK_FILESIZE_ONLY"] = True
        self.processor.env["download_missing_file"] = "false"
        self.processor.env["COMPUTE_HASHES"] = True

        self.run_download(b"data", {"Content-Length": "4"})

        self.assertFalse(self.processor.env["download_changed"])
        self.assertFalse(os.path.isfile(pathname))
        self.assertEqual(self.processor.env["file_sha1"], "aaa")
        self.assertEqual(self.processor.env["file_sha256"], "bbb")
        self.assertEqual(self.processor.env["file_md5"], "ccc")

    def test_missing_file_skip_without_stored_hashes_does_not_crash(self):
        """Same but no stored hashes: still no crash, hashes skipped."""
        pathname = self._write_info_json()
        self.processor.env["CHECK_FILESIZE_ONLY"] = True
        self.processor.env["download_missing_file"] = "false"
        self.processor.env["COMPUTE_HASHES"] = True

        self.run_download(b"data", {"Content-Length": "4"})  # must not raise

        self.assertFalse(self.processor.env["download_changed"])
        self.assertFalse(os.path.isfile(pathname))
        self.assertNotIn("file_sha1", self.processor.env)

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

    def test_content_length_mismatch_warns(self):
        with patch.object(self.processor, "output") as mock_output:
            self.run_download(b"data", {"Content-Length": "5"})

        self.assertTrue(
            any(
                "file size != content-length header" in call.args[0]
                for call in mock_output.call_args_list
            )
        )

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

    def test_download_changed_returns_true_when_file_missing(self):
        self.processor.env["pathname"] = os.path.join(
            self.temp_dir.name, "missing-download.bin"
        )

        changed = self.processor.download_changed(
            case_insensitive_headers({"Content-Length": "10"})
        )

        self.assertTrue(changed)

    def test_download_changed_content_length_mismatch_returns_true(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pathname = os.path.join(temp_dir, "download.bin")
            with open(pathname, "wb") as outfile:
                outfile.write(b"x" * 100)
            self.processor.env["pathname"] = pathname

            changed = self.processor.download_changed(
                case_insensitive_headers({"Content-Length": "200"})
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
                case_insensitive_headers({"ETag": "response-tag"})
            )

        self.assertTrue(changed)

    def test_download_changed_matches_configured_header_case_insensitively(self):
        pathname = os.path.join(self.temp_dir.name, "download.bin")
        with open(pathname, "wb") as outfile:
            outfile.write(b"test data")
        with open(pathname + ".info.json", "w", encoding="utf-8") as outfile:
            json.dump(
                {
                    "http_headers": {
                        "ETag": "cached-tag",
                        "Last-Modified": "Mon, 01 Jan 2024 00:00:00 GMT",
                    }
                },
                outfile,
            )
        self.processor.env["pathname"] = pathname

        for name, value in (
            ("etag", "cached-tag"),
            ("last-modified", "Mon, 01 Jan 2024 00:00:00 GMT"),
        ):
            with self.subTest(name=name):
                self.processor.env["HEADERS_TO_TEST"] = [name]
                self.assertFalse(
                    self.processor.download_changed(
                        case_insensitive_headers({name: value})
                    )
                )

    def test_download_changed_falls_back_to_cached_file_size(self):
        pathname = os.path.join(self.temp_dir.name, "download.bin")
        with open(pathname, "wb") as outfile:
            outfile.write(b"test data")
        with open(pathname + ".info.json", "w", encoding="utf-8") as outfile:
            json.dump({"http_headers": {"ETag": "", "Last-Modified": ""}}, outfile)
        self.processor.env["pathname"] = pathname
        self.processor.env["HEADERS_TO_TEST"] = ["ETag", "Last-Modified"]

        changed = self.processor.download_changed(
            case_insensitive_headers({"Content-Length": str(len(b"test data"))})
        )

        self.assertFalse(changed)

    def test_download_changed_missing_content_length_header_warns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pathname = os.path.join(temp_dir, "download.bin")
            with open(pathname, "wb") as outfile:
                outfile.write(b"test data")
            self.processor.env["pathname"] = pathname
            self.processor.env["HEADERS_TO_TEST"] = ["Content-Length"]

            with patch.object(self.processor, "output") as mock_output:
                self.processor.download_changed(
                    case_insensitive_headers({"ETag": "tag"})
                )

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
