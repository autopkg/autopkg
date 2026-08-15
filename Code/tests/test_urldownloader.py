#!/usr/local/autopkg/python
#
# Copyright 2025 Elliot Jordan
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

import json
import os
import sys
import tempfile
import unittest
from hashlib import md5, sha1, sha256
from unittest.mock import patch

from autopkglib import BUNDLE_ID, ProcessorError
from autopkglib.URLDownloader import URLDownloader
from autopkglib.URLGetter import URLGetter


class TestURLDownloader(unittest.TestCase):
    """Test class for URLDownloader Processor."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.good_env = {
            "url": "http://example.com/file.dmg",
            "RECIPE_CACHE_DIR": self.temp_dir,
        }
        self.processor = URLDownloader()
        self.processor.env = self.good_env.copy()

    def tearDown(self):
        """Clean up after tests."""
        # Clean up temp files
        if os.path.exists(self.temp_dir):
            for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                for name in files:
                    try:
                        os.remove(os.path.join(root, name))
                    except OSError:
                        pass
                for name in dirs:
                    try:
                        os.rmdir(os.path.join(root, name))
                    except OSError:
                        pass
            try:
                os.rmdir(self.temp_dir)
            except OSError:
                pass

    # Basic functionality tests

    def test_basic_download(self):
        """Test basic file download without complications."""
        temp_file = os.path.join(self.temp_dir, "tempfile")

        with (
            patch.object(URLDownloader, "download_with_curl") as mock_download,
            patch.object(URLDownloader, "parse_headers") as mock_parse_headers,
            patch.object(URLDownloader, "create_temp_file") as mock_create_temp,
            patch.object(URLDownloader, "move_temp_file"),
            patch.object(URLDownloader, "store_metadata") as mock_store,
        ):
            mock_create_temp.return_value = temp_file
            mock_download.return_value = ""
            mock_parse_headers.return_value = {
                "http_result_code": "200",
                "http_result_description": "OK",
            }

            # Create a fake downloaded file
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write("test content")

            self.processor.main()

            # Verify the download was attempted
            mock_download.assert_called_once()
            mock_store.assert_called_once()

    # Metadata storage tests for .info.json sidecars and legacy xattr writes.

    def test_store_metadata_writes_info_json(self):
        """Test that store_metadata writes ETag and Last-Modified metadata."""
        test_file = os.path.join(self.temp_dir, "testfile.dmg")
        test_content = b"test file content"

        # Create test file
        with open(test_file, "wb") as f:
            f.write(test_content)

        self.processor.env["pathname"] = test_file
        self.processor.env["url"] = "http://example.com/file.dmg"

        # Initialize xattr names
        self.processor.clear_vars()

        header = {
            "etag": '"abc123"',
            "last-modified": "Mon, 01 Jan 2024 00:00:00 GMT",
        }

        with patch.object(self.processor, "store_headers"):
            self.processor.store_metadata(header)

        info_json_path = test_file + ".info.json"
        self.assertTrue(os.path.exists(info_json_path))

        with open(info_json_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        self.assertEqual(metadata["download_url"], "http://example.com/file.dmg")
        self.assertEqual(metadata["file_size"], len(test_content))
        self.assertEqual(self.processor.env["download_info"], metadata)
        self.assertEqual(metadata["http_headers"]["ETag"], '"abc123"')
        self.assertEqual(
            metadata["http_headers"]["Last-Modified"],
            "Mon, 01 Jan 2024 00:00:00 GMT",
        )

    def test_store_metadata_uses_redirected_download_url(self):
        """store_metadata records the final redirected URL when curl reports one."""
        test_file = os.path.join(self.temp_dir, "testfile.dmg")
        with open(test_file, "wb") as f:
            f.write(b"test file content")

        self.processor.env["pathname"] = test_file
        self.processor.env["url"] = "http://example.com/file.dmg"
        self.processor.clear_vars()
        self.processor.env["download_url"] = "https://old.example.com/file.dmg"

        header = {
            "etag": '"abc123"',
            "http_redirected": "https://cdn.example.com/file.dmg",
            "last-modified": "Mon, 01 Jan 2024 00:00:00 GMT",
        }

        with patch.object(self.processor, "store_headers"):
            self.processor.store_metadata(header)

        with open(test_file + ".info.json", "r", encoding="utf-8") as f:
            metadata = json.load(f)

        self.assertEqual(metadata["download_url"], "https://cdn.example.com/file.dmg")
        self.assertEqual(
            self.processor.env["download_url"], "https://cdn.example.com/file.dmg"
        )

    def test_store_metadata_replaces_stale_redirect_with_current_url(self):
        test_file = os.path.join(self.temp_dir, "testfile.dmg")
        with open(test_file, "wb") as outfile:
            outfile.write(b"test file content")
        self.processor.env.update(
            {
                "download_url": "https://old.example.com/file.dmg",
                "pathname": test_file,
            }
        )

        with patch.object(self.processor, "store_headers"):
            self.processor.store_metadata({})

        with open(test_file + ".info.json", encoding="utf-8") as infile:
            metadata = json.load(infile)
        self.assertEqual(metadata["download_url"], self.processor.env["url"])

    def test_download_changed_invalid_content_length_returns_changed(self):
        test_file = os.path.join(self.temp_dir, "testfile.dmg")
        with open(test_file, "wb") as outfile:
            outfile.write(b"test data")
        with open(test_file + ".info.json", "w", encoding="utf-8") as outfile:
            json.dump({"http_headers": {}}, outfile)
        self.processor.env["pathname"] = test_file

        with patch.object(self.processor, "output") as mock_output:
            changed = self.processor.download_changed(
                {"http_result_code": "200", "content-length": "invalid"}
            )

        self.assertTrue(changed)
        self.assertTrue(
            any(
                "Content-Length' invalid" in call.args[0]
                for call in mock_output.call_args_list
            )
        )

    def test_store_metadata_preserves_custom_headers(self):
        test_file = os.path.join(self.temp_dir, "testfile.dmg")
        with open(test_file, "wb") as outfile:
            outfile.write(b"test file content")
        self.processor.env.update(
            {"HEADERS_TO_TEST": ["X-Release"], "pathname": test_file}
        )

        with patch.object(self.processor, "store_headers"):
            self.processor.store_metadata({"x-release": "2026.08"})

        with open(test_file + ".info.json", encoding="utf-8") as infile:
            metadata = json.load(infile)
        self.assertEqual(metadata["http_headers"]["X-Release"], "2026.08")

    def test_metadata_retrieval_from_storage(self):
        """Test that metadata can be retrieved correctly from .info.json."""
        test_file = os.path.join(self.temp_dir, "testfile.dmg")
        test_content = b"test file content with known size"

        # Create test file
        with open(test_file, "wb") as f:
            f.write(test_content)

        self.processor.env["pathname"] = test_file
        self.processor.clear_vars()

        info_json_path = test_file + ".info.json"

        metadata = {
            "download_url": "http://example.com/file.dmg",
            "file_name": "testfile.dmg",
            "file_size": 1024,
            "http_headers": {
                "Content-Length": 1024,
                "ETag": '"xyz789"',
                "Last-Modified": "Tue, 02 Jan 2024 00:00:00 GMT",
            },
        }
        with open(info_json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f)

        result = self.processor.get_metadata()

        self.assertEqual(result["download_url"], "http://example.com/file.dmg")
        self.assertEqual(result["file_size"], 1024)
        self.assertEqual(result["http_headers"]["ETag"], '"xyz789"')

    def test_metadata_returns_empty_when_no_storage(self):
        """Test that metadata retrieval returns empty dict when no storage exists."""
        test_file = os.path.join(self.temp_dir, "nonexistent.dmg")
        self.processor.env["pathname"] = test_file
        self.processor.clear_vars()

        result = self.processor.get_metadata()
        self.assertEqual(result, {})

    def test_getxattr_raises_processor_error(self):
        """getxattr() must raise ProcessorError in .info.json metadata mode."""
        with self.assertRaises(ProcessorError):
            self.processor.getxattr("any.xattr.name")

    def test_env_bool_accepts_strings(self):
        """Boolean-like env strings are parsed, not evaluated with truthiness."""
        for value in ("true", "True", "TRUE", "  true  ", "yes", "on", "1"):
            self.processor.env["flag"] = value
            self.assertTrue(
                self.processor.env_bool("flag"), f"{value!r} should be True"
            )
        for value in ("false", "False", "no", "off", "0", ""):
            self.processor.env["flag"] = value
            self.assertFalse(
                self.processor.env_bool("flag"), f"{value!r} should be False"
            )

        self.processor.env["none_value"] = None
        self.assertTrue(self.processor.env_bool("none_value", default=True))
        self.assertTrue(self.processor.env_bool("missing", default=True))

    def test_env_bool_prefetch_error_mentions_filename(self):
        self.processor.env["prefetch_filename"] = "file.dmg"

        with self.assertRaisesRegex(ProcessorError, "use filename"):
            self.processor.env_bool("prefetch_filename")

    def test_env_bool_rejects_unknown_strings(self):
        """Unrecognised strings fail loudly rather than silently defaulting."""
        self.processor.env["bad_value"] = "ture"

        with self.assertRaisesRegex(ProcessorError, "bad_value must be a boolean"):
            self.processor.env_bool("bad_value")

    def test_env_bool_rejects_non_boolean_values(self):
        """Unexpected value types fail loudly instead of using Python truthiness."""
        self.processor.env["bad_value"] = 1

        with self.assertRaisesRegex(ProcessorError, "bad_value must be a boolean"):
            self.processor.env_bool("bad_value")

    def test_get_metadata_returns_empty_on_corrupt_json(self):
        """get_metadata() must return {} and not raise when .info.json is corrupt."""
        test_file = os.path.join(self.temp_dir, "testfile.dmg")
        with open(test_file, "wb") as f:
            f.write(b"dummy")
        with open(test_file + ".info.json", "w", encoding="utf-8") as f:
            f.write("not valid json {{{")

        self.processor.env["pathname"] = test_file
        result = self.processor.get_metadata()
        self.assertEqual(result, {})

    # ETag functionality tests for .info.json metadata.

    @unittest.skipUnless(
        sys.platform in ("darwin", "linux"), "xattr not reliable on Windows"
    )
    def test_produce_etag_headers_from_stored_metadata(self):
        """Test that produce_etag_headers reads from .info.json metadata."""
        test_file = os.path.join(self.temp_dir, "testfile.dmg")

        # Create test file
        with open(test_file, "wb") as f:
            f.write(b"test content with specific size")

        self.processor.env["pathname"] = test_file
        self.processor.clear_vars()

        info_json_path = test_file + ".info.json"
        metadata = {
            "file_size": 100,
            "http_headers": {
                "ETag": '"etag-value-123"',
                "Last-Modified": "Wed, 03 Jan 2024 00:00:00 GMT",
            },
        }
        with open(info_json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f)

        headers = self.processor.produce_etag_headers()

        self.assertEqual(headers["If-None-Match"], '"etag-value-123"')
        self.assertEqual(headers["If-Modified-Since"], "Wed, 03 Jan 2024 00:00:00 GMT")

    def test_produce_etag_headers_empty_when_no_metadata(self):
        """Test that produce_etag_headers returns empty dict when no metadata exists."""
        test_file = os.path.join(self.temp_dir, "nonexistent.dmg")
        self.processor.env["pathname"] = test_file
        self.processor.clear_vars()

        headers = self.processor.produce_etag_headers()

        self.assertEqual(headers, {})

    def test_size_only_check_uses_real_file_size_not_stale_metadata(self):
        """A stale .info.json file_size must not make a changed cache look unchanged."""
        test_file = os.path.join(self.temp_dir, "testfile.dmg")
        with open(test_file, "wb") as f:
            f.write(b"short")

        metadata = {
            "file_size": 100,
            "http_headers": {
                "Content-Length": 100,
            },
        }
        with open(test_file + ".info.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f)

        self.processor.env["pathname"] = test_file
        self.processor.env["CHECK_FILESIZE_ONLY"] = True
        self.processor.clear_vars()

        headers = self.processor.produce_etag_headers()
        changed = self.processor.download_changed(
            {
                "http_result_code": "200",
                "content-length": "100",
            }
        )

        self.assertEqual(headers, {})
        self.assertTrue(changed)

    def test_download_changed_populates_cached_download_info(self):
        """Cache-hit checks expose previous .info.json metadata in env."""
        test_file = os.path.join(self.temp_dir, "testfile.dmg")
        with open(test_file, "wb") as f:
            f.write(b"test content")

        metadata = {
            "download_url": "https://cdn.example.com/testfile.dmg",
            "file_size": 12,
            "http_headers": {
                "Content-Length": 12,
                "ETag": '"cached"',
                "Last-Modified": "Tue, 02 Jan 2024 00:00:00 GMT",
            },
        }
        with open(test_file + ".info.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f)

        self.processor.env["pathname"] = test_file
        self.processor.env["HEADERS_TO_TEST"] = ["ETag"]
        self.processor.clear_vars()

        changed = self.processor.download_changed(
            {"http_result_code": "200", "etag": '"cached"'}
        )

        self.assertFalse(changed)
        self.assertEqual(self.processor.env["download_info"], metadata)
        self.assertEqual(self.processor.env["etag"], '"cached"')
        self.assertEqual(
            self.processor.env["last_modified"], "Tue, 02 Jan 2024 00:00:00 GMT"
        )
        self.assertEqual(
            self.processor.env["download_url"], "https://cdn.example.com/testfile.dmg"
        )

    def test_download_changed_is_version_only_ignores_missing_file(self):
        """download_changed compares versions only. A missing file whose stored
        metadata matches the remote is NOT 'changed', regardless of
        download_missing_file (that only affects materialising in main())."""
        test_file = os.path.join(self.temp_dir, "missing.dmg")
        with open(test_file + ".info.json", "w", encoding="utf-8") as f:
            json.dump({"http_headers": {"Content-Length": 10}}, f)

        self.processor.env["pathname"] = test_file
        self.processor.env["HEADERS_TO_TEST"] = ["Content-Length"]
        self.processor.clear_vars()

        response = {"http_result_code": "200", "content-length": "10"}
        for dmf in ("true", "false"):
            self.processor.env["download_missing_file"] = dmf
            self.assertFalse(
                self.processor.download_changed(response),
                f"download_missing_file={dmf} must not affect the version check",
            )

    @unittest.skipUnless(
        sys.platform in ("darwin", "linux"), "xattr not reliable on Windows"
    )
    def test_produce_etag_headers_partial_metadata(self):
        """Test produce_etag_headers with partial metadata (only ETag, no Last-Modified)."""
        test_file = os.path.join(self.temp_dir, "testfile.dmg")

        # Create test file
        with open(test_file, "wb") as f:
            f.write(b"test content")

        self.processor.env["pathname"] = test_file
        self.processor.clear_vars()

        info_json_path = test_file + ".info.json"
        metadata = {
            "file_size": 50,
            "http_headers": {
                "ETag": '"only-etag"',
            },
        }
        with open(info_json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f)

        headers = self.processor.produce_etag_headers()

        self.assertEqual(headers["If-None-Match"], '"only-etag"')
        self.assertNotIn("If-Modified-Since", headers)

    # Hash computation tests

    def test_compute_hashes_correctness(self):
        """Test that compute_hashes produces correct hash values."""
        test_file = os.path.join(self.temp_dir, "testfile.dmg")
        test_content = b"Hello, AutoPkg! This is test content."

        # Create test file
        with open(test_file, "wb") as f:
            f.write(test_content)

        # Compute expected hashes
        expected_sha1 = sha1(test_content).hexdigest()
        expected_sha256 = sha256(test_content).hexdigest()
        expected_md5 = md5(test_content).hexdigest()

        self.processor.env["pathname"] = test_file

        # Compute hashes
        hashes = self.processor.compute_hashes()

        self.assertEqual(hashes["sha1"], expected_sha1)
        self.assertEqual(hashes["sha256"], expected_sha256)
        self.assertEqual(hashes["md5"], expected_md5)

    def test_compute_hashes_with_large_file(self):
        """Test that compute_hashes handles large files efficiently."""
        test_file = os.path.join(self.temp_dir, "largefile.dmg")
        # Create a file larger than the chunk size (4096 bytes)
        test_content = b"X" * 10000

        with open(test_file, "wb") as f:
            f.write(test_content)

        expected_sha256 = sha256(test_content).hexdigest()

        self.processor.env["pathname"] = test_file

        hashes = self.processor.compute_hashes()

        # Verify correct hash despite chunking
        self.assertEqual(hashes["sha256"], expected_sha256)

    def test_store_metadata_includes_hashes_when_enabled(self):
        """Test that store_metadata includes hashes when COMPUTE_HASHES is True."""
        test_file = os.path.join(self.temp_dir, "testfile.dmg")
        test_content = b"test content for hashing"

        with open(test_file, "wb") as f:
            f.write(test_content)

        self.processor.env["pathname"] = test_file
        self.processor.env["url"] = "http://example.com/file.dmg"
        self.processor.env["COMPUTE_HASHES"] = True

        with patch.object(self.processor, "store_headers"):
            header = {
                "etag": '"hash123"',
                "last-modified": "Thu, 04 Jan 2024 00:00:00 GMT",
            }
            self.processor.store_metadata(header)

        info_json_path = test_file + ".info.json"
        with open(info_json_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # Verify hashes are included
        self.assertIn("file_sha1", metadata)
        self.assertIn("file_sha256", metadata)
        self.assertIn("file_md5", metadata)

        # Verify hash values are correct and available to downstream processors
        expected_sha1 = sha1(test_content).hexdigest()
        expected_sha256 = sha256(test_content).hexdigest()
        expected_md5 = md5(test_content).hexdigest()
        self.assertEqual(metadata["file_sha1"], expected_sha1)
        self.assertEqual(metadata["file_sha256"], expected_sha256)
        self.assertEqual(metadata["file_md5"], expected_md5)
        self.assertEqual(self.processor.env["file_sha1"], expected_sha1)
        self.assertEqual(self.processor.env["file_sha256"], expected_sha256)
        self.assertEqual(self.processor.env["file_md5"], expected_md5)
        self.assertIn("file_sha1", self.processor.output_variables)
        self.assertIn("file_sha256", self.processor.output_variables)
        self.assertIn("file_md5", self.processor.output_variables)

    def test_store_metadata_excludes_hashes_when_disabled(self):
        """Test that store_metadata excludes hashes when COMPUTE_HASHES is False."""
        test_file = os.path.join(self.temp_dir, "testfile.dmg")
        test_content = b"test content"

        with open(test_file, "wb") as f:
            f.write(test_content)

        self.processor.env["pathname"] = test_file
        self.processor.env["url"] = "http://example.com/file.dmg"
        self.processor.env["COMPUTE_HASHES"] = False

        with patch.object(self.processor, "store_headers"):
            header = {
                "etag": '"nohash"',
                "last-modified": "Fri, 05 Jan 2024 00:00:00 GMT",
            }
            self.processor.store_metadata(header)

        info_json_path = test_file + ".info.json"
        with open(info_json_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # Verify hashes are NOT included
        self.assertNotIn("file_sha1", metadata)
        self.assertNotIn("file_sha256", metadata)
        self.assertNotIn("file_md5", metadata)

    # Legacy xattr behavior tests

    @patch("autopkglib.xattr.setxattr")
    def test_store_headers_legacy_xattr_behavior(self, mock_setxattr):
        """Test that metadata storage maintains legacy xattr behavior."""
        test_file = os.path.join(self.temp_dir, "testfile.dmg")

        with open(test_file, "wb") as f:
            f.write(b"test")

        self.processor.env["pathname"] = test_file
        self.processor.env["url"] = "http://example.com/file.dmg"

        # Initialize xattr names
        self.processor.clear_vars()

        header = {
            "etag": '"compat123"',
            "last-modified": "Sat, 06 Jan 2024 00:00:00 GMT",
        }

        self.processor.store_metadata(header)

        self.assertTrue(mock_setxattr.called)
        self.assertEqual(self.processor.env["etag"], '"compat123"')
        self.assertEqual(
            self.processor.env["last_modified"], "Sat, 06 Jan 2024 00:00:00 GMT"
        )

    # Input variable tests

    def test_download_dir_input_variable(self):
        """Test that download_dir input variable is respected."""
        custom_dir = os.path.join(self.temp_dir, "custom_downloads")
        os.makedirs(custom_dir, exist_ok=True)

        self.processor.env["download_dir"] = custom_dir
        self.processor.env["url"] = "http://example.com/file.dmg"

        result_dir = self.processor.get_download_dir()

        self.assertEqual(result_dir, custom_dir)

    def test_filename_from_url(self):
        """Test that filename is extracted from URL."""
        self.processor.env["url"] = "http://example.com/path/to/custom_name.dmg"

        filename = self.processor.get_filename()

        self.assertEqual(filename, "custom_name.dmg")

    # Output variable tests

    def test_output_variables_set(self):
        """Test that expected output variables are set after download."""
        temp_file = os.path.join(self.temp_dir, "tempfile")
        final_file = os.path.join(self.temp_dir, "downloads", "file.dmg")

        os.makedirs(os.path.dirname(final_file), exist_ok=True)

        # Set required env vars
        self.processor.env["CHECK_FILESIZE_ONLY"] = False

        with (
            patch.object(URLDownloader, "download_with_curl") as mock_download,
            patch.object(URLDownloader, "parse_headers") as mock_parse_headers,
            patch.object(URLDownloader, "create_temp_file") as mock_create_temp,
            patch.object(URLDownloader, "move_temp_file") as mock_move,
            patch.object(URLDownloader, "store_metadata"),
        ):
            mock_create_temp.return_value = temp_file
            mock_download.return_value = ""
            mock_parse_headers.return_value = {
                "http_result_code": "200",
                "http_result_description": "OK",
                "etag": '"output123"',
            }

            # Create fake file
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write("output test")

            def mock_move_file(src):
                with open(final_file, "w", encoding="utf-8") as f:
                    f.write("output test")
                self.processor.env["pathname"] = final_file

            mock_move.side_effect = mock_move_file

            self.processor.main()

            # Verify output variables
            self.assertIn("pathname", self.processor.env)
            self.assertIn("etag", self.processor.env)
            self.assertIn("last_modified", self.processor.env)
            self.assertIn("download_changed", self.processor.env)

    # Error handling tests

    def test_missing_url_raises_error(self):
        """Test that missing 'url' input variable raises KeyError."""
        self.processor.env = {"RECIPE_CACHE_DIR": self.temp_dir}

        with self.assertRaises(KeyError):
            self.processor.get_filename()

    # Conditional download tests (304 Not Modified)

    def test_conditional_download_304_metadata_preserved(self):
        """Test that existing file metadata is preserved for conditional downloads."""
        test_file = os.path.join(self.temp_dir, "downloads", "existing.dmg")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)

        # Create existing file
        with open(test_file, "wb") as f:
            f.write(b"existing content")

        self.processor.env["pathname"] = test_file
        self.processor.clear_vars()

        info_json_path = test_file + ".info.json"
        metadata = {
            "file_size": 16,
            "http_headers": {
                "ETag": '"same-etag"',
                "Last-Modified": "Sun, 07 Jan 2024 00:00:00 GMT",
            },
        }
        with open(info_json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f)

        result = self.processor.get_metadata()
        self.assertEqual(result["http_headers"]["ETag"], '"same-etag"')

    def test_cache_hit_populates_hash_outputs_when_enabled(self):
        """Test that cache hits expose hashes when COMPUTE_HASHES is True."""
        cached_content = b"cached content for hashing"
        download_dir = os.path.join(self.temp_dir, "downloads")
        os.makedirs(download_dir, exist_ok=True)
        cached_file = os.path.join(download_dir, "file.dmg")

        with open(cached_file, "wb") as f:
            f.write(cached_content)
        with open(cached_file + ".info.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "file_size": len(cached_content),
                    "http_headers": {
                        "Content-Length": len(cached_content),
                    },
                },
                f,
            )

        self.processor.env["COMPUTE_HASHES"] = True
        self.processor.env["CHECK_FILESIZE_ONLY"] = True

        with (
            patch.object(URLDownloader, "download_with_curl") as mock_download,
            patch.object(URLDownloader, "parse_headers") as mock_parse_headers,
        ):
            mock_download.return_value = ""
            mock_parse_headers.return_value = {
                "http_result_code": "200",
                "http_result_description": "OK",
                "content-length": str(len(cached_content)),
            }

            self.processor.main()

        self.assertFalse(self.processor.env["download_changed"])
        self.assertEqual(
            self.processor.env["file_sha1"], sha1(cached_content).hexdigest()
        )
        self.assertEqual(
            self.processor.env["file_sha256"], sha256(cached_content).hexdigest()
        )
        self.assertEqual(
            self.processor.env["file_md5"], md5(cached_content).hexdigest()
        )

    def _run_main_with_mocked_curl(self, content_length):
        """Run main() with curl mocked to return a 200 of the given size."""
        temporary_path = os.path.join(self.temp_dir, "download.tmp")
        with open(temporary_path, "wb") as outfile:
            outfile.write(b"x" * content_length)
        with (
            patch.object(URLDownloader, "download_with_curl") as mock_download,
            patch.object(URLDownloader, "parse_headers") as mock_parse_headers,
            patch.object(
                URLDownloader, "create_temp_file", return_value=temporary_path
            ),
        ):
            mock_download.return_value = ""
            mock_parse_headers.return_value = {
                "http_result_code": "200",
                "http_result_description": "OK",
                "content-length": str(content_length),
            }
            self.processor.main()

    def test_main_materializes_missing_file_without_marking_changed(self):
        """Missing file + unchanged version + download_missing_file default:
        re-fetch the file but keep download_changed False (version is the
        signal, not file presence)."""
        download_dir = os.path.join(self.temp_dir, "downloads")
        os.makedirs(download_dir, exist_ok=True)
        pathname = os.path.join(download_dir, "file.dmg")
        # .info.json present, cached file absent.
        with open(pathname + ".info.json", "w", encoding="utf-8") as f:
            json.dump({"file_size": 5, "http_headers": {"Content-Length": 5}}, f)

        self.processor.env["CHECK_FILESIZE_ONLY"] = True
        with patch.object(self.processor, "output") as mock_output:
            self._run_main_with_mocked_curl(5)

        self.assertFalse(self.processor.env["download_changed"])
        self.assertTrue(os.path.isfile(pathname))
        with open(pathname, "rb") as infile:
            self.assertEqual(infile.read(), b"xxxxx")
        with open(pathname + ".info.json", encoding="utf-8") as infile:
            self.assertEqual(json.load(infile)["file_size"], 5)
        self.assertTrue(
            any(
                "Re-downloaded missing file" in call.args[0]
                for call in mock_output.call_args_list
            )
        )
        self.assertEqual(
            self.processor.env["url_downloader_summary_result"],
            {
                "summary_text": "The following missing items were re-downloaded:",
                "data": {"download_path": pathname},
            },
        )

    def test_main_metadata_only_skip_reuses_stored_hashes(self):
        """download_missing_file=false + missing file + unchanged + COMPUTE_HASHES:
        no crash; hashes are reused from .info.json and the file is not fetched."""
        download_dir = os.path.join(self.temp_dir, "downloads")
        os.makedirs(download_dir, exist_ok=True)
        pathname = os.path.join(download_dir, "file.dmg")
        with open(pathname + ".info.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "file_size": 5,
                    "http_headers": {"Content-Length": 5},
                    "file_sha1": "aaa",
                    "file_sha256": "bbb",
                    "file_md5": "ccc",
                },
                f,
            )

        self.processor.env["download_missing_file"] = "false"
        self.processor.env["COMPUTE_HASHES"] = True
        self.processor.env["CHECK_FILESIZE_ONLY"] = True
        self._run_main_with_mocked_curl(5)

        self.assertFalse(self.processor.env["download_changed"])
        self.assertFalse(os.path.isfile(pathname))
        self.assertEqual(self.processor.env["file_sha1"], "aaa")
        self.assertEqual(self.processor.env["file_sha256"], "bbb")
        self.assertEqual(self.processor.env["file_md5"], "ccc")

    def test_main_metadata_only_skip_without_stored_hashes_does_not_crash(self):
        """Same as above but .info.json has no stored hashes: still no crash,
        hashes are simply skipped."""
        download_dir = os.path.join(self.temp_dir, "downloads")
        os.makedirs(download_dir, exist_ok=True)
        pathname = os.path.join(download_dir, "file.dmg")
        with open(pathname + ".info.json", "w", encoding="utf-8") as f:
            json.dump({"file_size": 5, "http_headers": {"Content-Length": 5}}, f)

        self.processor.env["download_missing_file"] = "false"
        self.processor.env["COMPUTE_HASHES"] = True
        self.processor.env["CHECK_FILESIZE_ONLY"] = True
        self._run_main_with_mocked_curl(5)  # must not raise

        self.assertFalse(self.processor.env["download_changed"])
        self.assertNotIn("file_sha1", self.processor.env)

    # Clear vars test

    def test_clear_vars_initializes_variables(self):
        """Test that clear_vars properly initializes all instance variables."""
        self.processor.clear_vars()

        self.assertIsNotNone(self.processor.xattr_etag)
        self.assertIsNotNone(self.processor.xattr_last_modified)

        self.assertEqual(self.processor.env["file_size"], 0)

        self.assertEqual(self.processor.env["last_modified"], "")
        self.assertEqual(self.processor.env["etag"], "")

    # Platform-specific xattr names

    @patch("platform.platform")
    def test_xattr_names_linux(self, mock_platform):
        """Test that xattr names are prefixed with 'user.' on Linux."""
        mock_platform.return_value = "Linux-5.4.0"

        self.processor.clear_vars()

        self.assertTrue(self.processor.xattr_etag.startswith("user."))
        self.assertTrue(self.processor.xattr_last_modified.startswith("user."))

    @patch("platform.platform")
    def test_xattr_names_macos(self, mock_platform):
        """Test that xattr names are not prefixed with 'user.' on macOS."""
        mock_platform.return_value = "Darwin-20.6.0"

        self.processor.clear_vars()

        self.assertFalse(self.processor.xattr_etag.startswith("user."))
        self.assertFalse(self.processor.xattr_last_modified.startswith("user."))
        self.assertTrue(BUNDLE_ID in self.processor.xattr_etag)

    def _require_prefetch_filename(self):
        if not hasattr(self.processor, "prefetch_filename"):
            self.skipTest("prefetch_filename not available on this processor")

    def _prefetch_patches(self, headers):
        return (
            patch.object(
                URLDownloader,
                "prepare_base_curl_cmd",
                return_value=["curl", "http://example.com/file.dmg"],
            ),
            patch.object(URLGetter, "add_curl_common_opts"),
            patch.object(URLGetter, "download_with_curl", return_value=""),
            patch.object(URLGetter, "parse_headers", return_value=headers),
        )

    def test_prefetch_filename_calls_curl_common_opts(self):
        """prefetch_filename must call add_curl_common_opts before the HEAD
        request so options like --compressed or custom headers are honoured
        (regression: PR #925 added this call; this test pins the behaviour)."""
        self._require_prefetch_filename()
        prepare, add_opts, download, parse = self._prefetch_patches({})
        with prepare, add_opts as mock_add_opts, download, parse:
            self.processor.prefetch_filename()
        mock_add_opts.assert_called_once()

    def test_prefetch_filename_returns_content_disposition_filename(self):
        """prefetch_filename must extract the filename from the
        Content-Disposition header when present."""
        self._require_prefetch_filename()
        prepare, add_opts, download, parse = self._prefetch_patches(
            {"content-disposition": 'attachment; filename="MyApp-1.0.dmg"'}
        )
        with prepare, add_opts, download, parse:
            result = self.processor.prefetch_filename()
        self.assertEqual(result, "MyApp-1.0.dmg")

    def test_prefetch_filename_strips_content_disposition_path_components(self):
        """Content-Disposition filenames must not escape download_dir."""
        self._require_prefetch_filename()
        prepare, add_opts, download, parse = self._prefetch_patches(
            {"content-disposition": 'attachment; filename="../../tmp/evil.pkg"'}
        )
        with prepare, add_opts, download, parse:
            result = self.processor.prefetch_filename()
        self.assertEqual(result, "evil.pkg")

    def test_prefetch_filename_strips_backslash_path_components(self):
        """Backslash-separated filenames are unsafe on Windows and must be stripped."""
        self._require_prefetch_filename()
        prepare, add_opts, download, parse = self._prefetch_patches(
            {"content-disposition": 'attachment; filename="..\\..\\tmp\\evil.pkg"'}
        )
        with prepare, add_opts, download, parse:
            result = self.processor.prefetch_filename()
        self.assertEqual(result, "evil.pkg")

    def test_prefetch_filename_falls_back_to_redirect_url(self):
        """When there's no Content-Disposition header but the response
        includes an http_redirected URL, the filename is taken from
        the final path component of that URL."""
        self._require_prefetch_filename()
        prepare, add_opts, download, parse = self._prefetch_patches(
            {"http_redirected": "https://cdn.example.com/downloads/MyApp-2.0.pkg"}
        )
        with prepare, add_opts, download, parse:
            result = self.processor.prefetch_filename()
        self.assertEqual(result, "MyApp-2.0.pkg")

    def test_prefetch_filename_returns_none_when_no_hints(self):
        """When neither Content-Disposition nor a redirect URL is present,
        prefetch_filename must return None so the caller falls back to the
        URL-derived filename."""
        self._require_prefetch_filename()
        prepare, add_opts, download, parse = self._prefetch_patches({})
        with prepare, add_opts, download, parse:
            result = self.processor.prefetch_filename()
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
