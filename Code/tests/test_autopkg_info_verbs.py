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

import os
import sys
import unittest
import unittest.mock
from unittest.mock import patch

# Add the Code directory to the Python path to resolve autopkg dependencies
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import autopkglib
from tests import load_autopkg_module

autopkg = load_autopkg_module()


class TestInfoVerbs(unittest.TestCase):
    """Test cases for the verbs that report on recipes and processors:
    `info`, `processor-info` and `list-processors`, plus the
    find_processor_path() resolution helper they share."""

    def setUp(self):
        """Silence recipe-map side effects (see test_autopkg_recipes for
        rationale)."""
        self._recipe_map_patches = [
            patch("autopkg.calculate_recipe_map"),
            patch("autopkglib.calculate_recipe_map"),
            patch("autopkg.read_recipe_map"),
        ]
        for patcher in self._recipe_map_patches:
            patcher.start()

    def tearDown(self):
        for patcher in self._recipe_map_patches:
            patcher.stop()

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

    def test_get_info_option_plumbing(self):
        """--quiet disables suggestions and GitHub search; --pull enables
        auto-pull; quiet takes precedence over pull for the first two."""
        cases = [
            # (quiet, pull, make_suggestions, search_github, auto_pull)
            (True, False, False, False, False),
            (False, True, True, True, True),
            (True, True, False, False, True),
        ]
        for quiet, pull, suggestions, search_github, auto_pull in cases:
            with self.subTest(quiet=quiet, pull=pull):
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
                    mock_options.quiet = quiet
                    mock_options.pull = pull
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
                        make_suggestions=suggestions,
                        search_github=search_github,
                        auto_pull=auto_pull,
                    )

    def test_get_info_usage_string_includes_verb_and_recipe_placeholder(self):
        """Test get_info sets a usage string naming the verb and a recipe placeholder."""
        argv = ["autopkg", "info"]

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
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

            mock_parser.set_usage.assert_called_once_with(
                "Usage: %prog info [options] [recipe]"
            )

    def test_get_info_registers_quiet_and_pull_options(self):
        """Test get_info registers -q/--quiet and -p/--pull as boolean flags."""
        argv = ["autopkg", "info"]

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
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

            self.assertEqual(mock_parser.add_option.call_count, 2)

            quiet_call = mock_parser.add_option.call_args_list[0]
            self.assertEqual(quiet_call[0], ("-q", "--quiet"))
            self.assertTrue(quiet_call[1]["action"] == "store_true")

            pull_call = mock_parser.add_option.call_args_list[1]
            self.assertEqual(pull_call[0], ("-p", "--pull"))
            self.assertTrue(pull_call[1]["action"] == "store_true")

    def test_processor_info_usage_string_includes_verb_and_processor_placeholder(self):
        """Test processor_info sets a usage string naming the verb and a processor placeholder."""
        argv = ["autopkg", "processor-info", "URLDownloader"]

        mock_processor = unittest.mock.Mock()
        mock_processor.description = "Downloads URLs to a file"
        mock_processor.input_variables = {}
        mock_processor.output_variables = {}

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_processor") as mock_get_processor,
            patch("builtins.print"),
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

            autopkg.processor_info(argv)

            mock_parser.set_usage.assert_called_once_with(
                "Usage: %prog processor-info [options] processorname"
            )

    def test_processor_info_registers_recipe_option(self):
        """Test processor_info registers -r/--recipe to scope the processor lookup to a recipe."""
        argv = ["autopkg", "processor-info", "URLDownloader"]

        mock_processor = unittest.mock.Mock()
        mock_processor.description = "Downloads URLs to a file"
        mock_processor.input_variables = {}
        mock_processor.output_variables = {}

        with (
            patch("autopkg.gen_common_parser") as mock_parser_gen,
            patch("autopkg.add_search_and_override_dir_options"),
            patch("autopkg.common_parse") as mock_common_parse,
            patch("autopkg.get_override_dirs") as mock_get_override_dirs,
            patch("autopkg.get_search_dirs") as mock_get_search_dirs,
            patch("autopkg.get_processor") as mock_get_processor,
            patch("builtins.print"),
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

            autopkg.processor_info(argv)

            mock_parser.add_option.assert_called_once_with(
                "-r",
                "--recipe",
                metavar="RECIPE",
                help="Name of recipe using the processor.",
            )

    def test_processor_info_prints_processor_description(self):
        """Test processor_info prints the processor's description text."""
        argv = ["autopkg", "processor-info", "URLDownloader"]

        mock_processor = unittest.mock.Mock()
        mock_processor.description = "Downloads URLs to a file"
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
            mock_common_parse.return_value = (mock_options, ["URLDownloader"])

            mock_get_override_dirs.return_value = ["/overrides"]
            mock_get_search_dirs.return_value = ["/search"]
            mock_get_processor.return_value = mock_processor

            result = autopkg.processor_info(argv)

            self.assertIsNone(result)
            mock_print.assert_any_call("Description: Downloads URLs to a file")

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
                "URLDownloader",
                recipe=mock_recipe,
                env={"RECIPE_SEARCH_DIRS": ["/search"]},
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

            self.assertIsNone(result)
            output = "\n".join(
                " ".join(str(arg) for arg in call.args)
                for call in mock_print.call_args_list
            )
            for expected in (
                "simple_var:",
                "complex_var:",
                "default:",
                "nested: value",
                "list: ['item1', 'item2']",
                "result:",
                "metadata:",
                "type:",
                "name: string",
                "version: string",
            ):
                self.assertIn(expected, output)

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
            mock_get_processor.assert_called_once_with(
                "TestProcessor",
                recipe=None,
                env={"RECIPE_SEARCH_DIRS": ["/custom/search"]},
            )

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
        # Map hit must reside under env["RECIPE_SEARCH_DIRS"] to be
        # trusted (security fix F-5). Use /search/dir1 as the parent.
        env = {"RECIPE_SEARCH_DIRS": ["/search/dir1", "/search/dir2"]}

        with (
            patch(
                "autopkg.extract_processor_name_with_recipe_identifier"
            ) as mock_extract,
            patch("autopkg.find_recipe_by_identifier_in_map") as mock_find_in_map,
            patch("autopkg.find_recipe_by_identifier_on_disk") as mock_find_on_disk,
            patch("autopkg._path_under_dirs", return_value=True),
            patch("os.path.dirname") as mock_dirname,
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
            # Map hit; the _path_under_dirs check is mocked to True so we
            # don't depend on the host OS's path separator for the scope
            # check.
            mock_find_in_map.return_value = "/shared/SharedRecipe.recipe"
            mock_exists.side_effect = lambda path: path == "/shared/CustomProcessor.py"
            mock_join.side_effect = lambda *args: "/".join(args)

            result = autopkg.find_processor_path(processor_name, recipe, env)

            self.assertEqual(result, "/shared/CustomProcessor.py")
            mock_find_in_map.assert_called_once_with("com.example.recipes.shared")
            mock_find_on_disk.assert_not_called()

    def test_find_processor_path_map_hit_outside_scope_is_rejected(self):
        """Security F-5: a map hit that points OUTSIDE the caller's
        declared RECIPE_SEARCH_DIRS must NOT be honoured. Otherwise a
        pre-existing map could leak processor-resolution to directories
        the caller explicitly excluded via --search-dir."""
        processor_name = "com.example.shared/Proc"
        recipe = {"RECIPE_PATH": "/sandboxed/x.recipe"}
        env = {"RECIPE_SEARCH_DIRS": ["/sandboxed"]}

        autopkglib._recipe_map_cwd_rebuild_attempted = True  # skip rebuild
        with (
            patch(
                "autopkg.extract_processor_name_with_recipe_identifier"
            ) as mock_extract,
            patch("autopkg.find_recipe_by_identifier_in_map") as mock_find_in_map,
            patch(
                "autopkg.find_recipe_by_identifier_on_disk",
                return_value=None,
            ) as mock_find_on_disk,
            patch("autopkglib.calculate_recipe_map"),
            patch("os.path.exists", return_value=False),
        ):
            mock_extract.return_value = ("Proc", "com.example.shared")
            # Map says the shared recipe is OUTSIDE /sandboxed.
            mock_find_in_map.return_value = "/outside/Leaky.recipe"

            result = autopkg.find_processor_path(processor_name, recipe, env)

            # Map hit was rejected; fallback was tried and returned None.
            self.assertIsNone(result)
            mock_find_on_disk.assert_called_once_with(
                "com.example.shared", ["/sandboxed"]
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

        # find_processor_path consults the map first then the on-disk
        # scanner. Stub both to "not found" so we exercise the
        # cwd-rebuild fallback path.
        autopkglib._recipe_map_cwd_rebuild_attempted = True  # skip rebuild
        with (
            patch("os.path.dirname") as mock_dirname,
            patch(
                "autopkg.extract_processor_name_with_recipe_identifier"
            ) as mock_extract,
            patch("autopkg.find_recipe_by_identifier_in_map", return_value=None),
            patch("autopkg.find_recipe_by_identifier_on_disk", return_value=None),
            patch("os.path.exists") as mock_exists,
            patch("os.path.join") as mock_join,
        ):
            mock_dirname.return_value = "/recipes"
            mock_extract.return_value = ("TestProcessor", "com.missing.recipe")
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
            patch("autopkg.find_recipe_by_identifier_in_map") as mock_find_in_map,
            patch("autopkg.find_recipe_by_identifier_on_disk"),
            patch("autopkg._path_under_dirs", return_value=True),
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
            mock_find_in_map.return_value = "/shared/SharedRecipe.recipe"
            mock_exists.side_effect = lambda path: path == "/shared/CustomProcessor.py"
            mock_join.side_effect = lambda *args: "/".join(args)

            result = autopkg.find_processor_path(processor_name, recipe, env)

            self.assertEqual(result, "/shared/CustomProcessor.py")

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


if __name__ == "__main__":
    unittest.main()
