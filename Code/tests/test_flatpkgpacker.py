#!/usr/local/autopkg/python

import unittest
from unittest.mock import patch

from autopkglib import ProcessorError
from autopkglib.FlatPkgPacker import FlatPkgPacker


class TestFlatPkgPacker(unittest.TestCase):
    def test_flatten_wraps_launch_error(self):
        processor = FlatPkgPacker()

        with patch("subprocess.check_call", side_effect=OSError(2, "missing")):
            with self.assertRaisesRegex(ProcessorError, "pkgutil execution failed"):
                processor.flatten("/path/to/source", "/path/to/dest.pkg")


if __name__ == "__main__":
    unittest.main()
