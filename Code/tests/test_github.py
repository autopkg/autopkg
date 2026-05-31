#!/usr/local/autopkg/python

import os
import tempfile
import unittest
from unittest.mock import patch

from autopkglib.github import get_github_token


class TestGitHubToken(unittest.TestCase):
    """Tests for GitHub token discovery."""

    def _write_token_file(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        token_path = os.path.join(tmpdir.name, ".autopkg_gh_token")
        with open(token_path, "w") as token_file:
            token_file.write("file-token\n")
        return token_path

    def test_get_github_token_prefers_preferences(self):
        token_path = self._write_token_file()
        with patch("autopkglib.github.get_pref", return_value="prefs-token"):
            self.assertEqual(get_github_token(token_path), "prefs-token")

    def test_get_github_token_reads_token_file(self):
        token_path = self._write_token_file()
        with patch("autopkglib.github.get_pref", return_value=None):
            self.assertEqual(get_github_token(token_path), "file-token")


if __name__ == "__main__":
    unittest.main()
