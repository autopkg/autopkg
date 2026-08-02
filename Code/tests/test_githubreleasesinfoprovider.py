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
from autopkglib.GitHubReleasesInfoProvider import (
    GitHubReleasesInfoProvider,
    NoMatchingReleaseError,
)


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
        GitHubReleasesInfoProvider,
        "get_releases",
        return_value=_fake_release("vv1.0"),
    )
    def test_returns_version_stripping_only_one_v_prefix(self, _mock):
        """The processor should remove only one leading v from a tag."""
        env = self._run()
        self.assertEqual(env["version"], "v1.0")

    def test_preserves_intentional_extra_leading_dots(self):
        for tag_name in ("v..1.2", ".1.2"):
            with self.subTest(tag_name=tag_name):
                with patch.object(
                    GitHubReleasesInfoProvider,
                    "get_releases",
                    return_value=_fake_release(tag_name),
                ):
                    env = self._run()

                self.assertEqual(env["version"], ".1.2")

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

    # --- get_releases ---

    @patch("autopkglib.github.GitHubSession.call_api", return_value=(None, 403))
    def test_get_releases_with_http_error(self, _mock):
        """get_releases() raises ProcessorError when GitHub API returns non-200."""
        self.processor.env = {"github_repo": "autopkg/autopkg", **self.base_env}
        with self.assertRaises(ProcessorError) as ctx:
            self.processor.get_releases("autopkg/autopkg")
        self.assertIn("Unexpected GitHub API status code 403", str(ctx.exception))

    @patch("autopkglib.github.GitHubSession.call_api", return_value=([], 200))
    def test_get_releases_empty_list(self, _mock):
        """get_releases() raises ProcessorError when API returns empty list."""
        self.processor.env = {"github_repo": "autopkg/autopkg", **self.base_env}
        with self.assertRaises(ProcessorError) as ctx:
            self.processor.get_releases("autopkg/autopkg")
        self.assertIn("No releases found for repo", str(ctx.exception))

    def test_get_releases_with_latest_only_wraps_in_list(self):
        """get_releases() with latest_only=True wraps single dict in a list."""
        single = _fake_release()[0]
        self.processor.env = {"github_repo": "autopkg/autopkg", **self.base_env}
        with patch(
            "autopkglib.github.GitHubSession.call_api", return_value=(single, 200)
        ):
            result = self.processor.get_releases("autopkg/autopkg", latest_only=True)
        self.assertIsInstance(result, list)
        self.assertEqual(result, [single])

    # --- select_asset ---

    def test_select_asset_skips_prerelease_when_not_included(self):
        """select_asset() skips prerelease when include_prereleases is not set."""
        releases = _fake_releases_with_prerelease()
        self.processor.env = {"github_repo": "autopkg/autopkg", **self.base_env}
        self.processor.select_asset(releases, None)
        self.assertEqual(self.processor.selected_asset["name"], "stable.pkg")

    def test_select_asset_skips_release_with_no_assets(self):
        """select_asset() skips releases with empty assets list."""
        releases = [
            {
                "tag_name": "v1.0.0",
                "name": "v1.0.0",
                "prerelease": False,
                "body": "",
                "assets": [],
            },
            _fake_release()[0],
        ]
        self.processor.env = {"github_repo": "autopkg/autopkg", **self.base_env}
        self.processor.select_asset(releases, None)
        self.assertEqual(self.processor.selected_asset["name"], "test.pkg")

    def test_select_asset_with_regex_match(self):
        """select_asset() matches asset name against regex."""
        releases = [
            {
                "tag_name": "v1.0.0",
                "name": "v1.0.0",
                "prerelease": False,
                "body": "",
                "assets": [
                    {
                        "name": "app-1.0.dmg",
                        "browser_download_url": "https://example.com/app-1.0.dmg",
                        "url": "https://api.example.com/assets/dmg",
                        "created_at": "2024-01-01T00:00:00Z",
                    },
                    {
                        "name": "app-1.0.zip",
                        "browser_download_url": "https://example.com/app-1.0.zip",
                        "url": "https://api.example.com/assets/zip",
                        "created_at": "2024-01-01T00:00:00Z",
                    },
                ],
            }
        ]
        self.processor.env = {"github_repo": "autopkg/autopkg", **self.base_env}
        self.processor.select_asset(releases, r".*\.dmg$")
        self.assertEqual(self.processor.selected_asset["name"], "app-1.0.dmg")

    def test_select_asset_with_invalid_regex_raises_error(self):
        """select_asset() raises ProcessorError on invalid regex."""
        releases = [_fake_release()[0]]
        self.processor.env = {"github_repo": "autopkg/autopkg", **self.base_env}
        with self.assertRaises(ProcessorError) as ctx:
            self.processor.select_asset(releases, "[invalid(regex")
        self.assertIn("Invalid regex", str(ctx.exception))

    def test_select_asset_raises_no_matching_when_nothing_selected(self):
        """select_asset() raises NoMatchingReleaseError when nothing matches."""
        releases = [
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
                "assets": [],
            },
        ]
        self.processor.env = {"github_repo": "autopkg/autopkg", **self.base_env}
        with self.assertRaises(NoMatchingReleaseError):
            self.processor.select_asset(releases, None)

    # --- main ---

    @patch.object(
        GitHubReleasesInfoProvider,
        "get_releases",
        return_value=[
            {
                "tag_name": "v1.0",
                "name": "v1.0",
                "prerelease": False,
                "body": "",
                "assets": [
                    {
                        "name": "app-1.0.pkg",
                        "browser_download_url": "https://example.com/app-1.0.pkg",
                        "url": "https://api.example.com/assets/1",
                        "created_at": "2024-01-01T00:00:00Z",
                    }
                ],
            },
            {
                "tag_name": "v3.0",
                "name": "v3.0",
                "prerelease": False,
                "body": "",
                "assets": [
                    {
                        "name": "app-3.0.pkg",
                        "browser_download_url": "https://example.com/app-3.0.pkg",
                        "url": "https://api.example.com/assets/3",
                        "created_at": "2024-01-03T00:00:00Z",
                    }
                ],
            },
            {
                "tag_name": "v2.0",
                "name": "v2.0",
                "prerelease": False,
                "body": "",
                "assets": [
                    {
                        "name": "app-2.0.pkg",
                        "browser_download_url": "https://example.com/app-2.0.pkg",
                        "url": "https://api.example.com/assets/2",
                        "created_at": "2024-01-02T00:00:00Z",
                    }
                ],
            },
        ],
    )
    def test_main_with_sort_by_highest_tag_names(self, _mock):
        """main() selects highest version when sort_by_highest_tag_names is set."""
        self.processor.env = {
            "github_repo": "autopkg/autopkg",
            "sort_by_highest_tag_names": True,
            **self.base_env,
        }
        self.processor.main()
        self.assertEqual(self.processor.env["version"], "3.0")

    def test_main_honors_github_releases_per_page(self):
        """main() passes GITHUB_RELEASES_PER_PAGE to get_releases()."""
        with patch.object(
            GitHubReleasesInfoProvider, "get_releases", return_value=_fake_release()
        ) as mock_get_releases:
            self.processor.env = {
                "github_repo": "autopkg/autopkg",
                "GITHUB_RELEASES_PER_PAGE": 75,
                **self.base_env,
            }
            self.processor.main()

        mock_get_releases.assert_called_once_with(
            "autopkg/autopkg", latest_only=None, page=1, per_page=75
        )

    def test_main_pagination_with_no_matching_first_page(self):
        """main() continues to next page on NoMatchingReleaseError."""
        page1_releases = [
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
            }
        ]
        page2_releases = _fake_release()

        call_count = {"n": 0}

        def side_effect(repo, page=1, per_page=30, latest_only=False):
            call_count["n"] += 1
            if page == 1:
                return page1_releases
            return page2_releases

        with patch.object(
            GitHubReleasesInfoProvider, "get_releases", side_effect=side_effect
        ):
            self.processor.env = {
                "github_repo": "autopkg/autopkg",
                **self.base_env,
            }
            self.processor.main()

        self.assertEqual(call_count["n"], 2)
        self.assertEqual(self.processor.env["version"], "3.0.2")

    def test_main_latest_only_stops_when_no_asset_matches(self):
        """main() gives up after one request when latest_only finds no match.

        A latest_only request asks for the single latest release and ignores the
        page number, so advancing to the next page can never return anything new.
        """
        call_count = {"n": 0}

        def side_effect(repo, page=1, per_page=30, latest_only=False):
            call_count["n"] += 1
            if call_count["n"] > 5:
                self.fail("get_releases() called repeatedly; latest_only is looping")
            return _fake_release()

        with patch.object(
            GitHubReleasesInfoProvider, "get_releases", side_effect=side_effect
        ):
            self.processor.env = {
                "github_repo": "autopkg/autopkg",
                "latest_only": True,
                "asset_regex": r"^this-will-never-match\.pkg$",
                **self.base_env,
            }
            with self.assertRaises(NoMatchingReleaseError):
                self.processor.main()

        self.assertEqual(call_count["n"], 1)

    def test_main_latest_only_selects_matching_asset(self):
        """main() still resolves an asset normally when latest_only is set."""
        with patch.object(
            GitHubReleasesInfoProvider, "get_releases", return_value=_fake_release()
        ) as mock_get_releases:
            self.processor.env = {
                "github_repo": "autopkg/autopkg",
                "latest_only": True,
                "asset_regex": r"^test\.pkg$",
                **self.base_env,
            }
            self.processor.main()

        mock_get_releases.assert_called_once_with(
            "autopkg/autopkg", latest_only=True, page=1, per_page=30
        )
        self.assertEqual(self.processor.env["version"], "3.0.2")


if __name__ == "__main__":
    unittest.main()
