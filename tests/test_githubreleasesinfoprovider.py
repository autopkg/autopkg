#!/usr/local/autopkg/python

import re
import unittest

from autopkg.autopkglib import ProcessorError
from autopkg.autopkglib.GitHubReleasesInfoProvider import GitHubReleasesInfoProvider


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


if __name__ == "__main__":
    unittest.main()
