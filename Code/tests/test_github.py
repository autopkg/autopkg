#!/usr/local/autopkg/python

import json
import os
import tempfile
import unittest
from io import StringIO
from unittest.mock import patch

from autopkglib.github import GitHubSession, get_github_token


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
            patch("sys.stderr", new=StringIO()) as stderr,
        ):
            self.assertIsNone(get_github_token(token_path))

        self.assertIn("Ignoring malformed GitHub token", stderr.getvalue())
        self.assertIn(token_path, stderr.getvalue())

    def test_get_github_token_ignores_malformed_preference_token(self):
        token_path = self._write_token_file("ghp_filetoken\n")

        with (
            patch("autopkglib.github.get_pref", return_value="ghp_bad token"),
            patch("sys.stderr", new=StringIO()) as stderr,
        ):
            self.assertIsNone(get_github_token(token_path))

        self.assertIn("GITHUB_TOKEN preference", stderr.getvalue())


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
        with patch.object(GitHubSession, "_get_token", return_value=token):
            session = GitHubSession()
        session.curl_binary = lambda: "curl"
        return session

    def test_prepare_curl_cmd_does_not_use_fail(self):
        session = self._session()
        curl_cmd = session.prepare_curl_cmd(
            "GET",
            "application/vnd.github.v3+json",
            None,
            None,
            "/tmp/github-response.json",
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
            patch("sys.stderr", new=StringIO()) as stderr,
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
            patch("sys.stderr", new=StringIO()) as stderr,
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
            patch("sys.stderr", new=StringIO()) as stderr,
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
            patch("sys.stderr", new=StringIO()) as stderr,
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


if __name__ == "__main__":
    unittest.main()
