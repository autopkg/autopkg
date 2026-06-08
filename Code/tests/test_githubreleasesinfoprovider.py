#!/usr/local/autopkg/python
#
# Copyright 2021 Elliot Jordan
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


def _fake_releases_with_prerelease():
    """Build a minimal release list with a prerelease before a stable release."""
    return [
        {
            "tag_name": "v2.0.0-beta",
            "name": "v2.0.0-beta",
            "prerelease": True,
            "body": "",
            "assets": [
                {
                    "name": "beta.pkg",
                    "browser_download_url": "https://example.com/beta.pkg",
                    "url": "https://api.example.com/assets/beta",
                    "created_at": "2024-01-01T00:00:00Z",
                }
            ],
        },
        {
            "tag_name": "v1.0.0",
            "name": "v1.0.0",
            "prerelease": False,
            "body": "",
            "assets": [
                {
                    "name": "stable.pkg",
                    "browser_download_url": "https://example.com/stable.pkg",
                    "url": "https://api.example.com/assets/stable",
                    "created_at": "2024-01-02T00:00:00Z",
                }
            ],
        },
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
    def test_returns_version_from_tag(self, _mock):
        """The processor should return a version derived from a tag."""
        env = self._run()
        self.assertEqual(env["version"], "3.0.2")

    @patch.object(
        GitHubReleasesInfoProvider,
        "get_releases",
        return_value=_fake_release("v.1.1.16.1"),
    )
    def test_returns_version_from_tag_with_leading_dot(self, _mock):
        """The processor should handle tags with an extra leading dot."""
        env = self._run("macadmins/nudge")
        self.assertEqual(env["version"], "1.1.16.1")

    @patch.object(
        GitHubReleasesInfoProvider, "get_releases", return_value=_fake_release()
    )
    def test_returns_url(self, _mock):
        """The processor should return a URL."""
        env = self._run()
        self.assertEqual(env["url"], "https://example.com/test.pkg")

    @patch.object(
        GitHubReleasesInfoProvider, "get_releases", return_value=_fake_release()
    )
    def test_returns_asset_url(self, _mock):
        """The processor should return an asset URL."""
        env = self._run()
        self.assertEqual(env["asset_url"], "https://api.example.com/assets/1")

    @patch.object(
        GitHubReleasesInfoProvider,
        "get_releases",
        return_value=_fake_releases_with_prerelease(),
    )
    def test_null_include_prereleases_substitution_excludes_prereleases(self, _mock):
        """A null input variable substituted into include_prereleases is false."""
        self.processor.env = {
            "github_repo": "autopkg/autopkg",
            "INCLUDE_PRERELEASES": None,
            **self.base_env,
        }
        self.processor.inject({"include_prereleases": "%INCLUDE_PRERELEASES%"})
        self.processor.main()

        self.assertEqual(self.processor.env["url"], "https://example.com/stable.pkg")


if __name__ == "__main__":
    unittest.main()
