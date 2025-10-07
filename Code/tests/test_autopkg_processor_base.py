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

import io
import os
import plistlib
import sys
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from autopkglib import Processor, ProcessorError


class TestProcessor(Processor):
    """Test processor that inherits from base Processor class."""

    description = "Test processor for testing base Processor functionality"
    input_variables = {
        "test_input": {
            "required": True,
            "description": "A required test input",
        },
        "optional_input": {
            "required": False,
            "description": "An optional test input",
            "default": "default_value",
        },
    }
    output_variables = {
        "test_output": {
            "description": "Test output variable",
        }
    }

    def main(self):
        """Test main method implementation."""
        self.env["test_output"] = f"processed_{self.env['test_input']}"


class ConcreteProcessor(Processor):
    """Another test processor for testing base functionality."""

    description = "Another test processor"
    input_variables = {}
    output_variables = {}

    def main(self):
        """Simple main implementation."""
        pass


class IncompleteProcessor(Processor):
    """Processor missing description for testing."""

    input_variables = {}
    output_variables = {}

    def main(self):
        """Simple main implementation."""
        pass


class TestProcessorBase(unittest.TestCase):
    """Test cases for the base Processor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.tmp_dir = TemporaryDirectory()
        self.processor = TestProcessor()
        self.processor.env = {
            "test_input": "test_value",
            "verbose": 1,
        }

    def tearDown(self):
        """Clean up after tests."""
        self.tmp_dir.cleanup()

    # Test __init__ method
    def test_init_default_values(self):
        """Test Processor initialization with default values."""
        processor = ConcreteProcessor()

        self.assertIsNone(processor.env)
        self.assertEqual(processor.infile, sys.stdin)
        self.assertEqual(processor.outfile, sys.stdout)

    def test_init_with_custom_values(self):
        """Test Processor initialization with custom values."""
        test_env = {"key": "value"}
        test_infile = io.StringIO("input")
        test_outfile = io.StringIO()

        processor = ConcreteProcessor(
            env=test_env, infile=test_infile, outfile=test_outfile
        )

        self.assertEqual(processor.env, test_env)
        self.assertEqual(processor.infile, test_infile)
        self.assertEqual(processor.outfile, test_outfile)

    # Test output method
    def test_output_verbose_behavior(self):
        """Test output method behavior under different verbosity conditions."""
        test_cases = [
            # (env_verbose, message_verbose_level, should_print, description)
            (2, 2, True, "sufficient verbosity"),
            (1, 2, False, "insufficient verbosity"),
            (1, 1, True, "default verbose level"),
            (0, 1, False, "verbose set to zero"),
            (None, 1, False, "no verbose in env"),
        ]

        for env_verbose, msg_verbose, should_print, description in test_cases:
            with self.subTest(description=description):
                # Set up environment
                if env_verbose is None:
                    if "verbose" in self.processor.env:
                        del self.processor.env["verbose"]
                else:
                    self.processor.env["verbose"] = env_verbose

                with patch("builtins.print") as mock_print:
                    if msg_verbose == 1:  # Test default verbose level
                        self.processor.output("test message")
                    else:
                        self.processor.output("test message", verbose_level=msg_verbose)

                if should_print:
                    mock_print.assert_called_once_with("TestProcessor: test message")
                else:
                    mock_print.assert_not_called()

    # Test main method
    def test_main_raises_not_implemented(self):
        """Test that base Processor main method raises NotImplementedError."""
        base_processor = Processor()

        with self.assertRaises(ProcessorError) as context:
            base_processor.main()

        self.assertIn("Abstract method main() not implemented", str(context.exception))

    # Test get_manifest method
    def test_get_manifest_returns_correct_tuple(self):
        """Test that get_manifest returns the correct tuple."""
        description, input_vars, output_vars = self.processor.get_manifest()

        self.assertEqual(
            description, "Test processor for testing base Processor functionality"
        )
        self.assertEqual(input_vars, self.processor.input_variables)
        self.assertEqual(output_vars, self.processor.output_variables)

    def test_get_manifest_missing_description(self):
        """Test get_manifest when description is missing."""
        processor = IncompleteProcessor()

        with self.assertRaises(ProcessorError) as context:
            processor.get_manifest()

        self.assertIn("Missing manifest", str(context.exception))

    def test_get_manifest_missing_input_variables(self):
        """Test get_manifest when input_variables is missing."""
        processor = ConcreteProcessor()
        # Remove input_variables from the class (simulate missing attribute)
        original_input_vars = processor.input_variables
        del processor.__class__.input_variables

        try:
            with self.assertRaises(ProcessorError) as context:
                processor.get_manifest()

            self.assertIn("Missing manifest", str(context.exception))
        finally:
            # Restore the attribute
            processor.__class__.input_variables = original_input_vars

    # Test read_input_plist method
    def test_read_input_plist_with_data(self):
        """Test reading input plist with data."""
        test_data = {"key": "value", "number": 42}
        plist_data = plistlib.dumps(test_data)

        processor = ConcreteProcessor()
        processor.infile = MagicMock()
        processor.infile.buffer.read.return_value = plist_data

        processor.read_input_plist()

        self.assertEqual(processor.env, test_data)

    def test_read_input_plist_empty_data(self):
        """Test reading input plist with empty data."""
        processor = ConcreteProcessor()
        processor.infile = MagicMock()
        processor.infile.buffer.read.return_value = b""

        processor.read_input_plist()

        self.assertEqual(processor.env, {})

    def test_read_input_plist_error(self):
        """Test read_input_plist handles errors."""
        processor = ConcreteProcessor()
        processor.infile = MagicMock()
        processor.infile.buffer.read.side_effect = Exception("Read error")

        with self.assertRaises(ProcessorError):
            processor.read_input_plist()

    # Test write_output_plist method
    def test_write_output_plist_with_file_path(self):
        """Test writing output plist to file path."""
        test_file = os.path.join(self.tmp_dir.name, "output.plist")
        test_env = {"key": "value", "number": 42}

        processor = ConcreteProcessor()
        processor.env = test_env
        processor.outfile = test_file

        processor.write_output_plist()

        # Verify file was written correctly
        with open(test_file, "rb") as f:
            result = plistlib.load(f)
        self.assertEqual(result, test_env)

    def test_write_output_plist_with_buffer(self):
        """Test writing output plist to buffer."""
        test_env = {"key": "value", "number": 42}

        processor = ConcreteProcessor()
        processor.env = test_env
        mock_outfile = MagicMock()
        mock_buffer = io.BytesIO()
        mock_outfile.buffer = mock_buffer
        processor.outfile = mock_outfile

        # Mock the first plistlib.dump call to raise TypeError
        with patch("plistlib.dump") as mock_dump:
            mock_dump.side_effect = [TypeError("Mock TypeError"), None]
            processor.write_output_plist()

        # Should call plistlib.dump twice - once normally, once with buffer
        self.assertEqual(mock_dump.call_count, 2)

    def test_write_output_plist_none_env(self):
        """Test write_output_plist when env is None."""
        processor = ConcreteProcessor()
        processor.env = None

        # Should return early without error
        processor.write_output_plist()

    def test_write_output_plist_filters_none_values(self):
        """Test that write_output_plist filters out None values."""
        test_file = os.path.join(self.tmp_dir.name, "output.plist")
        test_env = {"key": "value", "none_key": None, "number": 42}
        expected_result = {"key": "value", "number": 42}

        processor = ConcreteProcessor()
        processor.env = test_env
        processor.outfile = test_file

        processor.write_output_plist()

        # Verify None values were filtered out
        with open(test_file, "rb") as f:
            result = plistlib.load(f)
        self.assertEqual(result, expected_result)

    def test_write_output_plist_error(self):
        """Test write_output_plist handles errors."""
        processor = ConcreteProcessor()
        processor.env = {"key": "value"}
        processor.outfile = "/invalid/path/output.plist"

        with self.assertRaises(ProcessorError):
            processor.write_output_plist()

    # Test parse_arguments method
    @patch("sys.argv", ["processor", "key1=value1", "key2=value2"])
    def test_parse_arguments(self):
        """Test parsing command line arguments."""
        processor = ConcreteProcessor()
        processor.parse_arguments()

        expected_env = {"key1": "value1", "key2": "value2"}
        self.assertEqual(processor.env, expected_env)

    @patch("sys.argv", ["processor", "invalid_arg"])
    def test_parse_arguments_invalid_format(self):
        """Test parse_arguments with invalid argument format."""
        processor = ConcreteProcessor()

        with self.assertRaises(ProcessorError) as context:
            processor.parse_arguments()

        self.assertIn("Illegal argument", str(context.exception))

    @patch("sys.argv", ["processor"])
    def test_parse_arguments_no_args(self):
        """Test parse_arguments with no arguments."""
        processor = ConcreteProcessor()
        processor.parse_arguments()

        self.assertEqual(processor.env, {})

    # Test inject method
    def test_inject_updates_env(self):
        """Test that inject updates environment with arguments."""
        processor = ConcreteProcessor()
        processor.env = {"existing": "value"}

        arguments = {"new_key": "new_value", "another_key": "another_value"}
        processor.inject(arguments)

        expected_env = {
            "existing": "value",
            "new_key": "new_value",
            "another_key": "another_value",
        }
        self.assertEqual(processor.env, expected_env)

    def test_inject_with_variable_substitution(self):
        """Test inject with variable substitution."""
        processor = ConcreteProcessor()
        processor.env = {"base_path": "/tmp"}

        arguments = {"full_path": "%base_path%/file.txt"}
        processor.inject(arguments)

        self.assertEqual(processor.env["full_path"], "/tmp/file.txt")

    # Test process method
    def test_process_applies_defaults(self):
        """Test that process applies default values."""
        processor = TestProcessor()
        processor.env = {"test_input": "test_value"}

        result_env = processor.process()

        self.assertEqual(result_env["optional_input"], "default_value")

    def test_process_required_missing(self):
        """Test process raises error when required input is missing."""
        processor = TestProcessor()
        processor.env = {}  # Missing required test_input

        with self.assertRaises(ProcessorError) as context:
            processor.process()

        self.assertIn("TestProcessor requires test_input", str(context.exception))

    def test_process_calls_main(self):
        """Test that process calls main method."""
        processor = TestProcessor()
        processor.env = {"test_input": "test_value"}

        result_env = processor.process()

        # Verify main was called (check output variable was set)
        self.assertEqual(result_env["test_output"], "processed_test_value")

    def test_process_returns_env(self):
        """Test that process returns the environment."""
        processor = TestProcessor()
        processor.env = {"test_input": "test_value"}

        result_env = processor.process()

        self.assertIs(result_env, processor.env)

    def test_process_prints_default_message(self):
        """Test that process prints default value message."""
        processor = TestProcessor()
        processor.env = {"test_input": "test_value", "verbose": 2}

        with patch.object(processor, "output") as mock_output:
            processor.process()

        mock_output.assert_called_with(
            "No value supplied for optional_input, setting default value of: default_value",
            verbose_level=2,
        )

    # Test cmdexec method
    def test_cmdexec_success(self):
        """Test successful command execution."""
        processor = ConcreteProcessor()

        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = (b"output", b"")
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc

            result = processor.cmdexec(["echo", "test"], "test command")

        self.assertEqual(result, b"output")

    def test_cmdexec_command_not_found(self):
        """Test cmdexec when command is not found."""
        processor = ConcreteProcessor()

        with patch("subprocess.Popen") as mock_popen:
            mock_popen.side_effect = OSError(2, "No such file")

            with self.assertRaises(ProcessorError) as context:
                processor.cmdexec(["nonexistent"], "test command")

        self.assertIn("execution failed with error code 2", str(context.exception))

    def test_cmdexec_command_failure(self):
        """Test cmdexec when command returns non-zero exit code."""
        processor = ConcreteProcessor()

        with patch("subprocess.Popen") as mock_popen:
            mock_proc = MagicMock()
            mock_proc.communicate.return_value = (b"", b"error message")
            mock_proc.returncode = 1
            mock_popen.return_value = mock_proc

            with self.assertRaises(ProcessorError) as context:
                processor.cmdexec(["false"], "test command")

        self.assertIn("test command failed", str(context.exception))

    # Test execute_shell method
    @patch("sys.argv", ["processor"])
    def test_execute_shell_read_input(self):
        """Test execute_shell reads input when no args."""
        processor = TestProcessor()

        with patch.object(processor, "read_input_plist") as mock_read:
            with patch.object(processor, "process") as mock_process:
                with patch.object(processor, "write_output_plist") as mock_write:
                    with patch("sys.exit") as mock_exit:
                        processor.execute_shell()

        mock_read.assert_called_once()
        mock_process.assert_called_once()
        mock_write.assert_called_once()
        mock_exit.assert_called_once_with(0)

    def test_parse_arguments_key_value(self):
        """Test parse_arguments correctly parses key=value pairs."""
        processor = TestProcessor()

        with patch("sys.argv", ["processor", "test_key=test_value", "number=42"]):
            processor.parse_arguments()

        self.assertEqual(processor.env["test_key"], "test_value")
        self.assertEqual(processor.env["number"], "42")

    def test_execute_shell_handles_processor_error(self):
        """Test execute_shell handles ProcessorError."""
        processor = TestProcessor()
        processor.env = {"test_input": "test_value"}  # Provide required input

        with patch.object(processor, "read_input_plist"):
            with patch.object(processor, "process") as mock_process:
                mock_process.side_effect = ProcessorError("Test error")
                with patch("autopkglib.log_err") as mock_log_err:
                    with patch("sys.exit") as mock_exit:
                        with patch("sys.argv", ["processor"]):  # Mock sys.argv
                            processor.execute_shell()

        # Check that log_err was called with the ProcessorError message
        mock_log_err.assert_called_once()
        args, _ = mock_log_err.call_args
        self.assertIn("ProcessorError: Test error", args[0])
        mock_exit.assert_called_once_with(10)

    # Test load_plist_from_file method
    def test_load_plist_from_file_with_path(self):
        """Test loading plist from file path."""
        test_data = {"key": "value", "number": 42}
        test_file = os.path.join(self.tmp_dir.name, "test.plist")

        with open(test_file, "wb") as f:
            plistlib.dump(test_data, f)

        processor = ConcreteProcessor()
        result = processor.load_plist_from_file(test_file)

        self.assertEqual(result, test_data)

    def test_load_plist_from_file_with_file_object(self):
        """Test loading plist from file object."""
        test_data = {"key": "value", "number": 42}
        plist_data = plistlib.dumps(test_data)
        file_obj = io.BytesIO(plist_data)

        processor = ConcreteProcessor()
        result = processor.load_plist_from_file(file_obj)

        self.assertEqual(result, test_data)

    def test_load_plist_from_file_error(self):
        """Test load_plist_from_file handles errors."""
        processor = ConcreteProcessor()

        with self.assertRaises(ProcessorError) as context:
            processor.load_plist_from_file("/nonexistent/file.plist")

        self.assertIn("Unable to load plist", str(context.exception))

    def test_load_plist_from_file_custom_exception_text(self):
        """Test load_plist_from_file with custom exception text."""
        processor = ConcreteProcessor()

        with self.assertRaises(ProcessorError) as context:
            processor.load_plist_from_file(
                "/nonexistent/file.plist", exception_text="Custom error message"
            )

        self.assertIn("Custom error message", str(context.exception))

    # Test show_deprecation method
    def test_show_deprecation(self):
        """Test show_deprecation method."""
        processor = TestProcessor()
        processor.env = {"RECIPE_PATH": "/path/to/test.recipe", "verbose": 1}
        processor.output_variables = {}

        with patch.object(processor, "output") as mock_output:
            processor.show_deprecation("Test deprecation message")

        # Check output was called
        mock_output.assert_called_once_with("WARNING: Test deprecation message")

        # Check deprecation summary was set
        self.assertIn("deprecation_summary_result", processor.env)
        self.assertIn("deprecation_summary_result", processor.output_variables)

        summary = processor.env["deprecation_summary_result"]
        self.assertEqual(summary["data"]["name"], "test")
        self.assertEqual(summary["data"]["warning"], "Test deprecation message")

    def test_show_deprecation_no_output_variables(self):
        """Test show_deprecation when output_variables is None."""
        processor = TestProcessor()
        processor.env = {"RECIPE_PATH": "/path/to/test.recipe.plist", "verbose": 1}
        processor.output_variables = None

        with patch.object(processor, "output"):
            processor.show_deprecation("Test deprecation message")

        # Should create output_variables dict
        self.assertIsInstance(processor.output_variables, dict)
        self.assertIn("deprecation_summary_result", processor.output_variables)

    # Test lifecycle attribute
    def test_lifecycle_default_empty_dict(self):
        """Test that lifecycle attribute defaults to empty dict."""
        processor = Processor()
        self.assertEqual(processor.lifecycle, {})
        self.assertIsInstance(processor.lifecycle, dict)

    # Test lifecycle with deprecated version
    def test_processor_with_deprecated_lifecycle(self):
        """Test processor with deprecated lifecycle metadata."""

        class DeprecatedProcessor(Processor):
            """Test processor with deprecated lifecycle."""

            description = "A deprecated processor"
            input_variables = {}
            output_variables = {}
            lifecycle = {"deprecated": "1.0.0", "introduced": "0.5.0"}

            def main(self):
                pass

        processor = DeprecatedProcessor(env={"verbose": 1})
        self.assertEqual(processor.lifecycle.get("deprecated"), "1.0.0")
        self.assertEqual(processor.lifecycle.get("introduced"), "0.5.0")

    def test_processor_without_deprecated_lifecycle(self):
        """Test processor without deprecated lifecycle metadata."""

        class ActiveProcessor(Processor):
            """Test processor without deprecation."""

            description = "An active processor"
            input_variables = {}
            output_variables = {}
            lifecycle = {"introduced": "2.0.0"}

            def main(self):
                pass

        processor = ActiveProcessor(env={"verbose": 1})
        self.assertIsNone(processor.lifecycle.get("deprecated"))
        self.assertEqual(processor.lifecycle.get("introduced"), "2.0.0")

    # Test get_deprecation_warning method
    def test_get_deprecation_warning(self):
        """Test get_deprecation_warning returns correct message."""

        class TestProcessorForWarning(Processor):
            """Test processor for deprecation warning."""

            description = "Test processor"
            input_variables = {}
            output_variables = {}

            def main(self):
                pass

        processor = TestProcessorForWarning()
        message = processor.get_deprecation_warning("1.5.0")

        expected = (
            "TestProcessorForWarning was deprecated in AutoPkg version 1.5.0 "
            "and may be removed in a future release."
        )
        self.assertEqual(message, expected)

    # Test process method with deprecated processor
    def test_process_shows_deprecation_warning_when_deprecated(self):
        """Test that process() shows deprecation warning for deprecated processor."""

        class DeprecatedProcessor(Processor):
            """Test deprecated processor."""

            description = "A deprecated processor"
            input_variables = {}
            output_variables = {}
            lifecycle = {"deprecated": "1.2.0"}

            def main(self):
                pass

        processor = DeprecatedProcessor(
            env={"verbose": 1, "RECIPE_PATH": "/test.recipe"}
        )

        with patch.object(processor, "show_deprecation") as mock_show:
            with patch.object(
                processor, "get_deprecation_warning", return_value="Test warning"
            ) as mock_get_warning:
                processor.process()

            mock_get_warning.assert_called_once_with("1.2.0")
            mock_show.assert_called_once_with("Test warning")

    def test_process_no_deprecation_warning_when_not_deprecated(self):
        """Test that process() does not show deprecation warning for active processor."""

        class ActiveProcessor(Processor):
            """Test active processor."""

            description = "An active processor"
            input_variables = {}
            output_variables = {}
            lifecycle = {"introduced": "2.0.0"}

            def main(self):
                pass

        processor = ActiveProcessor(env={"verbose": 1})

        with patch.object(processor, "show_deprecation") as mock_show:
            processor.process()

        mock_show.assert_not_called()

    def test_process_no_deprecation_warning_when_lifecycle_empty(self):
        """Test that process() does not show deprecation warning when lifecycle is empty."""

        class BasicProcessor(Processor):
            """Test basic processor."""

            description = "A basic processor"
            input_variables = {}
            output_variables = {}

            def main(self):
                pass

        processor = BasicProcessor(env={"verbose": 1})

        with patch.object(processor, "show_deprecation") as mock_show:
            processor.process()

        mock_show.assert_not_called()

    def test_show_deprecation_with_different_recipe_names(self):
        """Test show_deprecation with various recipe file extensions."""

        test_cases = [
            ("/path/to/MyRecipe.recipe", "MyRecipe"),
            ("/path/to/MyRecipe.recipe.plist", "MyRecipe"),
            ("/path/to/MyRecipe.recipe.yaml", "MyRecipe"),
            ("/path/to/SomeApp.download.recipe", "SomeApp.download"),
        ]

        for recipe_path, expected_name in test_cases:
            with self.subTest(recipe_path=recipe_path):
                processor = TestProcessor(env={"RECIPE_PATH": recipe_path})
                processor.output_variables = {}

                with patch.object(processor, "output"):
                    processor.show_deprecation("Warning")

                summary = processor.env["deprecation_summary_result"]
                self.assertEqual(summary["data"]["name"], expected_name)

    # Test lifecycle metadata structure
    def test_lifecycle_metadata_can_have_multiple_fields(self):
        """Test that lifecycle can contain multiple metadata fields."""

        class ExtendedLifecycleProcessor(Processor):
            """Processor with extended lifecycle metadata."""

            description = "Processor with extended lifecycle"
            input_variables = {}
            output_variables = {}
            lifecycle = {
                "introduced": "1.0.0",
                "deprecated": "2.0.0",
                "removed": "3.0.0",
                "notes": "Use NewProcessor instead",
            }

            def main(self):
                pass

        processor = ExtendedLifecycleProcessor(env={"verbose": 1})
        self.assertEqual(processor.lifecycle.get("introduced"), "1.0.0")
        self.assertEqual(processor.lifecycle.get("deprecated"), "2.0.0")
        self.assertEqual(processor.lifecycle.get("removed"), "3.0.0")
        self.assertEqual(processor.lifecycle.get("notes"), "Use NewProcessor instead")

    def test_process_calls_main_even_with_deprecation(self):
        """Test that process() still calls main() even for deprecated processors."""

        class DeprecatedProcessor(Processor):
            """Deprecated processor."""

            description = "Deprecated processor"
            input_variables = {}
            output_variables = {"test_output": {"description": "Test"}}
            lifecycle = {"deprecated": "1.0.0"}

            def main(self):
                self.env["test_output"] = "success"

        processor = DeprecatedProcessor(
            env={"verbose": 1, "RECIPE_PATH": "/test.recipe"}
        )

        with patch.object(processor, "show_deprecation"):
            env = processor.process()

        # Verify main() was still called
        self.assertEqual(env["test_output"], "success")

    def test_process_deprecation_check_before_main(self):
        """Test that deprecation check happens before main() is called."""

        class OrderTestProcessor(Processor):
            """Processor to test order of operations."""

            description = "Order test processor"
            input_variables = {}
            output_variables = {}
            lifecycle = {"deprecated": "1.0.0"}
            call_order = []

            def main(self):
                self.__class__.call_order.append("main")

        processor = OrderTestProcessor(
            env={"verbose": 1, "RECIPE_PATH": "/test.recipe"}
        )

        def mock_show_deprecation(_msg):
            OrderTestProcessor.call_order.append("deprecation")

        with patch.object(
            processor, "show_deprecation", side_effect=mock_show_deprecation
        ):
            processor.process()

        # Verify deprecation check came before main
        self.assertEqual(processor.call_order[0], "deprecation")
        self.assertEqual(processor.call_order[1], "main")
        OrderTestProcessor.call_order.clear()

    # Test edge cases
    def test_lifecycle_with_none_value(self):
        """Test lifecycle with None as deprecated value."""

        class TestProcessorNone(Processor):
            """Test processor."""

            description = "Test processor"
            input_variables = {}
            output_variables = {}
            lifecycle = {"deprecated": None, "introduced": "1.0.0"}

            def main(self):
                pass

        processor = TestProcessorNone(env={"verbose": 1})

        with patch.object(processor, "show_deprecation") as mock_show:
            processor.process()

        # Should not show deprecation for None value
        mock_show.assert_not_called()

    def test_lifecycle_with_empty_string(self):
        """Test lifecycle with empty string as deprecated value."""

        class TestProcessorEmpty(Processor):
            """Test processor."""

            description = "Test processor"
            input_variables = {}
            output_variables = {}
            lifecycle = {"deprecated": "", "introduced": "1.0.0"}

            def main(self):
                pass

        processor = TestProcessorEmpty(env={"verbose": 1})

        with patch.object(processor, "show_deprecation") as mock_show:
            processor.process()

        # Should not show deprecation for empty string
        mock_show.assert_not_called()

    def test_lifecycle_with_false_value(self):
        """Test lifecycle with False as deprecated value."""

        class TestProcessorFalse(Processor):
            """Test processor."""

            description = "Test processor"
            input_variables = {}
            output_variables = {}
            lifecycle = {"deprecated": False, "introduced": "1.0.0"}

            def main(self):
                pass

        processor = TestProcessorFalse(env={"verbose": 1})

        with patch.object(processor, "show_deprecation") as mock_show:
            processor.process()

        # Should not show deprecation for False value
        mock_show.assert_not_called()

    # Integration tests
    def test_real_world_deprecated_processor_workflow(self):
        """Test complete workflow of a deprecated processor."""

        class BrewCaskInfoProvider(Processor):
            """Simulated deprecated processor."""

            description = "Simulated BrewCaskInfoProvider"
            input_variables = {
                "cask_name": {
                    "required": True,
                    "description": "Cask name",
                }
            }
            output_variables = {
                "version": {
                    "description": "Version",
                }
            }
            lifecycle = {"deprecated": "0.6.0", "introduced": "0.2.5"}

            def main(self):
                self.env["version"] = "1.0.0"

        env = {
            "verbose": 1,
            "RECIPE_PATH": "/recipes/test.recipe",
            "cask_name": "firefox",
        }
        processor = BrewCaskInfoProvider(env=env)

        with patch.object(processor, "output") as mock_output:
            result_env = processor.process()

        # Verify deprecation warning was shown
        mock_output.assert_called()
        warning_call = [
            call for call in mock_output.call_args_list if "WARNING" in str(call)
        ]
        self.assertTrue(len(warning_call) > 0)

        # Verify processor still worked
        self.assertEqual(result_env["version"], "1.0.0")

        # Verify deprecation summary was set
        self.assertIn("deprecation_summary_result", result_env)

    def test_non_deprecated_processor_workflow(self):
        """Test complete workflow of a non-deprecated processor."""

        class CURLDownloader(Processor):
            """Simulated active processor."""

            description = "Simulated CURLDownloader"
            input_variables = {
                "url": {
                    "required": True,
                    "description": "URL to download",
                }
            }
            output_variables = {
                "pathname": {
                    "description": "Downloaded file path",
                }
            }
            lifecycle = {"introduced": "0.5.1"}

            def main(self):
                self.env["pathname"] = "/tmp/file.dmg"

        env = {
            "verbose": 1,
            "RECIPE_PATH": "/recipes/test.recipe",
            "url": "https://example.com/file.dmg",
        }
        processor = CURLDownloader(env=env)

        with patch.object(processor, "output") as mock_output:
            result_env = processor.process()

        # Verify no deprecation warning was shown
        warning_calls = [
            call for call in mock_output.call_args_list if "WARNING" in str(call)
        ]
        self.assertEqual(len(warning_calls), 0)

        # Verify processor worked
        self.assertEqual(result_env["pathname"], "/tmp/file.dmg")

        # Verify no deprecation summary
        self.assertNotIn("deprecation_summary_result", result_env)

    def test_no_input_variable_defaults_contain_percent_variables(self):
        """
        Test that no processor has default values containing %variable% patterns.

        This catches the bug fixed in ca4a27a where default values like
        "%pathname%/*.app" or "%RECIPE_CACHE_DIR%/%app_name%-%version%.pkg"
        were used. These defaults don't go through variable substitution,
        so they remain as literal strings instead of being replaced with
        actual values.

        The correct pattern is to leave defaults implicit and handle them
        programmatically in the processor's main() method.
        """
        import glob
        import importlib.util
        import inspect
        import os
        import re

        # Pattern to match %variable_name%
        percent_var_pattern = re.compile(r"%[^%]+%")

        # Get all processor files
        autopkglib_dir = os.path.join(os.path.dirname(__file__), "..", "autopkglib")
        processor_files = glob.glob(os.path.join(autopkglib_dir, "*.py"))

        violations = []

        for processor_file in processor_files:
            # Skip __init__ and other utility files
            if os.path.basename(processor_file).startswith("__"):
                continue

            try:
                # Load the module
                module_name = os.path.splitext(os.path.basename(processor_file))[0]
                spec = importlib.util.spec_from_file_location(
                    module_name, processor_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Find all classes in the module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # Check if it has input_variables (likely a Processor)
                    if hasattr(obj, "input_variables") and isinstance(
                        obj.input_variables, dict
                    ):
                        # Check each input variable for defaults with %...%
                        for var_name, var_config in obj.input_variables.items():
                            if isinstance(var_config, dict) and "default" in var_config:
                                default_value = var_config["default"]
                                # Only check string defaults
                                if isinstance(default_value, str):
                                    if percent_var_pattern.search(default_value):
                                        violations.append(
                                            {
                                                "processor": name,
                                                "variable": var_name,
                                                "default": default_value,
                                                "file": os.path.basename(
                                                    processor_file
                                                ),
                                            }
                                        )
            except Exception:
                # Skip files that can't be imported (dependencies, etc.)
                continue

        # Assert no violations found
        if violations:
            error_msg = (
                "Found processor input variables with defaults containing %variable% patterns.\n"
                "These defaults won't have variables substituted and will remain as literal strings.\n"
                "Instead, leave defaults implicit and handle them programmatically in main().\n\n"
                "Violations:\n"
            )
            for v in violations:
                error_msg += f"  {v['file']}: {v['processor']}.{v['variable']} = \"{v['default']}\"\n"
            self.fail(error_msg)


if __name__ == "__main__":
    unittest.main()
