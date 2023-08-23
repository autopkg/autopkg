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

import re
import unittest

from autopkglib import ProcessorError
from autopkglib.apgithubReleasesInfoProvider import GitHubReleasesInfoProvider


@unittest.skip("Skip GitHubReleasesInfoProvider tests while they are being redone")
class TestGitHubReleasesInfoProvider(unittest.TestCase):
    """Test class for GitHubReleasesInfoProvider Processor."""

    def setUp(self):
        self.vers_pattern = r"\d[\d\.]+"
        self.base_env = {
            "CURL_PATH": "/usr/bin/curl",
            "GITHUB_URL": "https://api.github.com",
            "GITHUB_TOKEN_PATH": "~/Library/AutoPkg/gh_token",
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
