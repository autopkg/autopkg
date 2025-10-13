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

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.print_tool_info") as mock_print_tool_info,
        ):

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

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_recipe_info") as mock_get_recipe_info,
        ):

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

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_recipe_info") as mock_get_recipe_info,
        ):

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

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.log_err") as mock_log_err,
        ):

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

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_recipe_info") as mock_get_recipe_info,
        ):

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

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_recipe_info") as mock_get_recipe_info,
        ):

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

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_recipe_info") as mock_get_recipe_info,
        ):

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

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_recipe_info") as mock_get_recipe_info,
        ):

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

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_recipe_info") as mock_get_recipe_info,
        ):

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

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options") as mock_add_options,
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.get_override_dirs"),
            patch("autopkg.get_search_dirs"),
            patch("autopkg.print_tool_info"),
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

    def test_processor_info_basic_functionality(self):
        """Test processor_info with a basic processor."""
        argv = ["autopkg", "processor-info", "URLDownloader"]

        # Mock processor class
        mock_processor = unittest.mock.Mock()
        mock_processor.description = "Downloads URLs to a file"
        mock_processor.input_variables = {
            "url": {"required": True, "description": "URL to download"},
            "filename": {"required": False, "description": "Output filename"},
        }
        mock_processor.output_variables = {
            "pathname": {"description": "Path to downloaded file"}
        }

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_processor") as mock_get_processor,
            patch("builtins.print") as mock_print,
        ):

            mock_parser = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.recipe = None
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, ["URLDownloader"])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/search"]
            mock_get_processor.return_value = mock_processor

            result = autopkg.processor_info(argv)

            # Should return None (no explicit return)
            self.assertIsNone(result)

            # Verify parser setup
            mock_parser.set_usage.assert_called_once()
            mock_parser.add_option.assert_called_once_with(
                "-r",
                "--recipe",
                metavar="RECIPE",
                help="Name of recipe using the processor.",
            )

            # Verify processor lookup
            mock_get_processor.assert_called_once_with("URLDownloader", recipe=None)

            # Verify output
            mock_print.assert_any_call("Description: Downloads URLs to a file")
            mock_print.assert_any_call("Input variables:")
            mock_print.assert_any_call("Output variables:")

    def test_processor_info_with_recipe_option(self):
        """Test processor_info with recipe option."""
        argv = ["autopkg", "processor-info", "-r", "TestRecipe", "URLDownloader"]

        mock_processor = unittest.mock.Mock()
        mock_processor.description = "Downloads URLs"
        mock_processor.input_variables = {}
        mock_processor.output_variables = {}

        mock_recipe = {"Process": []}

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.load_recipe") as mock_load_recipe,
            patch("autopkg.get_processor") as mock_get_processor,
            patch("builtins.print"),
        ):

            mock_parser = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.recipe = "TestRecipe"
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, ["URLDownloader"])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/search"]
            mock_load_recipe.return_value = mock_recipe
            mock_get_processor.return_value = mock_processor

            result = autopkg.processor_info(argv)

            self.assertIsNone(result)

            # Verify recipe was loaded
            mock_load_recipe.assert_called_once_with(
                "TestRecipe", ["/overrides"], ["/search"]
            )

            # Verify processor lookup with recipe
            mock_get_processor.assert_called_once_with(
                "URLDownloader", recipe=mock_recipe
            )

    def test_processor_info_no_arguments(self):
        """Test processor_info with no processor name."""
        argv = ["autopkg", "processor-info"]

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.log_err") as mock_log_err,
        ):

            mock_parser = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.recipe = None
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, [])

            result = autopkg.processor_info(argv)

            self.assertEqual(result, -1)
            mock_log_err.assert_called_once_with("Need exactly one processor name")

    def test_processor_info_too_many_arguments(self):
        """Test processor_info with too many arguments."""
        argv = ["autopkg", "processor-info", "URLDownloader", "ExtraArg"]

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.log_err") as mock_log_err,
        ):

            mock_parser = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.recipe = None
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (
                mock_options,
                ["URLDownloader", "ExtraArg"],
            )

            result = autopkg.processor_info(argv)

            self.assertEqual(result, -1)
            mock_log_err.assert_called_once_with("Need exactly one processor name")

    def test_processor_info_unknown_processor(self):
        """Test processor_info with unknown processor."""
        argv = ["autopkg", "processor-info", "UnknownProcessor"]

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_processor") as mock_get_processor,
            patch("autopkg.log_err") as mock_log_err,
        ):

            mock_parser = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.recipe = None
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, ["UnknownProcessor"])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/search"]
            mock_get_processor.side_effect = KeyError("Unknown processor")

            result = autopkg.processor_info(argv)

            self.assertEqual(result, -1)
            mock_log_err.assert_called_once_with("Unknown processor 'UnknownProcessor'")

    def test_processor_info_attribute_error(self):
        """Test processor_info when get_processor raises AttributeError."""
        argv = ["autopkg", "processor-info", "BadProcessor"]

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_processor") as mock_get_processor,
            patch("autopkg.log_err") as mock_log_err,
        ):

            mock_parser = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.recipe = None
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, ["BadProcessor"])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/search"]
            mock_get_processor.side_effect = AttributeError("Bad attribute")

            result = autopkg.processor_info(argv)

            self.assertEqual(result, -1)
            mock_log_err.assert_called_once_with("Unknown processor 'BadProcessor'")

    def test_processor_info_no_description_attribute(self):
        """Test processor_info with processor that has no description attribute."""
        argv = ["autopkg", "processor-info", "NoDescProcessor"]

        # Mock processor with __doc__ but no description
        mock_processor = unittest.mock.Mock()
        del mock_processor.description  # Remove description attribute
        mock_processor.__doc__ = "Processor documentation"
        mock_processor.input_variables = {}
        mock_processor.output_variables = {}

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_processor") as mock_get_processor,
            patch("builtins.print") as mock_print,
        ):

            mock_parser = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.recipe = None
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, ["NoDescProcessor"])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/search"]
            mock_get_processor.return_value = mock_processor

            result = autopkg.processor_info(argv)

            self.assertIsNone(result)
            # Should use __doc__ as fallback
            mock_print.assert_any_call("Description: Processor documentation")

    def test_processor_info_no_description_or_doc(self):
        """Test processor_info with processor that has no description or __doc__."""
        argv = ["autopkg", "processor-info", "NoDescProcessor"]

        # Mock processor with neither description nor __doc__
        mock_processor = unittest.mock.Mock()
        del mock_processor.description
        del mock_processor.__doc__
        mock_processor.input_variables = {}
        mock_processor.output_variables = {}

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_processor") as mock_get_processor,
            patch("builtins.print") as mock_print,
        ):

            mock_parser = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.recipe = None
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, ["NoDescProcessor"])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/search"]
            mock_get_processor.return_value = mock_processor

            result = autopkg.processor_info(argv)

            self.assertIsNone(result)
            # Should use empty string as fallback
            print_calls = [str(call) for call in mock_print.call_args_list]
            self.assertTrue(any("Description:" in call for call in print_calls))

    def test_processor_info_no_input_variables(self):
        """Test processor_info with processor that has no input_variables."""
        argv = ["autopkg", "processor-info", "NoInputProcessor"]

        mock_processor = unittest.mock.Mock()
        mock_processor.description = "Test processor"
        del mock_processor.input_variables  # Remove input_variables attribute
        mock_processor.output_variables = {}

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_processor") as mock_get_processor,
            patch("builtins.print") as mock_print,
        ):

            mock_parser = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.recipe = None
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, ["NoInputProcessor"])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/search"]
            mock_get_processor.return_value = mock_processor

            result = autopkg.processor_info(argv)

            self.assertIsNone(result)
            # Should handle missing input_variables gracefully
            mock_print.assert_any_call("Input variables:")

    def test_processor_info_no_output_variables(self):
        """Test processor_info with processor that has no output_variables."""
        argv = ["autopkg", "processor-info", "NoOutputProcessor"]

        mock_processor = unittest.mock.Mock()
        mock_processor.description = "Test processor"
        mock_processor.input_variables = {}
        del mock_processor.output_variables  # Remove output_variables attribute

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_processor") as mock_get_processor,
            patch("builtins.print") as mock_print,
        ):

            mock_parser = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.recipe = None
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, ["NoOutputProcessor"])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/search"]
            mock_get_processor.return_value = mock_processor

            result = autopkg.processor_info(argv)

            self.assertIsNone(result)
            # Should handle missing output_variables gracefully
            mock_print.assert_any_call("Output variables:")

    def test_processor_info_complex_variables(self):
        """Test processor_info with complex nested variables."""
        argv = ["autopkg", "processor-info", "ComplexProcessor"]

        mock_processor = unittest.mock.Mock()
        mock_processor.description = "Complex processor"
        mock_processor.input_variables = {
            "simple_var": {"required": True, "description": "Simple variable"},
            "complex_var": {
                "required": False,
                "description": "Complex variable",
                "default": {
                    "nested": "value",
                    "list": ["item1", "item2"],
                },
            },
        }
        mock_processor.output_variables = {
            "result": {"description": "Output result"},
            "metadata": {
                "description": "Metadata object",
                "type": {
                    "name": "string",
                    "version": "string",
                },
            },
        }

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_processor") as mock_get_processor,
            patch("builtins.print") as mock_print,
        ):

            mock_parser = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.recipe = None
            mock_options.override_dirs = None
            mock_options.search_dirs = None
            mock_common_parse.return_value = (mock_options, ["ComplexProcessor"])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/search"]
            mock_get_processor.return_value = mock_processor

            result = autopkg.processor_info(argv)

            self.assertIsNone(
                result
            )  # Verify that complex variables are printed with proper indentation
            print_calls = [str(call) for call in mock_print.call_args_list]

            # Check that nested structures are handled - print_vars uses multiple args
            found_calls = []
            for call_str in print_calls:
                if (
                    "simple_var" in call_str
                    or "complex_var" in call_str
                    or "result" in call_str
                    or "metadata" in call_str
                ):
                    found_calls.append(call_str)

            # Should have found some variable calls
            self.assertGreater(len(found_calls), 0)

    def test_processor_info_with_custom_directories(self):
        """Test processor_info with custom override and search directories."""
        argv = [
            "autopkg",
            "processor-info",
            "--override-dirs",
            "/custom/overrides",
            "--search-dirs",
            "/custom/search",
            "TestProcessor",
        ]

        mock_processor = unittest.mock.Mock()
        mock_processor.description = "Test processor"
        mock_processor.input_variables = {}
        mock_processor.output_variables = {}

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_processor") as mock_get_processor,
            patch("builtins.print"),
        ):

            mock_parser = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_options.recipe = None
            mock_options.override_dirs = ["/custom/overrides"]
            mock_options.search_dirs = ["/custom/search"]
            mock_common_parse.return_value = (mock_options, ["TestProcessor"])

            mock_get_processor.return_value = mock_processor

            result = autopkg.processor_info(argv)

            self.assertIsNone(result)

            # Verify that custom directories are used (not the default functions)
            mock_get_processor.assert_called_once_with("TestProcessor", recipe=None)

    def test_list_processors_basic_functionality(self):
        """Test list_processors basic functionality."""
        argv = ["autopkg", "list-processors"]

        mock_processor_names = ["URLDownloader", "CodeSignatureVerifier", "Copier"]

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.processor_names") as mock_processor_names_func,
            patch("builtins.print") as mock_print,
        ):

            mock_parser = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_common_parse.return_value = (mock_options, [])

            mock_processor_names_func.return_value = mock_processor_names

            result = autopkg.list_processors(argv)

            # Should return None (no explicit return)
            self.assertIsNone(result)

            # Verify parser setup
            mock_parser.set_usage.assert_called_once()
            usage_call = mock_parser.set_usage.call_args[0][0]
            self.assertIn("Usage: %prog list-processors [options]", usage_call)
            self.assertIn("List the core Processors.", usage_call)

            # Verify processor_names was called
            mock_processor_names_func.assert_called_once()

            # Verify output - processors should be printed in sorted order
            expected_output = "\n".join(sorted(mock_processor_names))
            mock_print.assert_called_once_with(expected_output)

    def test_list_processors_sorted_output(self):
        """Test that list_processors outputs processors in sorted order."""
        argv = ["autopkg", "list-processors"]

        # Unsorted list of processors
        mock_processor_names = ["ZebraProcessor", "AlphaProcessor", "BetaProcessor"]

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.processor_names") as mock_processor_names_func,
            patch("builtins.print") as mock_print,
        ):

            mock_parser = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_common_parse.return_value = (mock_options, [])

            mock_processor_names_func.return_value = mock_processor_names

            autopkg.list_processors(argv)

            # Should print in alphabetical order
            expected_output = "AlphaProcessor\nBetaProcessor\nZebraProcessor"
            mock_print.assert_called_once_with(expected_output)

    def test_list_processors_empty_list(self):
        """Test list_processors with empty processor list."""
        argv = ["autopkg", "list-processors"]

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.processor_names") as mock_processor_names_func,
            patch("builtins.print") as mock_print,
        ):

            mock_parser = unittest.mock.Mock()
            mock_parser_gen.return_value = mock_parser

            mock_options = unittest.mock.Mock()
            mock_common_parse.return_value = (mock_options, [])

            mock_processor_names_func.return_value = []

            autopkg.list_processors(argv)

            # Should print empty string
            mock_print.assert_called_once_with("")

    def test_find_processor_path_basic_functionality(self):
        """Test find_processor_path with basic recipe and processor."""
        processor_name = "TestProcessor"
        recipe = {"RECIPE_PATH": "/recipes/TestApp.recipe"}
        env = {"RECIPE_SEARCH_DIRS": ["/search/dir1", "/search/dir2"]}

        with (
            patch("os.path.dirname") as mock_dirname,
            patch(
                "autopkg.extract_processor_name_with_recipe_identifier"
            ) as mock_extract,
            patch("os.path.exists") as mock_exists,
            patch("os.path.join") as mock_join,
        ):

            mock_dirname.return_value = "/recipes"
            mock_extract.return_value = ("TestProcessor", None)
            mock_exists.return_value = True
            mock_join.return_value = "/recipes/TestProcessor.py"

            result = autopkg.find_processor_path(processor_name, recipe, env)

            self.assertEqual(result, "/recipes/TestProcessor.py")

            # Verify the function extracted processor name
            mock_extract.assert_called_once_with("TestProcessor")

            # Verify it checked if the processor file exists
            mock_exists.assert_called_with("/recipes/TestProcessor.py")

    def test_find_processor_path_no_recipe(self):
        """Test find_processor_path when no recipe is provided."""
        processor_name = "TestProcessor"
        recipe = None
        env = None

        result = autopkg.find_processor_path(processor_name, recipe, env)

        # Should return None when no recipe is provided
        self.assertIsNone(result)

    def test_find_processor_path_processor_not_found(self):
        """Test find_processor_path when processor file doesn't exist."""
        processor_name = "NonExistentProcessor"
        recipe = {"RECIPE_PATH": "/recipes/TestApp.recipe"}
        env = {"RECIPE_SEARCH_DIRS": ["/search/dir1"]}

        with (
            patch("os.path.dirname") as mock_dirname,
            patch(
                "autopkg.extract_processor_name_with_recipe_identifier"
            ) as mock_extract,
            patch("os.path.exists") as mock_exists,
        ):

            mock_dirname.return_value = "/recipes"
            mock_extract.return_value = ("NonExistentProcessor", None)
            mock_exists.return_value = False  # Processor file doesn't exist

            result = autopkg.find_processor_path(processor_name, recipe, env)

            self.assertIsNone(result)

    def test_find_processor_path_with_recipe_identifier(self):
        """Test find_processor_path with processor name that includes recipe identifier."""
        processor_name = "com.example.recipes.shared/CustomProcessor"
        recipe = {"RECIPE_PATH": "/recipes/TestApp.recipe"}
        env = {"RECIPE_SEARCH_DIRS": ["/search/dir1", "/search/dir2"]}

        with (
            patch("os.path.dirname") as mock_dirname,
            patch(
                "autopkg.extract_processor_name_with_recipe_identifier"
            ) as mock_extract,
            patch("autopkg.find_recipe_by_identifier") as mock_find_recipe,
            patch("os.path.exists") as mock_exists,
            patch("os.path.join") as mock_join,
        ):

            mock_dirname.side_effect = lambda path: {
                "/recipes/TestApp.recipe": "/recipes",
                "/shared/SharedRecipe.recipe": "/shared",
            }.get(path, "/default")

            mock_extract.return_value = (
                "CustomProcessor",
                "com.example.recipes.shared",
            )
            mock_find_recipe.return_value = "/shared/SharedRecipe.recipe"
            mock_exists.side_effect = lambda path: path == "/shared/CustomProcessor.py"
            mock_join.side_effect = lambda *args: "/".join(args)

            result = autopkg.find_processor_path(processor_name, recipe, env)

            self.assertEqual(result, "/shared/CustomProcessor.py")

            # Verify it searched for the shared recipe
            mock_find_recipe.assert_called_once_with(
                "com.example.recipes.shared", ["/search/dir1", "/search/dir2"]
            )

    def test_find_processor_path_with_parent_recipes(self):
        """Test find_processor_path with recipe that has parent recipes."""
        processor_name = "TestProcessor"
        recipe = {
            "RECIPE_PATH": "/recipes/TestApp.recipe",
            "PARENT_RECIPES": [
                "/parent1/Parent1.recipe",
                "/parent2/Parent2.recipe",
                "/parent1/AnotherParent.recipe",  # Same dir as first parent
            ],
        }
        env = {"RECIPE_SEARCH_DIRS": ["/search/dir1"]}

        with (
            patch("os.path.dirname") as mock_dirname,
            patch(
                "autopkg.extract_processor_name_with_recipe_identifier"
            ) as mock_extract,
            patch("os.path.exists") as mock_exists,
            patch("os.path.join") as mock_join,
        ):

            def dirname_side_effect(path):
                dirname_map = {
                    "/recipes/TestApp.recipe": "/recipes",
                    "/parent1/Parent1.recipe": "/parent1",
                    "/parent2/Parent2.recipe": "/parent2",
                    "/parent1/AnotherParent.recipe": "/parent1",
                }
                return dirname_map.get(path, "/default")

            mock_dirname.side_effect = dirname_side_effect
            mock_extract.return_value = ("TestProcessor", None)

            # Make processor exist in parent2 directory
            mock_exists.side_effect = lambda path: path == "/parent2/TestProcessor.py"
            mock_join.side_effect = lambda *args: "/".join(args)

            result = autopkg.find_processor_path(processor_name, recipe, env)

            self.assertEqual(result, "/parent2/TestProcessor.py")

    def test_find_processor_path_no_env_provided(self):
        """Test find_processor_path when no env is provided."""
        processor_name = "TestProcessor"
        recipe = {"RECIPE_PATH": "/recipes/TestApp.recipe"}
        env = None

        with (
            patch("autopkg.get_pref") as mock_get_pref,
            patch("os.path.dirname") as mock_dirname,
            patch(
                "autopkg.extract_processor_name_with_recipe_identifier"
            ) as mock_extract,
            patch("os.path.exists") as mock_exists,
            patch("os.path.join") as mock_join,
        ):

            mock_get_pref.return_value = ["/default/search/dir"]
            mock_dirname.return_value = "/recipes"
            mock_extract.return_value = ("TestProcessor", None)
            mock_exists.return_value = True
            mock_join.return_value = "/recipes/TestProcessor.py"

            result = autopkg.find_processor_path(processor_name, recipe, env)

            self.assertEqual(result, "/recipes/TestProcessor.py")

            # Verify it got default search dirs from preferences
            mock_get_pref.assert_called_once_with("RECIPE_SEARCH_DIRS")

    def test_find_processor_path_search_multiple_directories(self):
        """Test find_processor_path searches multiple directories in order."""
        processor_name = "TestProcessor"
        recipe = {
            "RECIPE_PATH": "/recipes/TestApp.recipe",
            "PARENT_RECIPES": ["/parent/Parent.recipe"],
        }
        env = {"RECIPE_SEARCH_DIRS": ["/search/dir1"]}

        with (
            patch("os.path.dirname") as mock_dirname,
            patch(
                "autopkg.extract_processor_name_with_recipe_identifier"
            ) as mock_extract,
            patch("os.path.exists") as mock_exists,
            patch("os.path.join") as mock_join,
        ):

            mock_dirname.side_effect = lambda path: {
                "/recipes/TestApp.recipe": "/recipes",
                "/parent/Parent.recipe": "/parent",
            }.get(path, "/default")

            mock_extract.return_value = ("TestProcessor", None)

            # Make processor exist only in parent directory (second search location)
            def exists_side_effect(path):
                return path == "/parent/TestProcessor.py"

            mock_exists.side_effect = exists_side_effect
            mock_join.side_effect = lambda *args: "/".join(args)

            result = autopkg.find_processor_path(processor_name, recipe, env)

            self.assertEqual(result, "/parent/TestProcessor.py")

            # Verify it checked recipe directory first, then parent directory
            expected_calls = [
                unittest.mock.call("/recipes/TestProcessor.py"),
                unittest.mock.call("/parent/TestProcessor.py"),
            ]
            mock_exists.assert_has_calls(expected_calls)

    def test_find_processor_path_shared_recipe_not_found(self):
        """Test find_processor_path when shared recipe is not found."""
        processor_name = "com.missing.recipe/TestProcessor"
        recipe = {"RECIPE_PATH": "/recipes/TestApp.recipe"}
        env = {"RECIPE_SEARCH_DIRS": ["/search/dir1"]}

        with (
            patch("os.path.dirname") as mock_dirname,
            patch(
                "autopkg.extract_processor_name_with_recipe_identifier"
            ) as mock_extract,
            patch("autopkg.find_recipe_by_identifier") as mock_find_recipe,
            patch("os.path.exists") as mock_exists,
            patch("os.path.join") as mock_join,
        ):

            mock_dirname.return_value = "/recipes"
            mock_extract.return_value = ("TestProcessor", "com.missing.recipe")
            mock_find_recipe.return_value = None  # Shared recipe not found
            mock_exists.return_value = False
            mock_join.side_effect = lambda *args: "/".join(args)

            result = autopkg.find_processor_path(processor_name, recipe, env)

            self.assertIsNone(result)

            # Should still search for processor in recipe directory
            mock_exists.assert_called_with("/recipes/TestProcessor.py")

    def test_find_processor_path_empty_parent_recipes(self):
        """Test find_processor_path with empty parent recipes list."""
        processor_name = "TestProcessor"
        recipe = {
            "RECIPE_PATH": "/recipes/TestApp.recipe",
            "PARENT_RECIPES": [],  # Empty list
        }
        env = {"RECIPE_SEARCH_DIRS": ["/search/dir1"]}

        with (
            patch("os.path.dirname") as mock_dirname,
            patch(
                "autopkg.extract_processor_name_with_recipe_identifier"
            ) as mock_extract,
            patch("os.path.exists") as mock_exists,
            patch("os.path.join") as mock_join,
        ):

            mock_dirname.return_value = "/recipes"
            mock_extract.return_value = ("TestProcessor", None)
            mock_exists.return_value = True
            mock_join.return_value = "/recipes/TestProcessor.py"

            result = autopkg.find_processor_path(processor_name, recipe, env)

            self.assertEqual(result, "/recipes/TestProcessor.py")

            # Should only check recipe directory
            mock_exists.assert_called_once_with("/recipes/TestProcessor.py")

    def test_find_processor_path_complex_scenario(self):
        """Test find_processor_path with a complex scenario involving all features."""
        processor_name = "com.shared.recipes/CustomProcessor"
        recipe = {
            "RECIPE_PATH": "/main/TestApp.recipe",
            "PARENT_RECIPES": ["/parent1/Parent1.recipe", "/parent2/Parent2.recipe"],
        }
        env = {"RECIPE_SEARCH_DIRS": ["/search1", "/search2"]}

        with (
            patch("os.path.dirname") as mock_dirname,
            patch(
                "autopkg.extract_processor_name_with_recipe_identifier"
            ) as mock_extract,
            patch("autopkg.find_recipe_by_identifier") as mock_find_recipe,
            patch("os.path.exists") as mock_exists,
            patch("os.path.join") as mock_join,
        ):

            def dirname_side_effect(path):
                dirname_map = {
                    "/main/TestApp.recipe": "/main",
                    "/parent1/Parent1.recipe": "/parent1",
                    "/parent2/Parent2.recipe": "/parent2",
                    "/shared/SharedRecipe.recipe": "/shared",
                }
                return dirname_map.get(path, "/default")

            mock_dirname.side_effect = dirname_side_effect
            mock_extract.return_value = ("CustomProcessor", "com.shared.recipes")
            mock_find_recipe.return_value = "/shared/SharedRecipe.recipe"

            # Make processor exist in shared directory
            def exists_side_effect(path):
                return path == "/shared/CustomProcessor.py"

            mock_exists.side_effect = exists_side_effect
            mock_join.side_effect = lambda *args: "/".join(args)

            result = autopkg.find_processor_path(processor_name, recipe, env)

            self.assertEqual(result, "/shared/CustomProcessor.py")

            # Verify the search order: recipe dir, shared dir, parent dirs
            expected_calls = [
                unittest.mock.call("/main/CustomProcessor.py"),
                unittest.mock.call(
                    "/shared/CustomProcessor.py"
                ),  # Found here, so stops
            ]
            mock_exists.assert_has_calls(expected_calls[:2])

    def test_find_processor_path_get_pref_returns_none(self):
        """Test find_processor_path when get_pref returns None for search dirs."""
        processor_name = "TestProcessor"
        recipe = {"RECIPE_PATH": "/recipes/TestApp.recipe"}
        env = None

        with (
            patch("autopkg.get_pref") as mock_get_pref,
            patch("os.path.dirname") as mock_dirname,
            patch(
                "autopkg.extract_processor_name_with_recipe_identifier"
            ) as mock_extract,
            patch("os.path.exists") as mock_exists,
            patch("os.path.join") as mock_join,
        ):

            mock_get_pref.return_value = None  # No search dirs in prefs
            mock_dirname.return_value = "/recipes"
            mock_extract.return_value = ("TestProcessor", None)
            mock_exists.return_value = True
            mock_join.return_value = "/recipes/TestProcessor.py"

            result = autopkg.find_processor_path(processor_name, recipe, env)

            self.assertEqual(result, "/recipes/TestProcessor.py")

            # Should still work with empty search dirs list
            mock_get_pref.assert_called_once_with("RECIPE_SEARCH_DIRS")

    def test_os_path_compressuser_exact_home(self):
        """Test os_path_compressuser when pathname exactly matches home directory."""
        home_dir = "/Users/testuser"

        with patch("os.path.expanduser", return_value=home_dir):
            result = autopkg.os_path_compressuser(home_dir)
            self.assertEqual(result, "~")

    def test_os_path_compressuser_subdirectory_of_home(self):
        """Test os_path_compressuser for paths inside home directory."""
        home_dir = "/Users/testuser"
        test_path = "/Users/testuser/Library/AutoPkg"

        with patch("os.path.expanduser", return_value=home_dir):
            with patch("os.path.relpath", return_value="Library/AutoPkg"):
                result = autopkg.os_path_compressuser(test_path)
                self.assertEqual(result, "~/Library/AutoPkg")

    def test_os_path_compressuser_path_not_in_home(self):
        """Test os_path_compressuser for paths outside home directory."""
        home_dir = "/Users/testuser"
        test_path = "/usr/local/bin/autopkg"

        with patch("os.path.expanduser", return_value=home_dir):
            result = autopkg.os_path_compressuser(test_path)
            self.assertEqual(result, test_path)

    def test_os_path_compressuser_empty_string(self):
        """Test os_path_compressuser with empty string."""
        home_dir = "/Users/testuser"

        with patch("os.path.expanduser", return_value=home_dir):
            result = autopkg.os_path_compressuser("")
            self.assertEqual(result, "")

    def test_os_path_compressuser_with_trailing_slash(self):
        """Test os_path_compressuser with home directory having trailing slash."""
        home_dir = "/Users/testuser/"
        test_path = "/Users/testuser/Library/AutoPkg/"

        with patch("os.path.expanduser", return_value=home_dir):
            with patch("os.path.relpath", return_value="Library/AutoPkg/"):
                result = autopkg.os_path_compressuser(test_path)
                self.assertEqual(result, "~/Library/AutoPkg/")

    def test_os_path_compressuser_nested_subdirectory(self):
        """Test os_path_compressuser for deeply nested paths in home."""
        home_dir = "/Users/testuser"
        test_path = (
            "/Users/testuser/Library/AutoPkg/Recipes/TestDev/TestApp.download.recipe"
        )

        with patch("os.path.expanduser", return_value=home_dir):
            with patch(
                "os.path.relpath",
                return_value="Library/AutoPkg/Recipes/TestDev/TestApp.download.recipe",
            ):
                result = autopkg.os_path_compressuser(test_path)
                self.assertEqual(
                    result,
                    "~/Library/AutoPkg/Recipes/TestDev/TestApp.download.recipe",
                )

    def test_os_path_compressuser_similar_path_not_in_home(self):
        """Test os_path_compressuser for path that starts with similar string but isn't in home."""
        home_dir = "/Users/testuser1"
        test_path = "/Users/testuser2/Documents"

        with patch("os.path.expanduser", return_value=home_dir):
            result = autopkg.os_path_compressuser(test_path)
            self.assertEqual(result, test_path)

    def test_os_path_compressuser_relative_path(self):
        """Test os_path_compressuser with relative path."""
        home_dir = "/Users/testuser"
        test_path = "Library/AutoPkg"

        with patch("os.path.expanduser", return_value=home_dir):
            result = autopkg.os_path_compressuser(test_path)
            self.assertEqual(result, test_path)

    def test_printplistitem_simple_string(self):
        """Test printplistitem with a simple string value."""
        with patch("autopkg.log") as mock_log:
            autopkg.printplistitem("test_key", "test_value", indent=0)
            mock_log.assert_called_once_with("test_key: test_value")

    def test_printplistitem_string_with_indent(self):
        """Test printplistitem with a string value and indentation."""
        with patch("autopkg.log") as mock_log:
            autopkg.printplistitem("test_key", "test_value", indent=2)
            mock_log.assert_called_once_with("        test_key: test_value")

    def test_printplistitem_none_value(self):
        """Test printplistitem with None value."""
        with patch("autopkg.log") as mock_log:
            autopkg.printplistitem("test_key", None, indent=0)
            mock_log.assert_called_once_with("test_key: !NONE!")

    def test_printplistitem_list_value(self):
        """Test printplistitem with a list value."""
        with patch("autopkg.log") as mock_log:
            test_list = ["item1", "item2", "item3"]
            autopkg.printplistitem("test_list", test_list, indent=0)

            # Check the calls made to log
            expected_calls = [
                unittest.mock.call("test_list:"),
                unittest.mock.call("    item1"),
                unittest.mock.call("    item2"),
                unittest.mock.call("    item3"),
            ]
            mock_log.assert_has_calls(expected_calls)

    def test_printplistitem_empty_list(self):
        """Test printplistitem with an empty list."""
        with patch("autopkg.log") as mock_log:
            autopkg.printplistitem("empty_list", [], indent=0)
            mock_log.assert_called_once_with("empty_list:")

    def test_printplistitem_dict_value(self):
        """Test printplistitem with a dictionary value."""
        with patch("autopkg.log") as mock_log:
            test_dict = {"key1": "value1", "key2": "value2"}
            autopkg.printplistitem("test_dict", test_dict, indent=0)

            # Check that the main label is printed
            mock_log.assert_any_call("test_dict:")

            # Check that dictionary items are printed with indentation
            mock_log.assert_any_call("    key1: value1")
            mock_log.assert_any_call("    key2: value2")

    def test_printplistitem_nested_dict(self):
        """Test printplistitem with nested dictionary."""
        with patch("autopkg.log") as mock_log:
            test_dict = {"outer_key": {"inner_key": "inner_value"}}
            autopkg.printplistitem("nested", test_dict, indent=0)

            expected_calls = [
                unittest.mock.call("nested:"),
                unittest.mock.call("    outer_key:"),
                unittest.mock.call("        inner_key: inner_value"),
            ]
            mock_log.assert_has_calls(expected_calls)

    def test_printplistitem_no_label_string(self):
        """Test printplistitem with empty label and string value."""
        with patch("autopkg.log") as mock_log:
            autopkg.printplistitem("", "test_value", indent=1)
            mock_log.assert_called_once_with("    test_value")

    def test_printplistitem_no_label_none(self):
        """Test printplistitem with empty label and None value."""
        with patch("autopkg.log") as mock_log:
            autopkg.printplistitem("", None, indent=1)
            mock_log.assert_called_once_with("    : !NONE!")

    def test_printplistitem_integer_value(self):
        """Test printplistitem with integer value."""
        with patch("autopkg.log") as mock_log:
            autopkg.printplistitem("number", 42, indent=0)
            mock_log.assert_called_once_with("number: 42")

    def test_printplistitem_boolean_value(self):
        """Test printplistitem with boolean value."""
        with patch("autopkg.log") as mock_log:
            autopkg.printplistitem("flag", True, indent=0)
            mock_log.assert_called_once_with("flag: True")

    def test_printplistitem_mixed_list(self):
        """Test printplistitem with list containing different data types."""
        with patch("autopkg.log") as mock_log:
            test_list = ["string", 42, True, None]
            autopkg.printplistitem("mixed", test_list, indent=0)

            expected_calls = [
                unittest.mock.call("mixed:"),
                unittest.mock.call("    string"),
                unittest.mock.call("    42"),
                unittest.mock.call("    True"),
                unittest.mock.call("    : !NONE!"),
            ]
            mock_log.assert_has_calls(expected_calls)

    def test_printplistitem_complex_nested_structure(self):
        """Test printplistitem with complex nested structure."""
        with patch("autopkg.log") as mock_log:
            complex_data = {
                "array": ["item1", "item2"],
                "nested_dict": {"inner_key": "inner_value", "inner_array": [1, 2, 3]},
                "simple": "value",
            }
            autopkg.printplistitem("complex", complex_data, indent=0)

            # Verify that the structure is printed correctly
            # (exact order may vary due to dict iteration)
            mock_log.assert_any_call("complex:")
            mock_log.assert_any_call("    simple: value")

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
