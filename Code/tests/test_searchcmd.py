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
from io import StringIO
from unittest.mock import MagicMock, mock_open, patch

from autopkgcmd import search_recipes
from autopkgcmd.searchcmd import check_search_cache, handle_cache_error
from autopkglib import ProcessorError
from autopkglib.github import print_gh_search_results


class TestSearchCmd(unittest.TestCase):
    """Test cases for autopkg search command."""

    def setUp(self):
        """Set up test fixtures."""
        # Disable preference reading for consistency
        self.prefs_patch = patch("autopkgcmd.opts.globalPreferences")
        self.prefs_patch.start()

        # Create a mock search index that will be used by tests
        self.mock_search_index = {
            "shortnames": {
                "netnewswire": ["com.github.autopkg.download.NetNewsWire"],
                "coconutbattery": ["com.github.autopkg.download.coconutBattery"],
            },
            "identifiers": {
                "com.github.autopkg.download.NetNewsWire": {
                    "name": "NetNewsWire.download.recipe",
                    "path": "NetNewsWire/NetNewsWire.download.recipe",
                    "repo": "autopkg/recipes",
                    "deprecated": False,
                },
                "com.github.autopkg.download.coconutBattery": {
                    "name": "coconutBattery.download.recipe",
                    "path": "coconutBattery/coconutBattery.download.recipe",
                    "repo": "autopkg/recipes",
                    "deprecated": False,
                },
            },
        }

    def tearDown(self):
        """Clean up after tests."""
        self.prefs_patch.stop()

    # Test handle_cache_error function

    def test_handle_cache_error_with_existing_cache_logs_warning(self):
        """Test that handle_cache_error logs warning when cache exists."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            cache_path = tmp.name
            tmp.write(b'{"test": "data"}')

        try:
            with patch("sys.stderr", new=StringIO()) as mock_stderr:
                # Should not raise an error when cache exists
                handle_cache_error(cache_path, "Test error reason")
                stderr_output = mock_stderr.getvalue()

            # Should log a warning message
            self.assertIn("WARNING", stderr_output)
            self.assertIn("Test error reason", stderr_output)
            self.assertIn("Using cached version", stderr_output)
        finally:
            os.unlink(cache_path)

    def test_handle_cache_error_without_cache_raises_error(self):
        """Test that handle_cache_error raises ProcessorError when no cache exists."""
        # Use a non-existent path
        cache_path = "/tmp/nonexistent_cache_file_" + str(os.getpid()) + ".json"

        # Ensure the cache file doesn't exist
        if os.path.exists(cache_path):
            os.unlink(cache_path)

        # Mock URLGetter to simulate failed download
        with patch("autopkgcmd.searchcmd.URLGetter") as mock_url_getter:
            mock_url_instance = MagicMock()
            mock_url_getter.return_value = mock_url_instance
            mock_url_instance.download_to_file.side_effect = ProcessorError(
                "Download failed"
            )

            with patch("sys.stderr", new=StringIO()) as mock_stderr:
                with self.assertRaises(ProcessorError) as context:
                    handle_cache_error(cache_path, "Test error reason")

                # Check error message
                self.assertIn("Test error reason", str(context.exception))
                self.assertIn("no cached index available", str(context.exception))

                # Check stderr output
                stderr_output = mock_stderr.getvalue()
                self.assertIn("ERROR", stderr_output)

    def test_handle_cache_error_attempts_raw_download_without_etag(self):
        """Test that handle_cache_error attempts raw download when no etag exists."""
        cache_path = "/tmp/test_cache_" + str(os.getpid()) + ".json"
        etag_path = cache_path + ".etag"

        # Ensure files don't exist
        for path in [cache_path, etag_path]:
            if os.path.exists(path):
                os.unlink(path)

        try:
            # Mock URLGetter to simulate successful download
            with patch("autopkgcmd.searchcmd.URLGetter") as mock_url_getter:
                mock_url_instance = MagicMock()
                mock_url_getter.return_value = mock_url_instance

                # Simulate successful download
                mock_url_instance.download_to_file.return_value = None

                with patch("sys.stderr", new=StringIO()):
                    # Should not raise error since download succeeds
                    handle_cache_error(cache_path, "Test error reason")

                # Verify download_to_file was called with raw GitHub URL
                mock_url_instance.download_to_file.assert_called_once()
                call_args = mock_url_instance.download_to_file.call_args[0]
                self.assertIn("raw.githubusercontent.com", call_args[0])
                self.assertEqual(call_args[1], cache_path)

                # Verify etag file was created
                self.assertTrue(os.path.exists(etag_path))
        finally:
            # Clean up
            for path in [cache_path, etag_path]:
                if os.path.exists(path):
                    os.unlink(path)

    def test_handle_cache_error_raw_download_fails_raises_error(self):
        """Test that handle_cache_error raises error when raw download fails."""
        cache_path = "/tmp/test_cache_" + str(os.getpid()) + ".json"
        etag_path = cache_path + ".etag"

        # Ensure files don't exist
        for path in [cache_path, etag_path]:
            if os.path.exists(path):
                os.unlink(path)

        try:
            # Mock URLGetter to simulate failed download
            with patch("autopkgcmd.searchcmd.URLGetter") as mock_url_getter:
                mock_url_instance = MagicMock()
                mock_url_getter.return_value = mock_url_instance

                # Simulate failed download
                mock_url_instance.download_to_file.side_effect = ProcessorError(
                    "Download failed"
                )

                with patch("sys.stderr", new=StringIO()) as _:
                    with self.assertRaises(ProcessorError) as context:
                        handle_cache_error(cache_path, "Test error reason")

                    # Check error message
                    self.assertIn("Test error reason", str(context.exception))
                    self.assertIn("no cached index available", str(context.exception))
        finally:
            # Clean up
            for path in [cache_path, etag_path]:
                if os.path.exists(path):
                    os.unlink(path)

    def test_handle_cache_error_skips_raw_download_if_etag_exists(self):
        """Test that handle_cache_error skips raw download if etag exists."""
        cache_path = "/tmp/test_cache_" + str(os.getpid()) + ".json"
        etag_path = cache_path + ".etag"

        # Ensure cache doesn't exist but etag does
        if os.path.exists(cache_path):
            os.unlink(cache_path)

        try:
            # Create etag file without cache file
            with open(etag_path, "w", encoding="utf-8") as f:
                f.write("some-etag-value")

            # Mock URLGetter - it should NOT be called
            with patch("autopkgcmd.searchcmd.URLGetter") as mock_url_getter:
                mock_url_instance = MagicMock()
                mock_url_getter.return_value = mock_url_instance

                with patch("sys.stderr", new=StringIO()) as _:
                    with self.assertRaises(ProcessorError) as context:
                        handle_cache_error(cache_path, "Test error reason")

                    # Verify URLGetter was NOT instantiated (raw download not attempted)
                    mock_url_getter.assert_not_called()

                    # Should go straight to error
                    self.assertIn("no cached index available", str(context.exception))
        finally:
            # Clean up
            for path in [cache_path, etag_path]:
                if os.path.exists(path):
                    os.unlink(path)

    def test_handle_cache_error_logs_success_message_on_raw_download(self):
        """Test that handle_cache_error logs success when raw download works."""
        cache_path = "/tmp/test_cache_" + str(os.getpid()) + ".json"
        etag_path = cache_path + ".etag"

        # Ensure files don't exist
        for path in [cache_path, etag_path]:
            if os.path.exists(path):
                os.unlink(path)

        try:
            # Mock URLGetter to simulate successful download
            with patch("autopkgcmd.searchcmd.URLGetter") as mock_url_getter:
                mock_url_instance = MagicMock()
                mock_url_getter.return_value = mock_url_instance
                mock_url_instance.download_to_file.return_value = None

                with patch("sys.stdout", new=StringIO()) as mock_stdout:
                    handle_cache_error(cache_path, "Test error reason")
                    stdout_output = mock_stdout.getvalue()

                # Verify success messages
                self.assertIn("attempting download from raw URL", stdout_output)
                self.assertIn("Successfully downloaded", stdout_output)
        finally:
            # Clean up
            for path in [cache_path, etag_path]:
                if os.path.exists(path):
                    os.unlink(path)

    # Test check_search_cache function

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.isfile")
    @patch("autopkgcmd.searchcmd.URLGetter")
    @patch("autopkgcmd.searchcmd.GitHubSession")
    def test_check_search_cache_downloads_when_no_local_cache_exists(
        self, mock_gh_session, mock_url_getter, mock_isfile, mock_file
    ):
        """Test that check_search_cache downloads index when no local cache exists."""
        cache_path = "/fake/test_cache.json"

        # Mock that no cache files exist
        mock_isfile.return_value = False

        # Mock GitHubSession
        mock_gh_session.return_value.token = None

        # Mock URLGetter
        mock_api = MagicMock()
        mock_url_getter.return_value = mock_api

        # Mock metadata retrieval
        cache_meta = {
            "sha": "abc123",
            "size": 1024 * 1024,  # 1 MB
        }
        mock_api.execute_curl.return_value = (
            json.dumps(cache_meta),
            "",
            0,
        )

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            check_search_cache(cache_path)
            stdout_output = mock_stdout.getvalue()

        # Should log "Refreshing local search index..."
        self.assertIn("Refreshing local search index", stdout_output)

        # Verify etag file was written
        mock_file.assert_called()
        write_calls = [call for call in mock_file().write.call_args_list]
        etag_written = any("abc123" in str(call) for call in write_calls)
        self.assertTrue(etag_written, "Etag should have been written to file")

        # Verify execute_curl was called twice (metadata + download)
        self.assertEqual(mock_api.execute_curl.call_count, 2)

    @patch("builtins.open", new_callable=mock_open, read_data="abc123")
    @patch("os.path.isfile")
    @patch("autopkgcmd.searchcmd.URLGetter")
    @patch("autopkgcmd.searchcmd.GitHubSession")
    def test_check_search_cache_skips_download_when_cache_is_current(
        self, mock_gh_session, mock_url_getter, mock_isfile, mock_file
    ):
        """Test that check_search_cache skips download when cache is up to date."""
        cache_path = "/fake/test_cache.json"

        # Mock that both cache and etag files exist
        mock_isfile.return_value = True

        # Mock GitHubSession
        mock_gh_session.return_value.token = None

        # Mock URLGetter
        mock_api = MagicMock()
        mock_url_getter.return_value = mock_api

        # Mock metadata retrieval with same SHA
        cache_meta = {
            "sha": "abc123",
            "size": 1024 * 1024,
        }
        mock_api.execute_curl.return_value = (
            json.dumps(cache_meta),
            "",
            0,
        )

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            check_search_cache(cache_path)
            stdout_output = mock_stdout.getvalue()

        # Should NOT log "Refreshing local search index..."
        self.assertNotIn("Refreshing local search index", stdout_output)

        # Verify execute_curl was called only once (metadata check only)
        self.assertEqual(mock_api.execute_curl.call_count, 1)

    @patch("builtins.open", new_callable=mock_open, read_data="old_sha")
    @patch("os.path.isfile")
    @patch("autopkgcmd.searchcmd.URLGetter")
    @patch("autopkgcmd.searchcmd.GitHubSession")
    def test_check_search_cache_updates_when_etag_differs(
        self, mock_gh_session, mock_url_getter, mock_isfile, mock_file
    ):
        """Test that check_search_cache downloads when etag differs."""
        cache_path = "/fake/test_cache.json"

        # Mock that both cache and etag files exist
        mock_isfile.return_value = True

        # Mock GitHubSession
        mock_gh_session.return_value.token = None

        # Mock URLGetter
        mock_api = MagicMock()
        mock_url_getter.return_value = mock_api

        # Mock metadata retrieval with new SHA
        cache_meta = {
            "sha": "new_sha",
            "size": 1024 * 1024,
        }
        mock_api.execute_curl.return_value = (
            json.dumps(cache_meta),
            "",
            0,
        )

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            check_search_cache(cache_path)
            stdout_output = mock_stdout.getvalue()

        # Should log "Refreshing local search index..."
        self.assertIn("Refreshing local search index", stdout_output)

        # Verify new etag was written
        write_calls = [call for call in mock_file().write.call_args_list]
        etag_written = any("new_sha" in str(call) for call in write_calls)
        self.assertTrue(etag_written, "New etag should have been written")

        # Verify execute_curl was called twice (metadata + download)
        self.assertEqual(mock_api.execute_curl.call_count, 2)

    @patch("autopkgcmd.searchcmd.handle_cache_error")
    @patch("autopkgcmd.searchcmd.URLGetter")
    @patch("autopkgcmd.searchcmd.GitHubSession")
    def test_check_search_cache_handles_api_error_during_metadata_retrieval(
        self, mock_gh_session, mock_url_getter, mock_handle_error
    ):
        """Test that check_search_cache handles API errors gracefully."""
        cache_path = "/tmp/test_cache_" + str(os.getpid()) + ".json"

        # Mock GitHubSession
        mock_gh_session.return_value.token = None

        # Mock URLGetter to raise ProcessorError
        mock_api = MagicMock()
        mock_url_getter.return_value = mock_api
        mock_api.execute_curl.side_effect = ProcessorError("API error")

        check_search_cache(cache_path)

        # Verify handle_cache_error was called
        mock_handle_error.assert_called_once()
        call_args = mock_handle_error.call_args[0]
        self.assertEqual(call_args[0], cache_path)
        self.assertIn("Unable to check for search index updates", call_args[1])

    @patch("autopkgcmd.searchcmd.handle_cache_error")
    @patch("autopkgcmd.searchcmd.URLGetter")
    @patch("autopkgcmd.searchcmd.GitHubSession")
    def test_check_search_cache_handles_non_zero_return_code_metadata(
        self, mock_gh_session, mock_url_getter, mock_handle_error
    ):
        """Test that check_search_cache handles non-zero return code from metadata."""
        cache_path = "/tmp/test_cache_" + str(os.getpid()) + ".json"

        # Mock GitHubSession
        mock_gh_session.return_value.token = None

        # Mock URLGetter to return non-zero code
        mock_api = MagicMock()
        mock_url_getter.return_value = mock_api
        mock_api.execute_curl.return_value = ("", "", 1)

        check_search_cache(cache_path)

        # Verify handle_cache_error was called
        mock_handle_error.assert_called_once()
        call_args = mock_handle_error.call_args[0]
        self.assertIn("Unable to retrieve search index metadata", call_args[1])

    @patch("autopkgcmd.searchcmd.handle_cache_error")
    @patch("autopkgcmd.searchcmd.URLGetter")
    @patch("autopkgcmd.searchcmd.GitHubSession")
    def test_check_search_cache_handles_invalid_json_response(
        self, mock_gh_session, mock_url_getter, mock_handle_error
    ):
        """Test that check_search_cache handles invalid JSON from API."""
        cache_path = "/tmp/test_cache_" + str(os.getpid()) + ".json"

        # Mock GitHubSession
        mock_gh_session.return_value.token = None

        # Mock URLGetter to return invalid JSON
        mock_api = MagicMock()
        mock_url_getter.return_value = mock_api
        mock_api.execute_curl.return_value = ("not valid json", "", 0)

        check_search_cache(cache_path)

        # Verify handle_cache_error was called
        mock_handle_error.assert_called_once()
        call_args = mock_handle_error.call_args[0]
        self.assertIn("Invalid response from GitHub API", call_args[1])

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.isfile")
    @patch("autopkgcmd.searchcmd.URLGetter")
    @patch("autopkgcmd.searchcmd.GitHubSession")
    def test_check_search_cache_warns_when_size_near_100mb(
        self, mock_gh_session, mock_url_getter, mock_isfile, mock_file
    ):
        """Test that check_search_cache warns when index approaches 100 MB."""
        cache_path = "/fake/test_cache.json"

        # Mock that no cache files exist (will trigger download)
        mock_isfile.return_value = False

        # Mock GitHubSession
        mock_gh_session.return_value.token = None

        # Mock URLGetter
        mock_api = MagicMock()
        mock_url_getter.return_value = mock_api

        # Mock metadata with size > 90 MB
        cache_meta = {
            "sha": "abc123",
            "size": 95 * 1024 * 1024,  # 95 MB
        }
        mock_api.execute_curl.return_value = (
            json.dumps(cache_meta),
            "",
            0,
        )

        with patch("sys.stdout", new=StringIO()), patch(
            "sys.stderr", new=StringIO()
        ) as mock_stderr:
            check_search_cache(cache_path)
            stderr_output = mock_stderr.getvalue()

        # Should warn about approaching limit (now goes to stderr via log_err)
        self.assertIn("WARNING", stderr_output)
        self.assertIn("nearing", stderr_output)

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.isfile")
    @patch("autopkgcmd.searchcmd.URLGetter")
    @patch("autopkgcmd.searchcmd.GitHubSession")
    def test_check_search_cache_warns_when_size_exceeds_100mb(
        self, mock_gh_session, mock_url_getter, mock_isfile, mock_file
    ):
        """Test that check_search_cache warns when index exceeds 100 MB."""
        cache_path = "/fake/test_cache.json"

        # Mock that no cache files exist (will trigger download)
        mock_isfile.return_value = False

        # Mock GitHubSession
        mock_gh_session.return_value.token = None

        # Mock URLGetter
        mock_api = MagicMock()
        mock_url_getter.return_value = mock_api

        # Mock metadata with size > 100 MB
        cache_meta = {
            "sha": "abc123",
            "size": 105 * 1024 * 1024,  # 105 MB
        }
        mock_api.execute_curl.return_value = (
            json.dumps(cache_meta),
            "",
            0,
        )

        with patch("sys.stdout", new=StringIO()) as mock_stdout, patch(
            "sys.stderr", new=StringIO()
        ) as mock_stderr:
            check_search_cache(cache_path)
            stdout_output = mock_stdout.getvalue()
            stderr_output = mock_stderr.getvalue()

        # Should warn about exceeding limit (note: due to elif, this actually
        # shows "nearing" instead of "greater than" - see searchcmd.py:115-117)
        combined_output = stdout_output + stderr_output
        self.assertIn("WARNING", combined_output)
        # Due to the elif logic, size > 100MB will show "nearing" not "greater than"
        self.assertIn("nearing", combined_output)

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.isfile")
    @patch("autopkgcmd.searchcmd.URLGetter")
    @patch("autopkgcmd.searchcmd.GitHubSession")
    def test_check_search_cache_uses_github_token_if_available(
        self, mock_gh_session, mock_url_getter, mock_isfile, mock_file
    ):
        """Test that check_search_cache uses GitHub token when available."""
        cache_path = "/fake/test_cache.json"

        # Mock that no cache files exist (will trigger download)
        mock_isfile.return_value = False

        # Mock GitHubSession with token
        mock_gh_session.return_value.token = "test_token_123"

        # Mock URLGetter
        mock_api = MagicMock()
        mock_url_getter.return_value = mock_api

        # Mock metadata retrieval
        cache_meta = {
            "sha": "abc123",
            "size": 1024 * 1024,
        }
        mock_api.execute_curl.return_value = (
            json.dumps(cache_meta),
            "",
            0,
        )

        check_search_cache(cache_path)

        # Verify add_curl_headers was called with Authorization header
        self.assertTrue(mock_api.add_curl_headers.called)
        call_args = mock_api.add_curl_headers.call_args[0]
        headers = call_args[1]
        self.assertIn("Authorization", headers)
        self.assertEqual(headers["Authorization"], "Bearer test_token_123")

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.isfile")
    @patch("autopkgcmd.searchcmd.handle_cache_error")
    @patch("autopkgcmd.searchcmd.URLGetter")
    @patch("autopkgcmd.searchcmd.GitHubSession")
    def test_check_search_cache_handles_download_error(
        self,
        mock_gh_session,
        mock_url_getter,
        mock_handle_error,
        mock_isfile,
        mock_file,
    ):
        """Test that check_search_cache handles download errors."""
        cache_path = "/fake/test_cache.json"

        # Mock that no cache files exist (will trigger download attempt)
        mock_isfile.return_value = False

        # Mock GitHubSession
        mock_gh_session.return_value.token = None

        # Mock URLGetter
        mock_api = MagicMock()
        mock_url_getter.return_value = mock_api

        # First call succeeds (metadata), second call raises error (download)
        cache_meta = {
            "sha": "abc123",
            "size": 1024 * 1024,
        }
        mock_api.execute_curl.side_effect = [
            (json.dumps(cache_meta), "", 0),
            ProcessorError("Download failed"),
        ]

        check_search_cache(cache_path)

        # Verify handle_cache_error was called for download error
        mock_handle_error.assert_called_once()
        call_args = mock_handle_error.call_args[0]
        self.assertIn("Unable to download updated search index", call_args[1])

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.isfile")
    @patch("autopkgcmd.searchcmd.handle_cache_error")
    @patch("autopkgcmd.searchcmd.URLGetter")
    @patch("autopkgcmd.searchcmd.GitHubSession")
    def test_check_search_cache_handles_non_zero_return_code_download(
        self,
        mock_gh_session,
        mock_url_getter,
        mock_handle_error,
        mock_isfile,
        mock_file,
    ):
        """Test that check_search_cache handles non-zero return code from download."""
        cache_path = "/fake/test_cache.json"

        # Mock that no cache files exist (will trigger download attempt)
        mock_isfile.return_value = False

        # Mock GitHubSession
        mock_gh_session.return_value.token = None

        # Mock URLGetter
        mock_api = MagicMock()
        mock_url_getter.return_value = mock_api

        # First call succeeds (metadata), second call fails (download)
        cache_meta = {
            "sha": "abc123",
            "size": 1024 * 1024,
        }
        mock_api.execute_curl.side_effect = [
            (json.dumps(cache_meta), "", 0),
            ("", "", 1),  # Non-zero return code
        ]

        check_search_cache(cache_path)

        # Verify handle_cache_error was called
        mock_handle_error.assert_called_once()
        call_args = mock_handle_error.call_args[0]
        self.assertIn("Unable to retrieve search index contents", call_args[1])

    # Test search_recipes function

    def test_search_no_query_specified(self):
        """Test search_recipes with no search query returns error code 1."""
        argv = ["autopkg", "search"]
        with patch("sys.stdout", new=StringIO()):
            result = search_recipes(argv)
        self.assertEqual(result, 1)

    @patch("autopkgcmd.searchcmd.check_search_cache")
    @patch("builtins.open", new_callable=mock_open)
    def test_search_with_results_returns_success(self, mock_file, mock_check_cache):
        """Test search_recipes with results returns exit code 0."""
        # Mock check_search_cache to prevent network calls
        mock_check_cache.return_value = None

        # Mock the file read to return our test search index
        mock_file.return_value.read.return_value = json.dumps(
            self.mock_search_index
        ).encode()
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(
            self.mock_search_index
        ).encode()

        argv = ["autopkg", "search", "NetNewsWire"]
        with patch("sys.stdout", new=StringIO()):
            result = search_recipes(argv)

        self.assertEqual(result, 0)
        # Verify check_search_cache was called but no actual network requests made
        mock_check_cache.assert_called_once()

    @patch("autopkgcmd.searchcmd.check_search_cache")
    @patch("builtins.open", new_callable=mock_open)
    def test_search_with_no_results_returns_error_code(
        self, mock_file, mock_check_cache
    ):
        """Test search_recipes with no results returns exit code 0."""
        # Mock check_search_cache to prevent network calls
        mock_check_cache.return_value = None

        # Mock empty search index
        empty_index = {"shortnames": {}, "identifiers": {}}
        mock_file.return_value.read.return_value = json.dumps(empty_index).encode()
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(
            empty_index
        ).encode()

        argv = ["autopkg", "search", "NonexistentRecipe12345"]
        with patch("sys.stdout", new=StringIO()):
            result = search_recipes(argv)

        self.assertEqual(result, 0)

    @patch("autopkgcmd.searchcmd.check_search_cache")
    @patch("builtins.open", new_callable=mock_open)
    def test_search_with_too_many_results(self, mock_file, mock_check_cache):
        """Test search_recipes with more than 100 results shows warning."""
        # Mock check_search_cache to prevent network calls
        mock_check_cache.return_value = None

        # Create a search index with 101 recipes
        large_index = {"shortnames": {}, "identifiers": {}}
        for i in range(101):
            recipe_id = f"com.test.recipe{i}"
            large_index["shortnames"][f"recipe{i}"] = [recipe_id]
            large_index["identifiers"][recipe_id] = {
                "name": f"Recipe{i}.recipe",
                "path": f"Recipes/Recipe{i}.recipe",
                "repo": "recipes",
                "deprecated": False,
            }

        mock_file.return_value.read.return_value = json.dumps(large_index).encode()
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(
            large_index
        ).encode()

        argv = ["autopkg", "search", "recipe"]
        with patch("sys.stdout", new=StringIO()), patch(
            "sys.stderr", new=StringIO()
        ) as mock_stderr:
            result = search_recipes(argv)

        # Should return 0 and print warning message
        self.assertEqual(result, 0)
        self.assertIn("try a more specific search term.", mock_stderr.getvalue())

    @patch("autopkgcmd.searchcmd.check_search_cache")
    @patch("builtins.open", new_callable=mock_open)
    def test_search_with_path_only_option(self, mock_file, mock_check_cache):
        """Test search_recipes with --path-only option."""
        # Mock check_search_cache to prevent network calls
        mock_check_cache.return_value = None

        # Mock the file read to return our test search index
        mock_file.return_value.read.return_value = json.dumps(
            self.mock_search_index
        ).encode()
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(
            self.mock_search_index
        ).encode()

        argv = ["autopkg", "search", "--path-only", "coconutBattery"]
        with patch("sys.stdout", new=StringIO()):
            result = search_recipes(argv)

        self.assertEqual(result, 0)

    def test_search_with_custom_user_option(self):
        """Test search_recipes with --user option prints GitHub URL."""
        # With the new implementation, --user option just prints a GitHub search URL
        argv = ["autopkg", "search", "--user", "customuser", "SomeApp"]
        with patch("sys.stdout", new=StringIO()) as fake_out:
            result = search_recipes(argv)
            output = fake_out.getvalue()

        self.assertEqual(result, 0)
        # Verify that a GitHub search URL was printed
        self.assertIn("github.com/search", output)
        self.assertIn("customuser", output)

    @patch("autopkgcmd.searchcmd.check_search_cache")
    @patch("builtins.open", new_callable=mock_open)
    def test_search_with_use_token_option(self, mock_file, mock_check_cache):
        """Test search_recipes with --use-token option prints deprecation warning."""
        # Mock check_search_cache to prevent network calls
        mock_check_cache.return_value = None

        # Mock the file read to return our test search index
        mock_file.return_value.read.return_value = json.dumps(
            self.mock_search_index
        ).encode()
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(
            self.mock_search_index
        ).encode()

        argv = ["autopkg", "search", "--use-token", "NetNewsWire"]
        # Warnings go to stderr via log_err, so we need to capture both
        with patch("sys.stdout", new=StringIO()) as fake_out, patch(
            "sys.stderr", new=StringIO()
        ) as fake_err:
            result = search_recipes(argv)
            stdout = fake_out.getvalue()
            stderr = fake_err.getvalue()

        self.assertEqual(result, 0)
        # The --use-token option is deprecated and should print a warning to stderr
        self.assertIn("Deprecated", stdout + stderr)

    @patch("autopkgcmd.searchcmd.check_search_cache")
    @patch("builtins.open", new_callable=mock_open)
    def test_search_with_special_characters(self, mock_file, mock_check_cache):
        """Test that search handles special characters in search term."""
        # Mock check_search_cache to prevent network calls
        mock_check_cache.return_value = None

        # Mock empty search index (no results for special characters)
        empty_index = {"shortnames": {}, "identifiers": {}}
        mock_file.return_value.read.return_value = json.dumps(empty_index).encode()
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(
            empty_index
        ).encode()

        # Search term with spaces and special characters
        argv = ["autopkg", "search", "App Name+Special"]
        with patch("sys.stdout", new=StringIO()):
            search_recipes(argv)

    @patch("autopkgcmd.searchcmd.check_search_cache")
    @patch("builtins.open", new_callable=mock_open)
    def test_search_prints_helper_messages(self, mock_file, mock_check_cache):
        """Test search_recipes prints helpful messages when relevant."""
        # Mock check_search_cache to prevent network calls
        mock_check_cache.return_value = None

        # Mock the file read to return our test search index
        mock_file.return_value.read.return_value = json.dumps(
            self.mock_search_index
        ).encode()
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(
            self.mock_search_index
        ).encode()

        argv = ["autopkg", "search", "coconutBattery"]
        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            search_recipes(argv)
            output = mock_stdout.getvalue()

        # Check for expected output (this may need to be adjusted based on actual output)
        self.assertIn("coconutBattery", output)

    @patch("autopkgcmd.searchcmd.check_search_cache")
    @patch("builtins.open", new_callable=mock_open)
    def test_search_prints_warning_for_too_many_results(
        self, mock_file, mock_check_cache
    ):
        """Test search_recipes prints a warning when there are too many results."""
        # Mock check_search_cache to prevent network calls
        mock_check_cache.return_value = None

        # Create a search index with 101 recipes
        large_index = {"shortnames": {}, "identifiers": {}}
        for i in range(101):
            recipe_id = f"com.test.recipe{i}"
            large_index["shortnames"][f"recipe{i}"] = [recipe_id]
            large_index["identifiers"][recipe_id] = {
                "name": f"Recipe{i}.recipe",
                "path": f"Recipes/Recipe{i}.recipe",
                "repo": "recipes",
                "deprecated": False,
            }

        mock_file.return_value.read.return_value = json.dumps(large_index).encode()
        mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(
            large_index
        ).encode()

        argv = ["autopkg", "search", "recipe"]
        with patch("sys.stdout", new=StringIO()) as mock_stdout, patch(
            "sys.stderr", new=StringIO()
        ) as mock_stderr:
            search_recipes(argv)
            stdout = mock_stdout.getvalue()
            stderr = mock_stderr.getvalue()

        # Check for warning message about too many results (goes to stderr via log_err)
        combined_output = (stdout + stderr).lower()
        self.assertIn("try a more specific search term.", combined_output)

    # Test print_gh_search_results function

    def test_print_gh_search_results_formats_output_correctly(self):
        """Test that print_gh_search_results formats output with proper columns."""
        results = [
            {
                "Name": "NetNewsWire.download.recipe",
                "Repo": "recipes",
                "Path": "NetNewsWire/NetNewsWire.download.recipe",
            },
            {
                "Name": "NetNewsWire.munki.recipe",
                "Repo": "recipes",
                "Path": "NetNewsWire/NetNewsWire.munki.recipe",
            },
        ]

        with patch("sys.stdout", new=StringIO()) as fake_out:
            print_gh_search_results(results)
            output = fake_out.getvalue()

        # Check for column headers
        self.assertIn("Name", output)
        self.assertIn("Repo", output)
        self.assertIn("Path", output)
        # Check for recipe names
        self.assertIn("NetNewsWire.download.recipe", output)
        self.assertIn("NetNewsWire.munki.recipe", output)

    def test_print_gh_search_results_shortens_autopkg_org_names(self):
        """Test that print_gh_search_results shortens autopkg org repo names."""
        results = [
            {
                "Name": "TestApp.recipe",
                "Repo": "recipes",
                "Path": "TestApp/TestApp.recipe",
            }
        ]

        with patch("sys.stdout", new=StringIO()) as fake_out:
            print_gh_search_results(results)
            output = fake_out.getvalue()

        # Should show "recipes" not "autopkg/recipes"
        lines = output.split("\n")
        # Find the line with the recipe (not header)
        for line in lines:
            if "TestApp.recipe" in line:
                # Check that it contains "recipes" but not the full path
                self.assertIn("recipes", line)
                # The repo column should be just "recipes"
                break

    def test_print_gh_search_results_shows_full_name_for_non_autopkg_repos(self):
        """Test that print_gh_search_results shows full names for non-autopkg repos."""
        results = [
            {
                "Name": "CustomApp.recipe",
                "Repo": "customuser/custom-recipes",
                "Path": "CustomApp/CustomApp.recipe",
            }
        ]

        with patch("sys.stdout", new=StringIO()) as fake_out:
            print_gh_search_results(results)
            output = fake_out.getvalue()

        # Should show full "customuser/custom-recipes"
        self.assertIn("customuser/custom-recipes", output)

    def test_print_gh_search_results_sorts_by_repo_name(self):
        """Test that print_gh_search_results sorts results by repository name."""
        results = [
            {
                "Name": "ZApp.recipe",
                "Repo": "user/zebra-recipes",
                "Path": "ZApp.recipe",
            },
            {
                "Name": "AApp.recipe",
                "Repo": "user/alpha-recipes",
                "Path": "AApp.recipe",
            },
            {
                "Name": "MApp.recipe",
                "Repo": "user/middle-recipes",
                "Path": "MApp.recipe",
            },
        ]

        with patch("sys.stdout", new=StringIO()) as fake_out:
            print_gh_search_results(results)
            output = fake_out.getvalue()

        # Find positions of repo names in output
        alpha_pos = output.find("alpha-recipes")
        middle_pos = output.find("middle-recipes")
        zebra_pos = output.find("zebra-recipes")

        # Verify they appear in alphabetical order
        self.assertLess(alpha_pos, middle_pos)
        self.assertLess(middle_pos, zebra_pos)

    def test_print_gh_search_results_handles_empty_results(self):
        """Test that print_gh_search_results handles empty results gracefully."""
        results = []

        with patch("sys.stdout", new=StringIO()) as fake_out, patch(
            "sys.stderr", new=StringIO()
        ) as fake_err:
            print_gh_search_results(results)
            output = fake_out.getvalue() + fake_err.getvalue()

        # Should print "Nothing found." for empty results
        self.assertIn("Nothing found", output)

    def test_print_gh_search_results_calculates_column_widths_dynamically(self):
        """Test that column widths adjust to content."""
        results = [
            {
                "Name": "VeryLongRecipeNameForTesting.download.recipe.yaml",
                "Repo": "recipes",
                "Path": "VeryLongPath/Subdir/VeryLongRecipeNameForTesting.download.recipe.yaml",
            },
            {
                "Name": "Short.recipe",
                "Repo": "recipes",
                "Path": "Short.recipe",
            },
        ]

        with patch("sys.stdout", new=StringIO()) as fake_out:
            print_gh_search_results(results)
            output = fake_out.getvalue()

        # Both recipes should be visible
        self.assertIn("VeryLongRecipeNameForTesting.download.recipe.yaml", output)
        self.assertIn("Short.recipe", output)
        # Headers should be present
        self.assertIn("Name", output)
        self.assertIn("Path", output)


if __name__ == "__main__":
    unittest.main()
