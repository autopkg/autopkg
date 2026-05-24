#!/usr/local/autopkg/python

import unittest
from unittest.mock import patch

from autopkglib import ProcessorError
from autopkglib.GitHubReleasesInfoProvider import GitHubReleasesInfoProvider


def _fake_release(tag_name="v3.0.2"):
    """Build a minimal GitHub release list for one tag."""
    return [
        {
            "tag_name": tag_name,
            "name": tag_name,
            "prerelease": False,
            "body": "",
            "assets": [
                {
                    "name": "test.pkg",
                    "browser_download_url": "https://example.com/test.pkg",
                    "url": "https://api.example.com/assets/1",
                    "created_at": "2024-01-01T00:00:00Z",
                }
            ],
        }
    ]


class TestGitHubReleasesInfoProvider(unittest.TestCase):
    """Test class for GitHubReleasesInfoProvider Processor."""

    def setUp(self):
        self.base_env = {
            "CURL_PATH": "/usr/bin/curl",
            "GITHUB_URL": "https://api.github.com",
            "GITHUB_TOKEN_PATH": "~/.autopkg_gh_token",
        }
        self.processor = GitHubReleasesInfoProvider()

    def _run(self, repo="autopkg/autopkg"):
        """Set up env and run the processor, returning the env dict."""
        env = {"github_repo": repo, **self.base_env}
        self.processor.env = env
        self.processor.main()
        return env

    def test_raise_if_no_repo(self):
        """Raise an exception if missing a critical input variable."""
        self.processor.env = {"github_repo": "", **self.base_env}
        with self.assertRaises(ProcessorError):
            self.processor.main()

    @patch.object(
        GitHubReleasesInfoProvider, "get_releases", return_value=_fake_release()
    )
    def test_no_fail_if_good_env(self, _mock):
        """The processor should not raise any exceptions if run normally."""
        self._run()

    @patch.object(
        GitHubReleasesInfoProvider, "get_releases", return_value=_fake_release()
    )
    def test_returns_version_from_tag(self, _mock):
        """The processor should return a version derived from a tag."""
        env = self._run()
        self.assertRegex(env["version"], r"\d[\d.]+")

    @patch.object(
        GitHubReleasesInfoProvider,
        "get_releases",
        return_value=_fake_release("v.1.1.16.1"),
    )
    def test_returns_version_from_tag_with_leading_dot(self, _mock):
        """The processor should handle tags with an extra leading dot."""
        env = self._run("macadmins/nudge")
        self.assertRegex(env["version"], r"\d[\d.]+")

    @patch.object(
        GitHubReleasesInfoProvider, "get_releases", return_value=_fake_release()
    )
    def test_returns_url(self, _mock):
        """The processor should return a URL."""
        env = self._run()
        self.assertIsNotNone(env["url"])

    @patch.object(
        GitHubReleasesInfoProvider, "get_releases", return_value=_fake_release()
    )
    def test_returns_asset_url(self, _mock):
        """The processor should return an asset URL."""
        env = self._run()
        self.assertIsNotNone(env["asset_url"])


if __name__ == "__main__":
    unittest.main()
