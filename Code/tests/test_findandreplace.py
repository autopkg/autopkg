#!/usr/local/autopkg/python

import unittest

from autopkglib.FindAndReplace import FindAndReplace


class TestFindAndReplace(unittest.TestCase):
    """Test class for FindAndReplace Processor."""

    def setUp(self):
        self.processor = FindAndReplace()
        self.single = {
            "input_string": "Hello World",
            "find": "World",
            "replace": "Universe",
        }
        self.multiple = {
            "input_string": "Hello Hello World",
            "find": "Hello",
            "replace": "Howdy",
        }
        self.nomatch = {
            "input_string": "Hello World",
            "find": "Universe",
            "replace": "Multiverse",
        }

    def tearDown(self):
        pass

    def test_simple_find_and_replace(self):
        self.processor.env = self.single
        self.processor.main()
        self.assertEqual(self.processor.env["output_string"], "Hello Universe")

    def test_multiple_find_and_replace(self):
        self.processor.env = self.multiple
        self.processor.main()
        # Both "Hello" should be replaced with "Howdy"
        self.assertEqual(self.processor.env["output_string"], "Howdy Howdy World")

    def test_no_match(self):
        self.processor.env = self.nomatch
        self.processor.main()
        # "Universe" is not in "Hello World", so no replacement
        self.assertEqual(self.processor.env["output_string"], "Hello World")


if __name__ == "__main__":
    unittest.main()
