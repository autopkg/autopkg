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
import unittest.mock
from copy import deepcopy

from autopkglib.DeprecationWarning import DeprecationWarning

DEFAULT_MESSAGE = "### This recipe has been deprecated. It may be removed soon. ###"


class TestDeprecationWarning(unittest.TestCase):
    """Test class for DeprecationWarning Processor."""

    def setUp(self):
        self.env = {"RECIPE_PATH": "/fake/path/SomeRecipe.recipe"}
        self.processor = DeprecationWarning(env=deepcopy(self.env))

    def test_uses_default_warning_message_when_not_provided(self):
        """main() uses the default message when warning_message is not in env."""
        with unittest.mock.patch.object(
            self.processor, "show_deprecation"
        ) as mock_show:
            self.processor.main()
        mock_show.assert_called_with(DEFAULT_MESSAGE)

    def test_uses_custom_warning_message_when_provided(self):
        """main() uses a custom message when warning_message is present in env."""
        custom_message = "This recipe is no longer maintained."
        self.processor.env["warning_message"] = custom_message
        with unittest.mock.patch.object(
            self.processor, "show_deprecation"
        ) as mock_show:
            self.processor.main()
        mock_show.assert_called_with(custom_message)

    def test_empty_warning_message_passes_through(self):
        """Empty string warning_message is passed through, not replaced with the default."""
        self.processor.env["warning_message"] = ""
        with unittest.mock.patch.object(
            self.processor, "show_deprecation"
        ) as mock_show:
            self.processor.main()
        mock_show.assert_called_with("")


if __name__ == "__main__":
    unittest.main()
