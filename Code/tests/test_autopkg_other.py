#!/usr/local/autopkg/python
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

import imp
import os
import sys
import unittest
import unittest.mock
from io import StringIO
from unittest.mock import patch

# Add the Code directory to the Python path to resolve autopkg dependencies
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

autopkg = imp.load_source(
    "autopkg", os.path.join(os.path.dirname(__file__), "..", "autopkg")
)


class TestAutoPkgOther(unittest.TestCase):
    """Test cases for miscellaneous core functions of AutoPkg."""

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

    # Tests for get_info function
    def test_get_info_no_arguments_prints_tool_info(self):
        """Test get_info with no arguments prints tool info."""
        argv = ["autopkg", "info"]

        with patch("autopkg.gen_common_parser") as mock_parser_gen, patch(
            "autopkg.add_search_and_override_dir_options"
        ), patch("autopkg.common_parse") as mock_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.print_tool_info"
        ) as mock_print_tool_info:

            mock_parser = unittest.mock.Mock()
            mock_parser.add_option = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_options.quiet = False
            mock_options.pull = False
            mock_parse.return_value = (mock_options, [])  # No arguments

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]

            result = autopkg.get_info(argv)

            self.assertEqual(result, 0)
            mock_print_tool_info.assert_called_once_with(mock_options)

    def test_get_info_single_recipe_found(self):
        """Test get_info with single recipe that is found."""
        argv = ["autopkg", "info", "TestRecipe"]

        with patch("autopkg.gen_common_parser") as mock_parser_gen, patch(
            "autopkg.add_search_and_override_dir_options"
        ), patch("autopkg.common_parse") as mock_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.get_recipe_info"
        ) as mock_get_recipe_info:

            mock_parser = unittest.mock.Mock()
            mock_parser.add_option = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_options.quiet = False
            mock_options.pull = False
            mock_parse.return_value = (mock_options, ["TestRecipe"])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]
            mock_get_recipe_info.return_value = True  # Recipe found

            result = autopkg.get_info(argv)

            self.assertEqual(result, 0)
            mock_get_recipe_info.assert_called_once_with(
                "TestRecipe",
                ["/overrides"],
                ["/recipes"],
                make_suggestions=True,
                search_github=True,
                auto_pull=False,
            )

    def test_get_info_single_recipe_not_found(self):
        """Test get_info with single recipe that is not found."""
        argv = ["autopkg", "info", "NonExistentRecipe"]

        with patch("autopkg.gen_common_parser") as mock_parser_gen, patch(
            "autopkg.add_search_and_override_dir_options"
        ), patch("autopkg.common_parse") as mock_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.get_recipe_info"
        ) as mock_get_recipe_info:

            mock_parser = unittest.mock.Mock()
            mock_parser.add_option = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_options.quiet = False
            mock_options.pull = False
            mock_parse.return_value = (mock_options, ["NonExistentRecipe"])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]
            mock_get_recipe_info.return_value = False  # Recipe not found

            result = autopkg.get_info(argv)

            self.assertEqual(result, -1)
            mock_get_recipe_info.assert_called_once_with(
                "NonExistentRecipe",
                ["/overrides"],
                ["/recipes"],
                make_suggestions=True,
                search_github=True,
                auto_pull=False,
            )

    def test_get_info_too_many_arguments(self):
        """Test get_info with too many arguments."""
        argv = ["autopkg", "info", "Recipe1", "Recipe2"]

        with patch("autopkg.gen_common_parser") as mock_parser_gen, patch(
            "autopkg.add_search_and_override_dir_options"
        ), patch("autopkg.common_parse") as mock_parse, patch(
            "autopkg.log_err"
        ) as mock_log_err:

            mock_parser = unittest.mock.Mock()
            mock_parser.add_option = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_parse.return_value = (mock_options, ["Recipe1", "Recipe2"])

            result = autopkg.get_info(argv)

            self.assertEqual(result, -1)
            mock_log_err.assert_called_once_with("Too many recipes!")

    def test_get_info_with_custom_override_dirs(self):
        """Test get_info with custom override directories."""
        argv = ["autopkg", "info", "TestRecipe"]

        with patch("autopkg.gen_common_parser") as mock_parser_gen, patch(
            "autopkg.add_search_and_override_dir_options"
        ), patch("autopkg.common_parse") as mock_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.get_recipe_info"
        ) as mock_get_recipe_info:

            mock_parser = unittest.mock.Mock()
            mock_parser.add_option = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.override_dirs = ["/custom/overrides"]
            mock_options.search_dirs = None
            mock_options.quiet = False
            mock_options.pull = False
            mock_parse.return_value = (mock_options, ["TestRecipe"])

            mock_get_override_dirs.return_value = ["/default/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]
            mock_get_recipe_info.return_value = True

            result = autopkg.get_info(argv)

            self.assertEqual(result, 0)
            mock_get_recipe_info.assert_called_once_with(
                "TestRecipe",
                ["/custom/overrides"],  # Should use custom override dirs
                ["/recipes"],
                make_suggestions=True,
                search_github=True,
                auto_pull=False,
            )

    def test_get_info_with_custom_search_dirs(self):
        """Test get_info with custom search directories."""
        argv = ["autopkg", "info", "TestRecipe"]

        with patch("autopkg.gen_common_parser") as mock_parser_gen, patch(
            "autopkg.add_search_and_override_dir_options"
        ), patch("autopkg.common_parse") as mock_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.get_recipe_info"
        ) as mock_get_recipe_info:

            mock_parser = unittest.mock.Mock()
            mock_parser.add_option = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.override_dirs = None
            mock_options.search_dirs = ["/custom/recipes"]
            mock_options.quiet = False
            mock_options.pull = False
            mock_parse.return_value = (mock_options, ["TestRecipe"])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/default/recipes"]
            mock_get_recipe_info.return_value = True

            result = autopkg.get_info(argv)

            self.assertEqual(result, 0)
            mock_get_recipe_info.assert_called_once_with(
                "TestRecipe",
                ["/overrides"],
                ["/custom/recipes"],  # Should use custom search dirs
                make_suggestions=True,
                search_github=True,
                auto_pull=False,
            )

    def test_get_info_with_quiet_option(self):
        """Test get_info with quiet option disables suggestions and GitHub search."""
        argv = ["autopkg", "info", "TestRecipe"]

        with patch("autopkg.gen_common_parser") as mock_parser_gen, patch(
            "autopkg.add_search_and_override_dir_options"
        ), patch("autopkg.common_parse") as mock_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.get_recipe_info"
        ) as mock_get_recipe_info:

            mock_parser = unittest.mock.Mock()
            mock_parser.add_option = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_options.quiet = True
            mock_options.pull = False
            mock_parse.return_value = (mock_options, ["TestRecipe"])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]
            mock_get_recipe_info.return_value = True

            result = autopkg.get_info(argv)

            self.assertEqual(result, 0)
            mock_get_recipe_info.assert_called_once_with(
                "TestRecipe",
                ["/overrides"],
                ["/recipes"],
                make_suggestions=False,  # Should be False when quiet=True
                search_github=False,  # Should be False when quiet=True
                auto_pull=False,
            )

    def test_get_info_with_pull_option(self):
        """Test get_info with pull option enables auto-pull."""
        argv = ["autopkg", "info", "TestRecipe"]

        with patch("autopkg.gen_common_parser") as mock_parser_gen, patch(
            "autopkg.add_search_and_override_dir_options"
        ), patch("autopkg.common_parse") as mock_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.get_recipe_info"
        ) as mock_get_recipe_info:

            mock_parser = unittest.mock.Mock()
            mock_parser.add_option = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_options.quiet = False
            mock_options.pull = True
            mock_parse.return_value = (mock_options, ["TestRecipe"])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]
            mock_get_recipe_info.return_value = True

            result = autopkg.get_info(argv)

            self.assertEqual(result, 0)
            mock_get_recipe_info.assert_called_once_with(
                "TestRecipe",
                ["/overrides"],
                ["/recipes"],
                make_suggestions=True,
                search_github=True,
                auto_pull=True,  # Should be True when pull=True
            )

    def test_get_info_with_both_quiet_and_pull_options(self):
        """Test get_info with both quiet and pull options."""
        argv = ["autopkg", "info", "TestRecipe"]

        with patch("autopkg.gen_common_parser") as mock_parser_gen, patch(
            "autopkg.add_search_and_override_dir_options"
        ), patch("autopkg.common_parse") as mock_parse, patch(
            "autopkg.get_override_dirs"
        ) as mock_get_override_dirs, patch(
            "autopkg.get_search_dirs"
        ) as mock_get_search_dirs, patch(
            "autopkg.get_recipe_info"
        ) as mock_get_recipe_info:

            mock_parser = unittest.mock.Mock()
            mock_parser.add_option = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_options.quiet = True
            mock_options.pull = True
            mock_parse.return_value = (mock_options, ["TestRecipe"])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/recipes"]
            mock_get_recipe_info.return_value = True

            result = autopkg.get_info(argv)

            self.assertEqual(result, 0)
            mock_get_recipe_info.assert_called_once_with(
                "TestRecipe",
                ["/overrides"],
                ["/recipes"],
                make_suggestions=False,  # Quiet takes precedence
                search_github=False,  # Quiet takes precedence
                auto_pull=True,  # Pull option still honored
            )

    def test_get_info_parser_setup(self):
        """Test get_info sets up parser correctly."""
        argv = ["autopkg", "info"]

        with patch("autopkg.gen_common_parser") as mock_parser_gen, patch(
            "autopkg.add_search_and_override_dir_options"
        ) as mock_add_options, patch("autopkg.common_parse") as mock_parse, patch(
            "autopkg.get_override_dirs"
        ), patch(
            "autopkg.get_search_dirs"
        ), patch(
            "autopkg.print_tool_info"
        ):

            mock_parser = unittest.mock.Mock()
            mock_parser.add_option = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_options.quiet = False
            mock_options.pull = False
            mock_parse.return_value = (mock_options, [])

            autopkg.get_info(argv)

            # Verify parser setup
            mock_parser_gen.assert_called_once()
            mock_parser.set_usage.assert_called_once_with(
                "Usage: %prog info [options] [recipe]"
            )
            mock_add_options.assert_called_once_with(mock_parser)

            # Verify options were added
            self.assertEqual(mock_parser.add_option.call_count, 2)

            # Check quiet option
            quiet_call = mock_parser.add_option.call_args_list[0]
            self.assertEqual(quiet_call[0], ("-q", "--quiet"))
            self.assertTrue(quiet_call[1]["action"] == "store_true")

            # Check pull option
            pull_call = mock_parser.add_option.call_args_list[1]
            self.assertEqual(pull_call[0], ("-p", "--pull"))
            self.assertTrue(pull_call[1]["action"] == "store_true")


if __name__ == "__main__":
    unittest.main()
