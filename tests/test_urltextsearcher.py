#!/usr/local/autopkg/python

import plistlib
import unittest
from textwrap import dedent
from unittest.mock import patch

from autopkg.autopkglib import ProcessorError
from autopkg.autopkglib.URLTextSearcher import NO_MATCH_MESSAGE, URLTextSearcher


class TestURLTextSearcher(unittest.TestCase):
    """Test class for URLTextSearcher Processor."""

    web_page = dedent(
        """
        foo
        <a href="http://someserver.url/first.dmg">first</a>
        bar
        <a href="http://someserver.url/second.dmg">second</a>
        drak
        """
    )

    def setUp(self):
        self.good_env = {
            "re_pattern": "http://.*.dmg",
            "result_output_var_name": "match",
            "url": "foobar",
        }
        self.bad_env = {}
        self.match = {
            "protocol": "http",
            "server": "someserver.url",
            "path": "first.dmg",
        }
        self.first_match = (
            f"{self.match['protocol']}://{self.match['server']}/{self.match['path']}"
        )
        self.case_sensitive_pattern = (
            f"{self.match['protocol']}://{self.match['server']}/FiRsT.dmg"
        )
        self.input_plist = plistlib.dumps(self.good_env)
        self.processor = URLTextSearcher(infile=self.input_plist)
        self.processor.env = self.good_env

    def tearDown(self):
        pass

    def match_first(self, mock_download, result_output_var_name="match"):
        """Run processor and expect to find a match"""
        mock_download.return_value = self.web_page
        self.processor.main()
        self.assertEqual(self.processor.env[result_output_var_name], self.first_match)

    def nomatch_exception(self, mock_download):
        """Run processor and expect exception for lack of match to be raised"""
        mock_download.return_value = self.web_page
        with self.assertRaises(ProcessorError) as err:
            self.processor.main()
        self.assertTrue(NO_MATCH_MESSAGE in str(err.exception))

    @patch("autopkg.autopkglib.URLTextSearcher.download_with_curl")
    def test_no_fail_if_good_env(self, mock_download):
        """The processor should not raise any exceptions if run normally."""
        mock_download.return_value = self.web_page
        self.processor.main()

    @patch("autopkg.autopkglib.URLTextSearcher.download_with_curl")
    def test_found_a_match(self, mock_download):
        """If processor finds a match, it should be in the env."""
        self.match_first(mock_download)

    @patch("autopkg.autopkglib.URLTextSearcher.download_with_curl")
    def test_not_found_a_match(self, mock_download):
        """If processor does not find a match, ProcessorError should be raised."""
        self.processor.env["re_pattern"] = "https://badpattern.pkg"
        self.nomatch_exception(mock_download)

    @patch("autopkg.autopkglib.URLTextSearcher.download_with_curl")
    def test_case_sensitive_re_pattern_default(self, mock_download):
        """Difference in character case should not produce a match by default."""
        self.processor.env["re_pattern"] = self.case_sensitive_pattern
        self.nomatch_exception(mock_download)

    @patch("autopkg.autopkglib.URLTextSearcher.download_with_curl")
    def test_case_insensitive_re_pattern_flag(self, mock_download):
        """With re.IGNORECASE flag difference in character case should match."""
        self.processor.env["re_pattern"] = self.case_sensitive_pattern
        self.processor.env["re_flags"] = ["IGNORECASE"]
        self.match_first(mock_download)

    @patch("autopkg.autopkglib.URLTextSearcher.download_with_curl")
    def test_match_last_unnamed_group(self, mock_download):
        """Only last unnamed re group should matchwhen multiple groups used."""
        self.processor.env["re_pattern"] = f'(<a href=")({self.first_match})"'
        self.match_first(mock_download)

    @patch("autopkg.autopkglib.URLTextSearcher.download_with_curl")
    def test_match_named_group_with_output_var(self, mock_download):
        """Only named group with name equal to result_output_var_name should match."""
        output_var_name = "my_match"
        self.processor.env["result_output_var_name"] = output_var_name
        self.processor.env[
            "re_pattern"
        ] = f'(<a href=")(?P<{output_var_name}>{self.first_match})(")'
        self.match_first(mock_download, result_output_var_name=output_var_name)

    @patch("autopkg.autopkglib.URLTextSearcher.download_with_curl")
    def test_match_multiple_named_groups(self, mock_download):
        """Processor should return output variable for each named re group."""
        self.processor.env[
            "re_pattern"
        ] = "(?P<match>(?P<protocol>http[s]?)://(?P<server>.*?)/(?P<path>.*dmg))"
        self.match_first(mock_download)
        self.assertEqual(self.processor.env["protocol"], self.match["protocol"])
        self.assertEqual(self.processor.env["server"], self.match["server"])
        self.assertEqual(self.processor.env["path"], self.match["path"])


if __name__ == "__main__":
    unittest.main()
