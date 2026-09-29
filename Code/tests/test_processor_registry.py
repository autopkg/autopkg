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

"""Tests for the name -> processor class registry that backs add_processor()
and get_processor()."""

import inspect
import os
import unittest

import autopkglib
from autopkglib import Processor


class DummyProcessor(Processor):
    input_variables = {}
    output_variables = {}

    def main(self):
        pass


class TestProcessorRegistry(unittest.TestCase):
    def _register(self, name):
        """Register DummyProcessor under name, cleaning up both containers."""
        self.addCleanup(self._unregister, name)
        autopkglib.add_processor(name, DummyProcessor)

    def _unregister(self, name):
        autopkglib._PROCESSORS.pop(name, None)
        if name in autopkglib._PROCESSOR_NAMES:
            autopkglib._PROCESSOR_NAMES.remove(name)

    def test_add_processor_does_not_shadow_autopkglib_module_globals(self):
        """A recipe-supplied processor named `os` must not replace autopkglib's
        own `os` module reference, which would break autopkglib itself for the
        rest of the process."""
        self._register("os")

        self.assertIs(autopkglib.os, os)
        self.assertIs(autopkglib._PROCESSORS["os"], DummyProcessor)

    def test_add_processor_does_not_shadow_autopkglib_api_names(self):
        """Same for autopkglib's own API names."""
        self._register("Processor")

        # Identity comparison against the imported Processor won't do: the test
        # suite loads autopkglib under more than one module identity, so the
        # base class is not a singleton across the run.
        self.assertIsNot(autopkglib.Processor, DummyProcessor)
        self.assertEqual(autopkglib.Processor.__name__, "Processor")
        self.assertIs(autopkglib._PROCESSORS["Processor"], DummyProcessor)

    def test_add_processor_records_the_name(self):
        self._register("SomeSharedProcessor")

        self.assertIn("SomeSharedProcessor", autopkglib.processor_names())

    def test_get_processor_raises_key_error_for_unknown_name(self):
        """AutoPackager.verify() converts this KeyError into the
        "Unknown processor" error; don't soften it."""
        with self.assertRaises(KeyError):
            autopkglib.get_processor("NoSuchProcessorAnywhere")

    def test_core_processor_names_remain_importable_from_package(self):
        """Third-party shared processors do `from autopkglib import URLGetter`,
        so every core name must stay bound to its class at the package root."""
        for name in autopkglib.core_processor_names():
            with self.subTest(processor=name):
                attr = getattr(autopkglib, name)
                self.assertFalse(inspect.ismodule(attr))
                self.assertTrue(inspect.isclass(attr))


if __name__ == "__main__":
    unittest.main()
