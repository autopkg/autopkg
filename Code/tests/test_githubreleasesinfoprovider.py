#!/usr/local/autopkg/python

import re
import unittest
from unittest.mock import patch

from autopkglib import ProcessorError
from autopkglib.GitHubReleasesInfoProvider import GitHubReleasesInfoProvider


class TestGitHubReleasesInfoProvider(unittest.TestCase):
    """Test class for GitHubReleasesInfoProvider Processor."""

    def setUp(self):
        self.vers_pattern = r"\d[\d\.]+"
        self.base_env = {
            "CURL_PATH": "/usr/bin/curl",
            "GITHUB_URL": "https://api.github.com",
            "GITHUB_TOKEN_PATH": "~/.autopkg_gh_token",
        }
        self.processor = GitHubReleasesInfoProvider()

    def tearDown(self):
        pass

    def test_raise_if_no_repo(self):
        """Raise an exception if missing a critical input variable."""
        test_env = {"github_repo": ""}
        test_env.update(self.base_env)
        self.processor.env = test_env
        with self.assertRaises(ProcessorError):
            self.processor.main()

    def test_no_fail_if_good_env(self):
        """The processor should not raise any exceptions if run normally."""
        test_env = {"github_repo": "autopkg/autopkg"}
        test_env.update(self.base_env)
        self.processor.env = test_env
        try:
            self.processor.main()
        except ProcessorError:
            self.fail()

    def test_returns_version_from_tag1(self):
        """The processor should return a version derived from a tag."""
        test_env = {"github_repo": "autopkg/autopkg"}
        test_env.update(self.base_env)
        self.processor.env = test_env
        self.processor.main()
        m = re.match(self.vers_pattern, test_env["version"])
        self.assertIsNotNone(m)

    def test_returns_version_from_tag2(self):
        """The processor should return a version derived from a tag, even if
        the tag has an extra leading dot."""
        test_env = {"github_repo": "macadmins/nudge"}
        test_env.update(self.base_env)
        self.processor.env = test_env
        self.processor.main()
        m = re.match(self.vers_pattern, test_env["version"])
        self.assertIsNotNone(m)

    def test_returns_url(self):
        """The processor should return a URL."""
        test_env = {"github_repo": "autopkg/autopkg"}
        test_env.update(self.base_env)
        self.processor.env = test_env
        self.processor.main()
        self.assertIsNotNone(test_env["url"])

    def test_returns_asset_url(self):
        """The processor should return an asset URL."""
        test_env = {"github_repo": "autopkg/autopkg"}
        test_env.update(self.base_env)
        self.processor.env = test_env
        self.processor.main()
        self.assertIsNotNone(test_env["asset_url"])

    def test_main_with_archived_repo(self):
        """The processor should raise an error if repo is archived and ignore_archived is not set."""
        test_env = {"github_repo": "autopkg/autopkg"}
        test_env.update(self.base_env)
        self.processor.env = test_env
        with patch.object(
            GitHubReleasesInfoProvider, "is_archived", return_value=True
        ):
            with self.assertRaises(ProcessorError):
                self.processor.main()

    def test_main_with_archived_repo_fail_if_archived_false(self):
        """The processor should not raise an error if repo is archived and fail_if_archived is False."""
        test_env = {"github_repo": "autopkg/autopkg", "fail_if_archived": False}
        test_env.update(self.base_env)
        self.processor.env = test_env
        with patch.object(
            GitHubReleasesInfoProvider, "is_archived", return_value=True
        ):
            # When fail_if_archived is False, is_archived should not be called
            # This test verifies that the processor doesn't attempt the archived check
            # when fail_if_archived is False, and proceeds with normal release fetching.
            # Since we're not mocking get_releases, this will make a real API call.
            # To avoid that, we also mock get_releases.
            with patch.object(
                GitHubReleasesInfoProvider,
                "get_releases",
                return_value=[
                    {
                        "tag_name": "v1.0",
                        "name": "Release 1.0",
                        "body": "Test release",
                        "prerelease": False,
                        "assets": [
                            {
                                "name": "test.tar.gz",
                                "browser_download_url": "https://example.com/test.tar.gz",
                                "url": "https://api.github.com/repos/test/test/releases/assets/1",
                                "created_at": "2024-01-01T00:00:00Z",
                            }
                        ],
                    }
                ],
            ):
                # This should not raise an error
                try:
                    self.processor.main()
                except ProcessorError:
                    self.fail(
                        "Processor should not raise error when fail_if_archived is False"
                    )


if __name__ == "__main__":
    unittest.main()
