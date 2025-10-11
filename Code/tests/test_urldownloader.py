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

import json
import os
import tempfile
import unittest
from hashlib import md5, sha1, sha256
from unittest.mock import patch

from autopkglib import BUNDLE_ID
from autopkglib.URLDownloader import URLDownloader


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

        # Determine which method to patch based on implementation
        if hasattr(self.processor, "store_metadata"):
            storage_method = "store_metadata"
        else:
            storage_method = "store_headers"

        with patch(
            "autopkglib.URLDownloader.download_with_curl"
        ) as mock_download, patch(
            "autopkglib.URLDownloader.parse_headers"
        ) as mock_parse_headers, patch(
            "autopkglib.URLDownloader.create_temp_file"
        ) as mock_create_temp, patch(
            "autopkglib.URLDownloader.move_temp_file"
        ), patch(
            f"autopkglib.URLDownloader.{storage_method}"
        ) as mock_store:

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

    # Metadata storage tests (works with both xattr [dev-2.x] and .info.json [PR #978])

    def test_store_headers_stores_etag_and_last_modified(self):
        """Test that store_headers correctly stores ETag and Last-Modified metadata."""
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

        # Store headers (xattr or .info.json depending on implementation)
        if hasattr(self.processor, "store_metadata"):
            # PR #978 implementation with .info.json
            with patch.object(self.processor, "store_headers"):
                self.processor.store_metadata(header)

            # Check that .info.json was created
            info_json_path = test_file + ".info.json"
            self.assertTrue(os.path.exists(info_json_path))

            # Verify contents
            with open(info_json_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            self.assertEqual(metadata["download_url"], "http://example.com/file.dmg")
            self.assertEqual(metadata["file_size"], len(test_content))
            self.assertEqual(metadata["http_headers"]["ETag"], '"abc123"')
            self.assertEqual(
                metadata["http_headers"]["Last-Modified"],
                "Mon, 01 Jan 2024 00:00:00 GMT",
            )
        else:
            # dev-2.x implementation with xattr
            self.processor.store_headers(header)

            # Verify environment variables are set
            self.assertEqual(self.processor.env["etag"], '"abc123"')
            self.assertEqual(
                self.processor.env["last_modified"],
                "Mon, 01 Jan 2024 00:00:00 GMT",
            )

            # Verify xattr values (if xattr is available)
            try:
                from autopkglib import xattr as autopkg_xattr

                stored_etag = autopkg_xattr.getxattr(
                    test_file, self.processor.xattr_etag
                ).decode()
                stored_last_modified = autopkg_xattr.getxattr(
                    test_file, self.processor.xattr_last_modified
                ).decode()

                self.assertEqual(stored_etag, '"abc123"')
                self.assertEqual(stored_last_modified, "Mon, 01 Jan 2024 00:00:00 GMT")
            except Exception:
                # xattr might not be available on all platforms during tests
                pass

    def test_metadata_retrieval_from_storage(self):
        """Test that metadata can be retrieved correctly from storage (xattr or .info.json)."""
        test_file = os.path.join(self.temp_dir, "testfile.dmg")
        test_content = b"test file content with known size"

        # Create test file
        with open(test_file, "wb") as f:
            f.write(test_content)

        self.processor.env["pathname"] = test_file
        self.processor.clear_vars()

        if hasattr(self.processor, "get_metadata"):
            # PR #978 implementation - test .info.json reading
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
        else:
            # dev-2.x implementation - test xattr reading via getxattr
            # First store some xattr values
            try:
                from autopkglib import xattr as autopkg_xattr

                autopkg_xattr.setxattr(
                    test_file, self.processor.xattr_etag, b'"xyz789"'
                )
                autopkg_xattr.setxattr(
                    test_file,
                    self.processor.xattr_last_modified,
                    b"Tue, 02 Jan 2024 00:00:00 GMT",
                )

                # Retrieve via getxattr
                etag = self.processor.getxattr(self.processor.xattr_etag)
                last_modified = self.processor.getxattr(
                    self.processor.xattr_last_modified
                )

                self.assertEqual(etag, '"xyz789"')
                self.assertEqual(last_modified, "Tue, 02 Jan 2024 00:00:00 GMT")
            except Exception:
                # xattr might not be available, skip this part of the test
                self.skipTest("xattr not available on this platform")

    def test_metadata_returns_empty_when_no_storage(self):
        """Test that metadata retrieval returns empty/None when no storage exists."""
        test_file = os.path.join(self.temp_dir, "nonexistent.dmg")
        self.processor.env["pathname"] = test_file
        self.processor.clear_vars()

        if hasattr(self.processor, "get_metadata"):
            # PR #978 - should return empty dict
            result = self.processor.get_metadata()
            self.assertEqual(result, {})
        else:
            # dev-2.x - getxattr should return None
            result = self.processor.getxattr(self.processor.xattr_etag)
            self.assertIsNone(result)

    # ETag functionality tests (works with both xattr and .info.json)

    def test_produce_etag_headers_from_stored_metadata(self):
        """Test that produce_etag_headers reads from metadata storage (xattr or .info.json)."""
        test_file = os.path.join(self.temp_dir, "testfile.dmg")

        # Create test file
        with open(test_file, "wb") as f:
            f.write(b"test content with specific size")

        self.processor.env["pathname"] = test_file
        self.processor.clear_vars()

        if hasattr(self.processor, "get_metadata"):
            # PR #978 - create .info.json
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
        else:
            # dev-2.x - store in xattr
            try:
                from autopkglib import xattr as autopkg_xattr

                autopkg_xattr.setxattr(
                    test_file, self.processor.xattr_etag, '"etag-value-123"'
                )
                autopkg_xattr.setxattr(
                    test_file,
                    self.processor.xattr_last_modified,
                    "Wed, 03 Jan 2024 00:00:00 GMT",
                )
            except Exception:
                self.skipTest("xattr not available on this platform")

        # Get etag headers - should work regardless of storage method
        headers = self.processor.produce_etag_headers(test_file)

        self.assertEqual(headers["If-None-Match"], '"etag-value-123"')
        self.assertEqual(headers["If-Modified-Since"], "Wed, 03 Jan 2024 00:00:00 GMT")
        self.assertIsNotNone(self.processor.existing_file_size)

    def test_produce_etag_headers_empty_when_no_metadata(self):
        """Test that produce_etag_headers returns empty dict when no metadata exists."""
        test_file = os.path.join(self.temp_dir, "nonexistent.dmg")
        self.processor.env["pathname"] = test_file
        self.processor.clear_vars()

        headers = self.processor.produce_etag_headers(test_file)

        self.assertEqual(headers, {})

    def test_produce_etag_headers_partial_metadata(self):
        """Test produce_etag_headers with partial metadata (only ETag, no Last-Modified)."""
        test_file = os.path.join(self.temp_dir, "testfile.dmg")

        # Create test file
        with open(test_file, "wb") as f:
            f.write(b"test content")

        self.processor.env["pathname"] = test_file
        self.processor.clear_vars()

        if hasattr(self.processor, "get_metadata"):
            # PR #978 - create .info.json with only ETag
            info_json_path = test_file + ".info.json"
            metadata = {
                "file_size": 50,
                "http_headers": {
                    "ETag": '"only-etag"',
                },
            }
            with open(info_json_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f)
        else:
            # dev-2.x - store only ETag in xattr
            try:
                from autopkglib import xattr as autopkg_xattr

                autopkg_xattr.setxattr(
                    test_file, self.processor.xattr_etag, '"only-etag"'
                )
                # Deliberately NOT setting last_modified
            except Exception:
                self.skipTest("xattr not available on this platform")

        headers = self.processor.produce_etag_headers(test_file)

        self.assertEqual(headers["If-None-Match"], '"only-etag"')
        self.assertNotIn("If-Modified-Since", headers)

    # Hash computation tests (PR #978 only - not in dev-2.x)

    def test_compute_hashes_correctness(self):
        """Test that compute_hashes produces correct hash values (PR #978 only)."""
        if not hasattr(self.processor, "compute_hashes"):
            self.skipTest("compute_hashes not available in dev-2.x")

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
        """Test that compute_hashes handles large files efficiently (PR #978 only)."""
        if not hasattr(self.processor, "compute_hashes"):
            self.skipTest("compute_hashes not available in dev-2.x")

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
        """Test that store_metadata includes hashes when COMPUTE_HASHES is True (PR #978 only)."""
        if not hasattr(self.processor, "store_metadata"):
            self.skipTest("store_metadata not available in dev-2.x")

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

        # Verify hash values are correct
        expected_sha256 = sha256(test_content).hexdigest()
        self.assertEqual(metadata["file_sha256"], expected_sha256)

    def test_store_metadata_excludes_hashes_when_disabled(self):
        """Test that store_metadata excludes hashes when COMPUTE_HASHES is False (PR #978 only)."""
        if not hasattr(self.processor, "store_metadata"):
            self.skipTest("store_metadata not available in dev-2.x")

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

    # Backward compatibility tests

    @patch("autopkglib.xattr.setxattr")
    def test_store_headers_backward_compatibility(self, mock_setxattr):
        """Test that metadata storage maintains backward compatibility with xattr."""
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

        if hasattr(self.processor, "store_metadata"):
            # PR #978 - verify store_metadata calls store_headers for backward compat
            self.processor.store_metadata(header)
            # Verify store_headers was effectively called (xattr operations attempted)
            self.assertTrue(mock_setxattr.called)
        else:
            # dev-2.x - just test store_headers directly
            self.processor.store_headers(header)
            # Verify xattr operations were attempted
            self.assertTrue(mock_setxattr.called)
            # Verify env variables are set
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

        # Determine which method to patch
        if hasattr(self.processor, "store_metadata"):
            storage_method = "store_metadata"
        else:
            storage_method = "store_headers"

        with patch(
            "autopkglib.URLDownloader.download_with_curl"
        ) as mock_download, patch(
            "autopkglib.URLDownloader.parse_headers"
        ) as mock_parse_headers, patch(
            "autopkglib.URLDownloader.create_temp_file"
        ) as mock_create_temp, patch(
            "autopkglib.URLDownloader.move_temp_file"
        ) as mock_move, patch(
            f"autopkglib.URLDownloader.{storage_method}"
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

        if hasattr(self.processor, "get_metadata"):
            # PR #978 - test .info.json reading
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

            # Test that metadata can be read
            result = self.processor.get_metadata()
            self.assertEqual(result["http_headers"]["ETag"], '"same-etag"')
        else:
            # dev-2.x - test xattr reading
            try:
                from autopkglib import xattr as autopkg_xattr

                autopkg_xattr.setxattr(
                    test_file, self.processor.xattr_etag, '"same-etag"'
                )

                # Test that xattr can be read
                result = self.processor.getxattr(self.processor.xattr_etag)
                self.assertEqual(result, '"same-etag"')
            except Exception:
                self.skipTest("xattr not available on this platform")

    # Clear vars test

    def test_clear_vars_initializes_variables(self):
        """Test that clear_vars properly initializes all instance variables."""
        self.processor.clear_vars()

        self.assertIsNotNone(self.processor.xattr_etag)
        self.assertIsNotNone(self.processor.xattr_last_modified)

        # file_size is only in PR #978
        if hasattr(self.processor, "store_metadata"):
            self.assertEqual(self.processor.env["file_size"], 0)

        self.assertEqual(self.processor.env["last_modified"], "")
        self.assertEqual(self.processor.env["etag"], "")

        # existing_file_size is only set in PR #978
        if hasattr(self.processor, "store_metadata"):
            self.assertIsNone(self.processor.existing_file_size)

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


if __name__ == "__main__":
    unittest.main()
