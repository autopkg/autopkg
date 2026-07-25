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

import json
import os
import tempfile
import unittest
from io import BytesIO, StringIO
from unittest.mock import MagicMock, mock_open, patch

import autopkglib.github as github
from autopkglib.github import GitHubSession, _sanitize_github_token, get_github_token


class TestGitHubToken(unittest.TestCase):
    """Tests for GitHub token discovery."""

    def _write_token_file(self, token="ghp_filetoken\n"):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        token_path = os.path.join(tmpdir.name, ".autopkg_gh_token")
        with open(token_path, "w") as token_file:
            token_file.write(token)
        return token_path

    def test_get_github_token_prefers_preferences(self):
        token_path = self._write_token_file()
        with patch("autopkglib.github.get_pref", return_value="ghp_prefstoken"):
            self.assertEqual(get_github_token(token_path), "ghp_prefstoken")

    def test_get_github_token_reads_token_file(self):
        token_path = self._write_token_file()
        with patch("autopkglib.github.get_pref", return_value=None):
            self.assertEqual(get_github_token(token_path), "ghp_filetoken")

    def test_get_github_token_strips_preferences_token(self):
        with patch("autopkglib.github.get_pref", return_value="  ghp_prefstoken  "):
            self.assertEqual(get_github_token("/missing/token"), "ghp_prefstoken")

    def test_get_github_token_ignores_malformed_file_token(self):
        token_path = self._write_token_file("ghp_bad token\n")

        with (
            patch("autopkglib.github.get_pref", return_value=None),
            patch("sys.stderr", new_callable=StringIO) as stderr,
        ):
            self.assertIsNone(get_github_token(token_path))

        self.assertIn("Ignoring malformed GitHub token", stderr.getvalue())
        self.assertIn(token_path, stderr.getvalue())

    def test_get_github_token_ignores_malformed_preference_token(self):
        token_path = self._write_token_file("ghp_filetoken\n")

        with (
            patch("autopkglib.github.get_pref", return_value="ghp_bad token"),
            patch("sys.stderr", new_callable=StringIO) as stderr,
        ):
            self.assertIsNone(get_github_token(token_path))

        self.assertIn("GITHUB_TOKEN preference", stderr.getvalue())

    def test_sanitize_github_token_returns_none_for_none_input(self):
        with patch("autopkglib.github.log_err") as log_err:
            self.assertIsNone(_sanitize_github_token(None, "source"))

        log_err.assert_not_called()

    def test_sanitize_github_token_returns_empty_string_as_none(self):
        with patch("autopkglib.github.log_err") as log_err:
            self.assertIsNone(_sanitize_github_token("", "source"))

        log_err.assert_called_once()
        self.assertIn("Ignoring malformed", log_err.call_args.args[0])

    def test_sanitize_github_token_strips_whitespace(self):
        self.assertEqual(_sanitize_github_token("  ghp_valid  ", "source"), "ghp_valid")

    def test_get_github_token_handles_file_read_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            token_path = os.path.join(tmpdir, ".autopkg_gh_token")
            with open(token_path, "w") as token_file:
                token_file.write("ghp_filetoken")

            with (
                patch("autopkglib.github.get_pref", return_value=None),
                patch("builtins.open", side_effect=OSError("permission denied")),
                patch("autopkglib.github.log_err") as log_err,
            ):
                self.assertIsNone(get_github_token(token_path))

        log_err.assert_called_once()
        self.assertIn("Couldn't read token file", log_err.call_args.args[0])


class TestGitHubSession(unittest.TestCase):
    """Tests for GitHub API request handling."""

    def _execute_curl_side_effect(self, responses, curl_cmds):
        def _execute_curl(curl_cmd):
            curl_cmds.append(curl_cmd)
            output_path = curl_cmd[curl_cmd.index("--output") + 1]
            response = responses.pop(0)
            with open(output_path, "w") as response_file:
                json.dump(response["body"], response_file)
            return response["headers"], "", 0

        return _execute_curl

    def _session(self, token=None):
        with patch("autopkglib.github.get_github_token", return_value=token):
            session = GitHubSession()
        session.curl_binary = lambda: "curl"
        return session

    def _named_temp_file_mock(self, path="github-response.json"):
        temp_file = MagicMock()
        temp_file.name = path
        return temp_file

    def test_prepare_curl_cmd_does_not_use_fail(self):
        session = self._session()
        curl_cmd = session.prepare_curl_cmd(
            "GET",
            "application/vnd.github.v3+json",
            None,
            None,
            "github-response.json",
        )

        self.assertNotIn("--fail", curl_cmd)

    def test_call_api_retries_get_without_auth_after_401(self):
        session = self._session(token="ghp_badtoken")
        responses = [
            {
                "headers": "HTTP/2 401 Unauthorized\n\n",
                "body": {"message": "Bad credentials"},
            },
            {
                "headers": "HTTP/2 200 OK\n\n",
                "body": {"name": "recipes"},
            },
        ]
        curl_cmds = []

        with (
            patch.object(
                session,
                "execute_curl",
                side_effect=self._execute_curl_side_effect(responses, curl_cmds),
            ),
            patch("sys.stderr", new_callable=StringIO) as stderr,
        ):
            data, status = session.call_api("/repos/autopkg/recipes")

        self.assertEqual(status, 200)
        self.assertEqual(data, {"name": "recipes"})
        self.assertEqual(len(curl_cmds), 2)
        self.assertIn("Authorization: token ghp_badtoken", curl_cmds[0])
        self.assertNotIn("Authorization: token ghp_badtoken", curl_cmds[1])
        self.assertIn("invalid or expired", stderr.getvalue())
        self.assertIn("Continuing without it", stderr.getvalue())

    def test_call_api_returns_anonymous_retry_failure(self):
        session = self._session(token="ghp_badtoken")
        responses = [
            {
                "headers": "HTTP/2 401 Unauthorized\n\n",
                "body": {"message": "Bad credentials"},
            },
            {
                "headers": "HTTP/2 404 Not Found\n\n",
                "body": {"message": "Not Found"},
            },
        ]
        curl_cmds = []

        with (
            patch.object(
                session,
                "execute_curl",
                side_effect=self._execute_curl_side_effect(responses, curl_cmds),
            ),
            patch("sys.stderr", new_callable=StringIO) as stderr,
        ):
            data, status = session.call_api("/repos/autopkg/private-recipes")

        self.assertEqual(status, 404)
        self.assertEqual(data, {"message": "Not Found"})
        self.assertEqual(len(curl_cmds), 2)
        self.assertIn("Authorization: token ghp_badtoken", curl_cmds[0])
        self.assertNotIn("Authorization: token ghp_badtoken", curl_cmds[1])
        self.assertIn("Continuing without it", stderr.getvalue())

    def test_call_api_does_not_retry_403(self):
        session = self._session(token="ghp_goodtoken")
        responses = [
            {
                "headers": "HTTP/2 403 Forbidden\n\n",
                "body": {"message": "API rate limit exceeded"},
            }
        ]
        curl_cmds = []

        with (
            patch.object(
                session,
                "execute_curl",
                side_effect=self._execute_curl_side_effect(responses, curl_cmds),
            ),
            patch("sys.stderr", new_callable=StringIO) as stderr,
        ):
            data, status = session.call_api("/repos/autopkg/recipes")

        self.assertEqual(status, 403)
        self.assertEqual(data, {"message": "API rate limit exceeded"})
        self.assertEqual(len(curl_cmds), 1)
        self.assertIn("Authorization: token ghp_goodtoken", curl_cmds[0])
        self.assertNotIn("invalid or expired", stderr.getvalue())

    def test_call_api_does_not_retry_non_get_401(self):
        session = self._session(token="ghp_badtoken")
        responses = [
            {
                "headers": "HTTP/2 401 Unauthorized\n\n",
                "body": {"message": "Bad credentials"},
            }
        ]
        curl_cmds = []

        with (
            patch.object(
                session,
                "execute_curl",
                side_effect=self._execute_curl_side_effect(responses, curl_cmds),
            ),
            patch("sys.stderr", new_callable=StringIO) as stderr,
        ):
            data, status = session.call_api(
                "/repos/autopkg/recipes", method="POST", data={"name": "recipes"}
            )

        self.assertEqual(status, 401)
        self.assertEqual(data, {"message": "Bad credentials"})
        self.assertEqual(len(curl_cmds), 1)
        self.assertIn("Authorization: token ghp_badtoken", curl_cmds[0])
        self.assertIn("invalid or expired", stderr.getvalue())
        self.assertNotIn("Continuing without it", stderr.getvalue())

    def test_get_or_setup_token_uses_existing_token(self):
        session = self._session()

        with (
            patch("autopkglib.github.get_github_token", return_value="ghp_existing"),
            patch("builtins.input") as input_mock,
        ):
            token = session.get_or_setup_token()

        self.assertEqual(token, "ghp_existing")
        self.assertEqual(session.token, "ghp_existing")
        input_mock.assert_not_called()

    def test_get_or_setup_token_prompts_when_no_token_and_file_missing(self):
        session = self._session()
        file_mock = mock_open()

        with (
            patch("autopkglib.github.get_github_token", return_value=None),
            patch("autopkglib.github.os.path.exists", return_value=False),
            patch("builtins.input", return_value="ghp_prompttoken"),
            patch("builtins.open", file_mock),
            patch("autopkglib.github.os.chmod") as chmod,
            patch("builtins.print"),
        ):
            token = session.get_or_setup_token()

        self.assertEqual(token, "ghp_prompttoken")
        self.assertEqual(session.token, "ghp_prompttoken")
        file_mock.assert_called_once_with(github.TOKEN_LOCATION, "w")
        file_mock().write.assert_called_once_with("ghp_prompttoken")
        chmod.assert_called_once_with(github.TOKEN_LOCATION, 0o600)

    def test_get_or_setup_token_skips_creation_on_empty_input(self):
        session = self._session()

        with (
            patch("autopkglib.github.get_github_token", return_value=None),
            patch("autopkglib.github.os.path.exists", return_value=False),
            patch("builtins.input", return_value=""),
            patch("autopkglib.github.log") as log_mock,
            patch("builtins.print"),
        ):
            token = session.get_or_setup_token()

        self.assertIsNone(token or None)
        self.assertIsNone(session.token or None)
        log_mock.assert_called_once_with("Skipping token file creation.")

    def test_get_or_setup_token_handles_file_write_error(self):
        session = self._session()

        with (
            patch("autopkglib.github.get_github_token", return_value=None),
            patch("autopkglib.github.os.path.exists", return_value=False),
            patch("builtins.input", return_value="ghp_token"),
            patch("builtins.open", side_effect=OSError("permission denied")),
            patch("autopkglib.github.os.chmod") as chmod,
            patch("autopkglib.github.log_err") as log_err,
            patch("builtins.print"),
        ):
            token = session.get_or_setup_token()

        self.assertEqual(token, "ghp_token")
        chmod.assert_not_called()
        log_err.assert_called_once()
        self.assertIn("Couldn't write token file", log_err.call_args.args[0])

    def test_prepare_curl_cmd_includes_custom_headers(self):
        session = self._session()
        session.env["url"] = "https://api.github.com/repos"

        curl_cmd = session.prepare_curl_cmd(
            "GET",
            "application/vnd.github.v3+json",
            {"X-Custom": "value"},
            None,
            "github-response.json",
        )

        self.assertIn("--header", curl_cmd)
        self.assertIn("X-Custom: value", curl_cmd)

    def test_call_api_appends_query_string(self):
        session = self._session()

        with patch.object(session, "_call_api_once", return_value=({}, 200)):
            session.call_api("/repos", query="page=2")

        self.assertTrue(session.env["url"].endswith("?page=2"))

    def test_call_api_does_not_append_empty_query(self):
        session = self._session()

        with patch.object(session, "_call_api_once", return_value=({}, 200)):
            session.call_api("/repos", query=None)

        self.assertNotIn("?", session.env["url"])

    def test_status_code_returns_zero_for_invalid_status(self):
        session = self._session()

        self.assertEqual(session._status_code("invalid"), 0)
        self.assertEqual(session._status_code(None), 0)

    def test_call_api_once_handles_unicode_decode_error(self):
        session = self._session()
        temp_file = self._named_temp_file_mock()

        with (
            patch(
                "autopkglib.github.tempfile.NamedTemporaryFile",
                return_value=temp_file,
            ),
            patch.object(session, "download_with_curl", return_value="HTTP/2 200 OK"),
            patch.object(
                session, "parse_headers", return_value={"http_result_code": "200"}
            ),
            patch(
                "builtins.open",
                side_effect=[
                    UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid"),
                    BytesIO(b'{"ok": true}'),
                ],
            ),
            patch("autopkglib.github.os.unlink") as unlink,
        ):
            resp_data, status = session._call_api_once(
                "GET", "application/vnd.github.v3+json", None, None
            )

        self.assertEqual(resp_data, {"ok": True})
        self.assertEqual(status, 200)
        temp_file.close.assert_called_once()
        unlink.assert_called_once_with(temp_file.name)

    def test_call_api_once_json_decode_error_calls_output(self):
        session = self._session()
        temp_file = self._named_temp_file_mock()

        with (
            patch(
                "autopkglib.github.tempfile.NamedTemporaryFile",
                return_value=temp_file,
            ),
            patch.object(session, "download_with_curl", return_value="HTTP/2 200 OK"),
            patch.object(
                session, "parse_headers", return_value={"http_result_code": "200"}
            ),
            patch(
                "builtins.open",
                side_effect=json.JSONDecodeError("bad json", "{", 0),
            ),
            patch.object(session, "output") as output,
            patch("autopkglib.github.os.unlink"),
        ):
            resp_data, status = session._call_api_once(
                "GET", "application/vnd.github.v3+json", None, None
            )

        self.assertIsNone(resp_data)
        self.assertEqual(status, 200)
        output.assert_called_once()
        self.assertIn("JSONDecodeError:", output.call_args.args[0])

    def test_call_api_once_cleans_up_temp_file_on_oserror(self):
        session = self._session()
        temp_file = self._named_temp_file_mock()

        with (
            patch(
                "autopkglib.github.tempfile.NamedTemporaryFile",
                return_value=temp_file,
            ),
            patch.object(session, "download_with_curl", return_value="HTTP/2 200 OK"),
            patch.object(
                session, "parse_headers", return_value={"http_result_code": "200"}
            ),
            patch("builtins.open", mock_open(read_data='{"ok": true}')),
            patch("autopkglib.github.os.unlink", side_effect=OSError("busy")),
        ):
            resp_data, status = session._call_api_once(
                "GET", "application/vnd.github.v3+json", None, None
            )

        self.assertEqual(resp_data, {"ok": True})
        self.assertEqual(status, 200)

    def test_search_for_name_warns_on_non_default_user(self):
        session = self._session()

        with (
            patch("autopkgcmd.searchcmd.get_search_results", return_value=[]),
            patch("autopkglib.github.log") as log_mock,
        ):
            results = session.search_for_name("recipe", user="other")

        self.assertEqual(results, [])
        log_mock.assert_called_once()
        self.assertIn("WARNING: Searching non-autopkg", log_mock.call_args.args[0])

    def test_search_for_name_warns_on_use_token_flag(self):
        session = self._session()

        with (
            patch("autopkgcmd.searchcmd.get_search_results", return_value=[]),
            patch("autopkglib.github.log") as log_mock,
        ):
            results = session.search_for_name("recipe", use_token=True)

        self.assertEqual(results, [])
        log_mock.assert_called_once()
        self.assertIn("deprecated and no longer needed", log_mock.call_args.args[0])

    def test_search_for_name_returns_empty_list_when_no_results(self):
        session = self._session()

        with patch("autopkgcmd.searchcmd.get_search_results", return_value=[]):
            results = session.search_for_name("nonexistent")

        self.assertEqual(results, [])

    def test_search_for_name_transforms_results_with_autopkg_prefix(self):
        session = self._session()
        search_results = [
            {"Name": "Recipe.rb", "Repo": "recipes", "Path": "recipes/Recipe.rb"}
        ]

        with patch(
            "autopkgcmd.searchcmd.get_search_results", return_value=search_results
        ):
            results = session.search_for_name("Recipe")

        self.assertEqual(results[0]["repository"]["full_name"], "autopkg/recipes")
        self.assertIn("github.com/autopkg/recipes", results[0]["html_url"])

    def test_search_for_name_preserves_full_repo_name(self):
        session = self._session()
        search_results = [
            {"Name": "Recipe.rb", "Repo": "org/recipes", "Path": "recipes/Recipe.rb"}
        ]

        with patch(
            "autopkgcmd.searchcmd.get_search_results", return_value=search_results
        ):
            results = session.search_for_name("Recipe")

        self.assertEqual(results[0]["repository"]["full_name"], "org/recipes")


if __name__ == "__main__":
    unittest.main()
