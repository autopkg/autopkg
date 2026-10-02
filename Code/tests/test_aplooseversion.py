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

"""Characterization tests for APLooseVersion.
APLooseVersion was vendored off distutils.version.LooseVersion (removed in Python
3.12). These tests pin its parsing and comparison behavior so the vendoring stays
behavior-preserving. Where distutils is still importable (Python < 3.12), we also
assert parity against the original LooseVersion parser.
"""

import unittest

from autopkglib import APLooseVersion, version_equal_or_greater

# A table of version strings exercising the tricky cases: trailing-zero
# equality, alpha/beta/rc suffixes, mixed int/str components, date-like and
# build-suffixed strings, and the int-vs-string comparison path.
VERSION_PAIRS = [
    # (left, right, expected sign of left <=> right): -1, 0, or 1
    ("1.0", "1.0.0", 0),
    ("1.0.0", "1.0", 0),
    ("10.6", "10.6.0", 0),
    ("1.2.3", "1.2.4", -1),
    ("2.0", "1.9.9", 1),
    # NOTE: a trailing non-numeric component sorts GREATER, not less -- the legacy
    # LooseVersion behavior (the str-vs-int TypeError path), preserved by the
    # vendoring. Note this differs from packaging.version, which sorts
    # pre-releases lower.
    ("1.2.3b4", "1.2.3", 1),
    ("1.2.3", "1.2.3b4", -1),
    ("1.0.1", "1.0.1", 0),
    ("2024.05.01", "2024.5.1", 0),
    ("1.0.0-rc1", "1.0.0", 1),
    ("3.10.11", "3.13.0", -1),
    ("11.0", "9.0", 1),
    # Pre-release letters sort lexically; trailing ints sort numerically.
    ("1.0a1", "1.0b1", -1),
    ("1.0b1", "1.0b2", -1),
    # A leading "v" makes the first component a string, so any "vX" sorts above
    # any all-numeric version -- relevant to GitHubReleasesInfoProvider, which
    # sorts release tag_names (often "v1.2.3") with APLooseVersion.
    ("1.0.1", "v1.0", -1),
    ("v1.0.0", "v1.0.1", -1),
]


class TestAPLooseVersion(unittest.TestCase):
    """Pin APLooseVersion behavior."""

    def _sign(self, value: int) -> int:
        return (value > 0) - (value < 0)

    def test_comparison_table(self):
        """Each pair compares with the expected ordering."""
        for left, right, expected in VERSION_PAIRS:
            with self.subTest(left=left, right=right):
                result = APLooseVersion(left)._compare(APLooseVersion(right))
                self.assertEqual(self._sign(result), expected)

    def test_operators(self):
        """The rich-comparison operators agree with _compare."""
        self.assertTrue(APLooseVersion("1.0") == APLooseVersion("1.0.0"))
        self.assertTrue(APLooseVersion("1.0") != APLooseVersion("1.0.1"))
        self.assertTrue(APLooseVersion("1.2.3") < APLooseVersion("1.2.4"))
        self.assertTrue(APLooseVersion("1.2.4") > APLooseVersion("1.2.3"))
        self.assertTrue(APLooseVersion("1.0.0") <= APLooseVersion("1.0"))
        self.assertTrue(APLooseVersion("1.0") >= APLooseVersion("1.0.0"))

    def test_compares_against_bare_string(self):
        """A non-APLooseVersion operand is coerced."""
        self.assertTrue(APLooseVersion("2.0") > "1.0")
        self.assertTrue(APLooseVersion("1.0") == "1.0.0")

    def test_none_treated_as_empty(self):
        """None parses like an empty string."""
        self.assertEqual(APLooseVersion(None).version, [])
        self.assertEqual(str(APLooseVersion(None)), "")

    def test_parse_components(self):
        """Parsing splits into int/str components, dropping dot separators."""
        self.assertEqual(APLooseVersion("1.2.3").version, [1, 2, 3])
        self.assertEqual(APLooseVersion("1.2.3b4").version, [1, 2, 3, "b", 4])

    def test_str_roundtrips_original(self):
        """__str__ returns the original string, not the parsed form."""
        self.assertEqual(str(APLooseVersion("2024.05.01")), "2024.05.01")

    def test_hash_is_unchanged_latent_bug(self):
        """__hash__ hashes a list and raises; pre-existing, preserved by vendoring.

        Documented here so a future __hash__ fix is a deliberate, tested change
        rather than an accidental behavior shift.
        """
        with self.assertRaises(TypeError):
            hash(APLooseVersion("1.2.3"))

    def test_version_equal_or_greater(self):
        """The module-level helper still works after the vendoring."""
        self.assertTrue(version_equal_or_greater("2.0", "1.0"))
        self.assertTrue(version_equal_or_greater("1.0.0", "1.0"))
        self.assertFalse(version_equal_or_greater("1.0", "2.0"))

    def test_parity_with_distutils_where_available(self):
        """On Python < 3.12, parsing matches the original distutils parser."""
        try:
            from distutils.version import LooseVersion
        except ImportError:
            self.skipTest("distutils removed on this interpreter")
        for left, _right, _expected in VERSION_PAIRS:
            with self.subTest(version=left):
                self.assertEqual(
                    APLooseVersion(left).version, LooseVersion(left).version
                )


if __name__ == "__main__":
    unittest.main()
