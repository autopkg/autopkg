#!/usr/local/autopkg/python

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
import sys
import unittest
from unittest import TestSuite, TextTestRunner

try:
    import coverage

    COVERAGE_AVAILABLE = True
except ImportError:
    COVERAGE_AVAILABLE = False


class SafeStdout:
    """Wrapper for stdout that handles file descriptor errors during shutdown."""

    def __init__(self, original_stdout):
        self._original = original_stdout

    def __getattr__(self, name):
        return getattr(self._original, name)

    def write(self, data):
        try:
            return self._original.write(data)
        except (OSError, ValueError):
            # Silently handle file descriptor errors during shutdown
            pass

    def flush(self):
        try:
            return self._original.flush()
        except (OSError, ValueError):
            # Silently handle file descriptor errors during shutdown
            pass


AUTOPKG_TOP: str = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "Code")
)
sys.path.insert(0, AUTOPKG_TOP)

TESTS_DIR: str = os.path.join(AUTOPKG_TOP, "tests")

# Start coverage collection if available
if COVERAGE_AVAILABLE:
    cov = coverage.Coverage(source=[AUTOPKG_TOP])
    cov.start()

TEST_SUITE: TestSuite = unittest.defaultTestLoader.discover(TESTS_DIR)
RUNNER: TextTestRunner = TextTestRunner(verbosity=2)

# Protect stdout from file descriptor errors during interpreter shutdown
sys.stdout = SafeStdout(sys.stdout)

result = RUNNER.run(TEST_SUITE)

# Stop coverage and save results
if COVERAGE_AVAILABLE:
    cov.stop()
    cov.save()
    cov.html_report()
    cov.xml_report()

if result.wasSuccessful():
    sys.exit(0)
sys.exit(1)
