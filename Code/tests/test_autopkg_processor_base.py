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
    def test_output_prints_message_when_verbose_sufficient(self):
        """Test that output prints message when verbosity is sufficient."""
        self.processor.env["verbose"] = 2

        with patch("builtins.print") as mock_print:
            self.processor.output("test message", verbose_level=2)

        mock_print.assert_called_once_with("TestProcessor: test message")

    def test_output_no_print_when_verbose_insufficient(self):
        """Test that output doesn't print when verbosity is insufficient."""
        self.processor.env["verbose"] = 1

        with patch("builtins.print") as mock_print:
            self.processor.output("test message", verbose_level=2)

        mock_print.assert_not_called()

    def test_output_default_verbose_level(self):
        """Test output with default verbose level."""
        self.processor.env["verbose"] = 1

        with patch("builtins.print") as mock_print:
            self.processor.output("test message")

        mock_print.assert_called_once_with("TestProcessor: test message")

    def test_output_no_verbose_env(self):
        """Test output when verbose is not set in env."""
        del self.processor.env["verbose"]

        with patch("builtins.print") as mock_print:
            self.processor.output("test message", verbose_level=1)

        mock_print.assert_not_called()

    def test_output_verbose_zero(self):
        """Test output when verbose is set to 0."""
        self.processor.env["verbose"] = 0

        with patch("builtins.print") as mock_print:
            self.processor.output("test message", verbose_level=1)

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

    @patch("sys.argv", ["processor", "key=value"])
    def test_execute_shell_parse_args(self):
        """Test execute_shell parses args when provided."""
        processor = TestProcessor()

        with patch.object(processor, "parse_arguments") as mock_parse:
            with patch.object(processor, "process") as mock_process:
                with patch.object(processor, "write_output_plist") as mock_write:
                    with patch("sys.exit") as mock_exit:
                        processor.execute_shell()

        mock_parse.assert_called_once()
        mock_process.assert_called_once()
        mock_write.assert_called_once()
        mock_exit.assert_called_once_with(0)

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


if __name__ == "__main__":
    unittest.main()
