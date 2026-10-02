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

import sys
import unittest
from copy import deepcopy
from unittest.mock import MagicMock, patch

from autopkglib import ProcessorError
from autopkglib.StopProcessingIf import StopProcessingIf

TEST_PREDICATE = "version == '1.0'"


class TestStopProcessingIf(unittest.TestCase):
    """Test class for StopProcessingIf Processor."""

    def setUp(self):
        self.env = {"predicate": TEST_PREDICATE}
        self.processor = StopProcessingIf(env=deepcopy(self.env))
        self.module = sys.modules[StopProcessingIf.__module__]

    def test_predicate_evaluates_as_true_when_true(self):
        """Returns True and calls output() when the predicate evaluates to True."""
        mock_predicate = MagicMock()
        mock_predicate.evaluateWithObject_.return_value = True

        with patch.object(self.module, "NSPredicate", create=True) as mock_ns:
            mock_ns.predicateWithFormat_.return_value = mock_predicate
            with patch.object(self.processor, "output") as mock_output:
                result = self.processor.predicate_evaluates_as_true(TEST_PREDICATE)

        self.assertTrue(result)
        mock_output.assert_called_once()
        call_args = mock_output.call_args[0][0]
        self.assertIn(TEST_PREDICATE, call_args)

    def test_predicate_evaluates_as_true_when_false(self):
        """Returns False when the predicate evaluates to False."""
        mock_predicate = MagicMock()
        mock_predicate.evaluateWithObject_.return_value = False

        with patch.object(self.module, "NSPredicate", create=True) as mock_ns:
            mock_ns.predicateWithFormat_.return_value = mock_predicate
            result = self.processor.predicate_evaluates_as_true(TEST_PREDICATE)

        self.assertFalse(result)

    def test_predicate_evaluates_as_true_raises_processor_error(self):
        """Raises ProcessorError when NSPredicate raises an exception."""
        with patch.object(self.module, "NSPredicate", create=True) as mock_ns:
            mock_ns.predicateWithFormat_.side_effect = ValueError("bad predicate")
            with self.assertRaises(ProcessorError) as ctx:
                self.processor.predicate_evaluates_as_true(TEST_PREDICATE)

        self.assertIn(TEST_PREDICATE, str(ctx.exception))
        self.assertIn("bad predicate", str(ctx.exception))

    def test_main_sets_stop_processing_recipe_env_var(self):
        """main() sets stop_processing_recipe to True when predicate is True."""
        mock_predicate = MagicMock()
        mock_predicate.evaluateWithObject_.return_value = True

        with patch.object(self.module, "NSPredicate", create=True) as mock_ns:
            mock_ns.predicateWithFormat_.return_value = mock_predicate
            self.processor.main()

        self.assertTrue(self.processor.env["stop_processing_recipe"])

    def test_main_with_false_predicate(self):
        """main() sets stop_processing_recipe to False when predicate is False."""
        mock_predicate = MagicMock()
        mock_predicate.evaluateWithObject_.return_value = False

        with patch.object(self.module, "NSPredicate", create=True) as mock_ns:
            mock_ns.predicateWithFormat_.return_value = mock_predicate
            self.processor.main()

        self.assertFalse(self.processor.env["stop_processing_recipe"])


if __name__ == "__main__":
    unittest.main()
