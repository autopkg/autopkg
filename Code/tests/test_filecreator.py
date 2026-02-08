#!/usr/local/autopkg/python

import os
import plistlib
import tempfile
import unittest

from autopkglib import ProcessorError
from autopkglib.FileCreator import FileCreator


class TestFileCreator(unittest.TestCase):
    """Test class for FileCreator Processor."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_file_path = os.path.join(self.temp_dir, "testfile")
        self.good_env = {
            "file_content": "Hello world",
            "file_path": self.test_file_path,
        }
        self.input_plist = plistlib.dumps(self.good_env)
        self.processor = FileCreator(infile=self.input_plist)

    def tearDown(self):
        # Clean up temp files
        if os.path.exists(self.test_file_path):
            os.unlink(self.test_file_path)
        os.rmdir(self.temp_dir)

    def test_file_creation_and_content(self):
        """Test that FileCreator creates file with correct content."""
        self.processor.env = self.good_env
        self.processor.main()

        # Verify file was created
        self.assertTrue(os.path.exists(self.test_file_path))

        # Verify file content
        with open(self.test_file_path, "r") as f:
            content = f.read()
        self.assertEqual(content, "Hello world")

    def test_file_permissions(self):
        """Test that FileCreator sets file permissions correctly."""
        env_with_mode = self.good_env.copy()
        env_with_mode["file_mode"] = "0644"

        self.processor.env = env_with_mode
        self.processor.main()

        # Verify file permissions (0644 = 420 decimal)
        file_mode = os.stat(self.test_file_path).st_mode & 0o777
        self.assertEqual(file_mode, 0o644)

    def test_invalid_file_path_raises_error(self):
        """Test that invalid file path raises ProcessorError."""
        bad_env = {"file_content": "Hello", "file_path": "/nonexistent/path/file"}
        self.processor.env = bad_env

        with self.assertRaises(ProcessorError):
            self.processor.main()

    def test_invalid_file_mode_raises_error(self):
        """Test that invalid file mode raises ProcessorError."""
        env_with_bad_mode = self.good_env.copy()
        env_with_bad_mode["file_mode"] = "invalid"

        self.processor.env = env_with_bad_mode

        with self.assertRaises(ProcessorError):
            self.processor.main()


if __name__ == "__main__":
    unittest.main()
