#!/usr/local/autopkg/python
#
# Copyright 2025 Elliot Jordan
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

    def test_simple_find_and_replace_custom_output_var(self):
        self.processor.env = dict(self.single)
        self.processor.env["result_output_var_name"] = "custom_string"
        self.processor.main()
        self.assertEqual(self.processor.env["custom_string"], "Hello Universe")
        self.assertNotIn("output_string", self.processor.env)

    def test_multiple_find_and_replace_custom_output_var(self):
        self.processor.env = dict(self.multiple)
        self.processor.env["result_output_var_name"] = "custom_string"
        self.processor.main()
        self.assertEqual(self.processor.env["custom_string"], "Howdy Howdy World")
        self.assertNotIn("output_string", self.processor.env)

    def test_no_match_custom_output_var(self):
        self.processor.env = dict(self.nomatch)
        self.processor.env["result_output_var_name"] = "custom_string"
        self.processor.main()
        self.assertEqual(self.processor.env["custom_string"], "Hello World")
        self.assertNotIn("output_string", self.processor.env)


if __name__ == "__main__":
    unittest.main()
