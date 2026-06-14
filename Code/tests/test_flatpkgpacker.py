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

import importlib
import subprocess
import unittest
from unittest.mock import patch

from autopkglib import ProcessorError
from autopkglib.FlatPkgPacker import FlatPkgPacker

flatpkgpacker = importlib.import_module("autopkglib.FlatPkgPacker")


class TestFlatPkgPacker(unittest.TestCase):
    def test_flatten_raises_on_non_mac(self):
        processor = FlatPkgPacker()

        with (
            patch("autopkglib.is_mac", return_value=False),
            patch.object(flatpkgpacker, "is_mac", return_value=False),
        ):
            with self.assertRaisesRegex(
                ProcessorError, "Flat package packing is only supported on macOS"
            ):
                processor.flatten("/path/to/source", "/path/to/dest.pkg")

    def test_flatten_wraps_launch_error(self):
        processor = FlatPkgPacker()

        with (
            patch("autopkglib.is_mac", return_value=True),
            patch.object(flatpkgpacker, "is_mac", return_value=True),
            patch("subprocess.check_call", side_effect=OSError(2, "missing")),
        ):
            with self.assertRaisesRegex(ProcessorError, "pkgutil execution failed"):
                processor.flatten("/path/to/source", "/path/to/dest.pkg")

    def test_flatten_wraps_called_process_error(self):
        processor = FlatPkgPacker()

        with (
            patch("autopkglib.is_mac", return_value=True),
            patch.object(flatpkgpacker, "is_mac", return_value=True),
            patch(
                "subprocess.check_call",
                side_effect=subprocess.CalledProcessError(1, "pkgutil"),
            ),
        ):
            with self.assertRaisesRegex(ProcessorError, "flattening /path/to/source"):
                processor.flatten("/path/to/source", "/path/to/dest.pkg")

    def test_main_calls_flatten_and_outputs(self):
        processor = FlatPkgPacker()
        processor.env = {
            "source_flatpkg_dir": "/path/to/source",
            "destination_pkg": "/path/to/dest.pkg",
        }

        with (
            patch.object(processor, "flatten") as mock_flatten,
            patch.object(processor, "output") as mock_output,
        ):
            processor.main()

        mock_flatten.assert_called_once_with("/path/to/source", "/path/to/dest.pkg")
        mock_output.assert_called_once_with(
            "Flattened /path/to/source to /path/to/dest.pkg"
        )


if __name__ == "__main__":
    unittest.main()
