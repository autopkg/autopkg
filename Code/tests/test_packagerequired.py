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

import os
import tempfile
import unittest

from autopkglib import ProcessorError
from autopkglib.PackageRequired import PackageRequired


class TestPackageRequired(unittest.TestCase):
    """Tests for PackageRequired."""

    def test_missing_pkg_raises_processor_error(self):
        """ProcessorError raised when PKG is not set in env."""
        processor = PackageRequired(env={"verbose": 0})
        with self.assertRaises(ProcessorError) as ctx:
            processor.main()
        self.assertIn("requires a package or disk image", str(ctx.exception))

    def test_empty_pkg_value_raises_processor_error(self):
        """ProcessorError raised when PKG is an empty string."""
        processor = PackageRequired(env={"PKG": "", "verbose": 0})
        with self.assertRaises(ProcessorError) as ctx:
            processor.main()
        self.assertIn("requires a package or disk image", str(ctx.exception))

    def test_nonexistent_pkg_path_raises_processor_error(self):
        """ProcessorError raised when PKG path does not exist."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_path = os.path.join(tmp_dir, "missing.pkg")
            processor = PackageRequired(env={"PKG": missing_path, "verbose": 0})
            with self.assertRaises(ProcessorError) as ctx:
                processor.main()
        self.assertEqual(
            str(ctx.exception),
            f"Path to package or disk image does not exist: {missing_path}",
        )

    def test_valid_pkg_path_succeeds(self):
        """main() succeeds when PKG is set and path exists."""
        with tempfile.NamedTemporaryFile() as tmp_file:
            processor = PackageRequired(env={"PKG": tmp_file.name, "verbose": 0})
            processor.main()  # Should not raise


if __name__ == "__main__":
    unittest.main()
