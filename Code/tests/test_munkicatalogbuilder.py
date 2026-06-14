#!/usr/local/autopkg/python
#
# Copyright 2026 Elliot Jordan
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

from autopkglib.MunkiCatalogBuilder import MunkiCatalogBuilder


class TestMunkiCatalogBuilder(unittest.TestCase):
    """Tests for the MunkiCatalogBuilder deprecated no-op processor."""

    def setUp(self):
        self.processor = MunkiCatalogBuilder(env={"verbose": 0})

    def test_main_does_not_raise(self):
        """main() executes without raising an exception and returns None."""
        result = self.processor.main()
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
