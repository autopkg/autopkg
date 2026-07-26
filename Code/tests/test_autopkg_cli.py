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
import sys
import unittest
import unittest.mock
from io import StringIO
from unittest.mock import patch

# Add the Code directory to the Python path to resolve autopkg dependencies
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests import load_autopkg_module

autopkg = load_autopkg_module()


class TestAutoPkgCLI(unittest.TestCase):
    """Test cases for top-level CLI behaviour: help display, main()
    dispatch, and the path/plist output formatting helpers."""

    def setUp(self):
        """Silence recipe-map side effects (see test_autopkg_recipes for
        rationale)."""
        self._recipe_map_patches = [
            patch("autopkg.calculate_recipe_map"),
            patch("autopkg.read_recipe_map"),
        ]
        for patcher in self._recipe_map_patches:
            patcher.start()

    def tearDown(self):
        for patcher in self._recipe_map_patches:
            patcher.stop()

    def test_display_help_basic_functionality(self):
        """Test display_help with basic subcommands."""
        argv = ["autopkg"]
        subcommands = {
            "run": {"help": "Run one or more recipes"},
            "list-recipes": {"help": "List available recipes"},
            "info": {"help": "Get information about a recipe"},
        }

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            autopkg.display_help(argv, subcommands)
            output = mock_stdout.getvalue()

        # Check that the usage line is printed
        self.assertIn("Usage: autopkg <verb> <options>", output)
        self.assertIn("where <verb> is one of the following:", output)

        # Check that all subcommands are listed
        self.assertIn("info", output)
        self.assertIn("list-recipes", output)
        self.assertIn("run", output)

        # Check that help text for each subcommand is included
        self.assertIn("Run one or more recipes", output)
        self.assertIn("List available recipes", output)
        self.assertIn("Get information about a recipe", output)

        # Check that the final help line is printed
        self.assertIn("autopkg <verb> --help for more help for that verb", output)

    def test_display_help_with_custom_command_name(self):
        """Test display_help with a custom command name in argv[0]."""
        argv = ["/usr/local/bin/autopkg-custom"]
        subcommands = {
            "test": {"help": "Test command"},
        }

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            autopkg.display_help(argv, subcommands)
            output = mock_stdout.getvalue()

        # Check that the custom command name is used
        self.assertIn("Usage: autopkg-custom <verb> <options>", output)
        self.assertIn("autopkg-custom <verb> --help", output)

    def test_display_help_with_path_in_argv0(self):
        """Test display_help when argv[0] contains a full path."""
        argv = ["/some/long/path/to/autopkg"]
        subcommands = {
            "version": {"help": "Show version information"},
        }

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            autopkg.display_help(argv, subcommands)
            output = mock_stdout.getvalue()

        # Check that only the basename is used, not the full path
        self.assertIn("Usage: autopkg <verb> <options>", output)
        self.assertNotIn("/some/long/path/to/autopkg", output)

    def test_display_help_with_unknown_verb(self):
        """Test display_help when an unknown verb is provided."""
        argv = ["autopkg", "unknown-command"]
        subcommands = {
            "run": {"help": "Run one or more recipes"},
            "info": {"help": "Get information about a recipe"},
        }

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            autopkg.display_help(argv, subcommands)
            output = mock_stdout.getvalue()

        # Check that the error message for unknown verb is displayed
        self.assertIn("Error: unknown verb: unknown-command", output)

        # Check that normal help content is still displayed
        self.assertIn("Usage: autopkg <verb> <options>", output)
        self.assertIn("run", output)
        self.assertIn("info", output)

    def test_display_help_with_valid_verb_in_subcommands(self):
        """Test display_help when a valid verb is provided."""
        argv = ["autopkg", "run"]
        subcommands = {
            "run": {"help": "Run one or more recipes"},
            "info": {"help": "Get information about a recipe"},
        }

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            autopkg.display_help(argv, subcommands)
            output = mock_stdout.getvalue()

        # Check that no error message is displayed for valid verb
        self.assertNotIn("Error: unknown verb:", output)

        # Check that the normal help message is displayed
        self.assertIn("autopkg <verb> --help for more help for that verb", output)

    def test_display_help_subcommand_alignment(self):
        """Test display_help aligns subcommands properly."""
        argv = ["autopkg"]
        subcommands = {
            "a": {"help": "Short command"},
            "very-long-command-name": {"help": "Long command"},
            "mid": {"help": "Medium command"},
        }

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            autopkg.display_help(argv, subcommands)
            output = mock_stdout.getvalue()

        lines = output.split("\n")

        # Find lines containing subcommands
        subcommand_lines = [
            line
            for line in lines
            if (
                "Short command" in line
                or "Long command" in line
                or "Medium command" in line
            )
        ]

        # Check that we have all three subcommands
        self.assertEqual(len(subcommand_lines), 3)

        # Check that alignment is consistent (all help text starts at same position)
        help_positions = []
        for line in subcommand_lines:
            if "(" in line and ")" in line:
                help_start = line.index("(")
                help_positions.append(help_start)

        # All help text should start at the same position
        self.assertEqual(
            len(set(help_positions)), 1, "Help text should be aligned consistently"
        )

    def test_display_help_sorted_subcommands(self):
        """Test display_help displays subcommands in sorted order."""
        argv = ["autopkg"]
        subcommands = {
            "zebra": {"help": "Last alphabetically"},
            "alpha": {"help": "First alphabetically"},
            "beta": {"help": "Middle alphabetically"},
        }

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            autopkg.display_help(argv, subcommands)
            output = mock_stdout.getvalue()

        # Find the positions of each subcommand in the output
        alpha_pos = output.find("alpha")
        beta_pos = output.find("beta")
        zebra_pos = output.find("zebra")

        # Check that they appear in alphabetical order
        self.assertLess(alpha_pos, beta_pos)
        self.assertLess(beta_pos, zebra_pos)

    def test_display_help_empty_subcommands(self):
        """Test display_help with empty subcommands dictionary."""
        argv = ["autopkg"]
        subcommands = {}

        with patch("sys.stdout", new_callable=StringIO):
            # This should raise a ValueError when trying to find max of empty sequence
            with self.assertRaises(ValueError):
                autopkg.display_help(argv, subcommands)

    def test_display_help_single_subcommand(self):
        """Test display_help with only one subcommand."""
        argv = ["autopkg"]
        subcommands = {
            "only": {"help": "The only command available"},
        }

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            autopkg.display_help(argv, subcommands)
            output = mock_stdout.getvalue()

        # Check basic functionality with single command
        self.assertIn("Usage: autopkg <verb> <options>", output)
        self.assertIn("only", output)
        self.assertIn("The only command available", output)

    def test_display_help_no_argv_provided(self):
        """Test display_help when argv has no additional arguments."""
        argv = ["autopkg"]
        subcommands = {
            "test": {"help": "Test command"},
        }

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            autopkg.display_help(argv, subcommands)
            output = mock_stdout.getvalue()

        # Should not show error message when no additional args provided
        self.assertNotIn("Error: unknown verb:", output)
        self.assertIn("autopkg <verb> --help for more help for that verb", output)

    def test_display_help_with_special_characters_in_help_text(self):
        """Test display_help with special characters in help text."""
        argv = ["autopkg"]
        subcommands = {
            "special": {"help": "Command with (parentheses) and [brackets]"},
            "unicode": {"help": "Command with unicode: café résumé"},
        }

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            autopkg.display_help(argv, subcommands)
            output = mock_stdout.getvalue()

        # Check that special characters are handled correctly
        self.assertIn("Command with (parentheses) and [brackets]", output)
        self.assertIn("Command with unicode: café résumé", output)

    def test_display_help_with_long_help_text(self):
        """Test display_help with very long help text."""
        argv = ["autopkg"]
        subcommands = {
            "long": {
                "help": "This is a very long help text that should still be displayed correctly without breaking the formatting or causing any issues with the output"
            },
        }

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            autopkg.display_help(argv, subcommands)
            output = mock_stdout.getvalue()

        # Check that long help text is included
        self.assertIn("This is a very long help text", output)
        self.assertIn("without breaking the formatting", output)

    def test_display_help_preserves_original_subcommands(self):
        """Test display_help doesn't modify the original subcommands dictionary."""
        argv = ["autopkg"]
        original_subcommands = {
            "test": {"help": "Test command"},
            "run": {"help": "Run command"},
        }
        subcommands_copy = original_subcommands.copy()

        with patch("sys.stdout", new_callable=StringIO):
            autopkg.display_help(argv, subcommands_copy)

        # Check that the original dictionary wasn't modified
        self.assertEqual(original_subcommands, subcommands_copy)

    def test_os_path_compressuser(self):
        """os_path_compressuser replaces the home dir prefix with '~' and
        leaves anything outside the home dir untouched.

        Paths are built with os.sep so the real os.path.relpath can run
        unmocked on both POSIX and Windows. Mocking relpath would leave only
        the '~/' concatenation under test. Note the result keeps the literal
        '~/' prefix, so on Windows it mixes separators ('~/Library\\AutoPkg');
        the value is only ever printed, never used as a path.
        """
        users = os.path.join(os.sep, "Users")
        home_dir = os.path.join(users, "testuser")
        subdir = os.path.join("Library", "AutoPkg")
        nested = os.path.join(subdir, "Recipes", "TestDev", "TestApp.recipe")
        outside = os.path.join(os.sep, "usr", "local", "bin", "autopkg")
        no_shared_prefix = os.path.join(users, "otheruser", "Documents")
        shared_prefix = os.path.join(users, "testuser2", "Documents")
        cases = [
            # (pathname, expected, what it covers)
            (home_dir, "~", "exact home"),
            (os.path.join(home_dir, subdir), f"~/{subdir}", "subdirectory"),
            (os.path.join(home_dir, nested), f"~/{nested}", "nested subdirectory"),
            (outside, outside, "outside home"),
            (no_shared_prefix, no_shared_prefix, "sibling home, no shared prefix"),
            # Shares a string prefix with home_dir but is not inside it.
            # Returned "~/../testuser2/Documents" before the separator
            # boundary was added to the startswith() check.
            (shared_prefix, shared_prefix, "sibling home sharing a prefix"),
            (subdir, subdir, "relative path"),
            ("", "", "empty string"),
        ]
        with patch("os.path.expanduser", return_value=home_dir):
            for pathname, expected, covers in cases:
                with self.subTest(covers=covers, pathname=pathname):
                    self.assertEqual(autopkg.os_path_compressuser(pathname), expected)

    def test_printplistitem_scalars(self):
        """Scalar values print as 'label: value', indented four spaces per
        level, with None rendered as !NONE! and no label omitting the colon."""
        cases = [
            # (label, value, indent, expected log line)
            ("test_key", "test_value", 0, "test_key: test_value"),
            ("test_key", "test_value", 2, "        test_key: test_value"),
            ("test_key", None, 0, "test_key: !NONE!"),
            ("number", 42, 0, "number: 42"),
            ("flag", True, 0, "flag: True"),
            ("", "test_value", 1, "    test_value"),
            ("", None, 1, "    : !NONE!"),
        ]
        for label, value, indent, expected in cases:
            with self.subTest(label=label, value=value, indent=indent):
                with patch("autopkg.log") as mock_log:
                    autopkg.printplistitem(label, value, indent=indent)
                    mock_log.assert_called_once_with(expected)

    def test_printplistitem_containers(self):
        """Lists and dicts print a label line then recurse one indent level
        deeper; empty containers print the label line only."""
        cases = [
            # (label, value, expected log lines in order)
            (
                "test_list",
                ["item1", "item2", "item3"],
                ["test_list:", "    item1", "    item2", "    item3"],
            ),
            ("empty_list", [], ["empty_list:"]),
            (
                "mixed",
                ["string", 42, True, None],
                ["mixed:", "    string", "    42", "    True", "    : !NONE!"],
            ),
            (
                "test_dict",
                {"key1": "value1", "key2": "value2"},
                ["test_dict:", "    key1: value1", "    key2: value2"],
            ),
            (
                "nested",
                {"outer_key": {"inner_key": "inner_value"}},
                ["nested:", "    outer_key:", "        inner_key: inner_value"],
            ),
        ]
        for label, value, expected in cases:
            with self.subTest(label=label):
                with patch("autopkg.log") as mock_log:
                    autopkg.printplistitem(label, value, indent=0)
                    self.assertEqual(
                        [call.args[0] for call in mock_log.call_args_list], expected
                    )

    def test_main_help_no_args(self):
        """Test main() with no arguments defaults to help."""
        argv = ["autopkg"]

        with patch("autopkg.display_help") as mock_display_help:
            result = autopkg.main(argv)

            # Should call display_help and return 1
            mock_display_help.assert_called_once()
            self.assertEqual(result, 1)

    def test_main_help_explicit(self):
        """Test main() with explicit help command."""
        argv = ["autopkg", "help"]

        with patch("autopkg.display_help") as mock_display_help:
            result = autopkg.main(argv)

            # Should call display_help and return 1
            mock_display_help.assert_called_once()
            self.assertEqual(result, 1)

    def test_main_invalid_verb(self):
        """Test main() with invalid verb."""
        argv = ["autopkg", "invalid-command"]

        with patch("autopkg.display_help") as mock_display_help:
            result = autopkg.main(argv)

            # Should call display_help and return 1
            mock_display_help.assert_called_once()
            self.assertEqual(result, 1)

    def test_main_option_instead_of_verb(self):
        """Test main() with option instead of verb."""
        argv = ["autopkg", "--version"]

        with patch("autopkg.display_help") as mock_display_help:
            result = autopkg.main(argv)

            # Should call display_help and return 1
            mock_display_help.assert_called_once()
            self.assertEqual(result, 1)

    def test_main_valid_verb_version(self):
        """Test main() with valid version verb."""
        argv = ["autopkg", "version"]

        with patch("autopkg.print_version") as mock_print_version:
            mock_print_version.return_value = 0
            result = autopkg.main(argv)

            # Should call print_version function
            mock_print_version.assert_called_once_with(argv)
            self.assertEqual(result, 0)

    def test_main_valid_verb_run(self):
        """Test main() with valid run verb."""
        argv = ["autopkg", "run", "test.recipe"]

        with patch("autopkg.run_recipes") as mock_run_recipes:
            mock_run_recipes.return_value = 0
            result = autopkg.main(argv)

            # Should call run_recipes function
            mock_run_recipes.assert_called_once_with(argv)
            self.assertEqual(result, 0)

    @unittest.skipUnless(sys.platform == "darwin", "Uses os.getuid (Unix-only)")
    def test_main_root_warning_mac(self):
        """Test main() shows warning when running as root on macOS."""
        argv = ["autopkg", "version"]

        with (
            patch("autopkg.is_mac", return_value=True),
            patch("os.getuid", return_value=0),
            patch("autopkg.log_err") as mock_log_err,
            patch("autopkg.print_version", return_value=0),
        ):
            autopkg.main(argv)

            # Should log multiple warning messages
            warning_calls = [
                log_call
                for log_call in mock_log_err.call_args_list
                if "WARNING!" in str(log_call)
            ]
            self.assertGreater(len(warning_calls), 0)

    @unittest.skipUnless(sys.platform == "darwin", "Uses os.getuid (Unix-only)")
    def test_main_no_root_warning_non_root(self):
        """Test main() doesn't show root warning when not running as root."""
        argv = ["autopkg", "version"]

        with (
            patch("autopkg.is_mac", return_value=True),
            patch("os.getuid", return_value=1000),
            patch("autopkg.log_err") as mock_log_err,
            patch("autopkg.print_version", return_value=0),
        ):
            autopkg.main(argv)

            # Should not log warning messages
            warning_calls = [
                log_call
                for log_call in mock_log_err.call_args_list
                if "WARNING!" in str(log_call)
            ]
            self.assertEqual(len(warning_calls), 0)

    def test_main_function_return_values(self):
        """Test main() properly returns function return values."""
        argv = ["autopkg", "run", "test.recipe"]

        # Test successful execution
        with patch("autopkg.run_recipes", return_value=0):
            result = autopkg.main(argv)
            self.assertEqual(result, 0)

        # Test failed execution
        with patch("autopkg.run_recipes", return_value=1):
            result = autopkg.main(argv)
            self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
