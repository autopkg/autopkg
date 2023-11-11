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

import unittest
from unittest.mock import patch

from autopkg.autopkgcmd import search_recipes


class TestSearchCmd(unittest.TestCase):
    def setUp(self):
        # Disable preference reading for consistency
        patch("autopkg.autopkgcmd.opts.globalPreferences").start()
        pass

    def test_no_term(self):
        self.assertEqual(1, search_recipes(["TestSearchCmd", "search"]))

    @patch("autopkg.autopkgcmd.searchcmd.GitHubSession.code_search")
    def test_empty_results(self, gh_mock):
        gh_mock.return_value = []
        self.assertEqual(
            2, search_recipes(["TestSearchCmd", "search", "#test-search#"])
        )

    @patch("autopkg.autopkgcmd.searchcmd.print_gh_search_results")
    @patch("autopkg.autopkgcmd.searchcmd.GitHubSession.search_for_name")
    def test_too_many_results(self, search_mock, _print_results_mock):
        search_mock.return_value = list(range(101))
        self.assertEqual(
            3, search_recipes(["TestSearchCmd", "search", "#test-search#"])
        )

    @patch("autopkg.autopkgcmd.searchcmd.print_gh_search_results")
    @patch("autopkg.autopkgcmd.searchcmd.GitHubSession.search_for_name")
    def test_got_results(self, search_mock, _print_results_mock):
        search_mock.return_value = list(range(10))
        self.assertEqual(
            0, search_recipes(["TestSearchCmd", "search", "#test-search#"])
        )


if __name__ == "__main__":
    unittest.main()
