#!/usr/local/autopkg/python
"""
Integration tests for DMG mounting and plist reading functionality.

These tests verify the complete workflow of mounting DMGs, reading plists,
and unmounting, using real file operations where possible.
"""

import os
import plistlib
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

import autopkglib


class TestDMGPlistIntegration(unittest.TestCase):
    """Integration tests for DMG mounting and plist reading workflow."""

    def setUp(self):
        """Set up test fixtures."""
        self.tmp_dir = TemporaryDirectory()
        self.processor = autopkglib.PlistReader()

    def tearDown(self):
        """Clean up test fixtures."""
        self.tmp_dir.cleanup()

    def test_dmg_mount_read_unmount_workflow(self):
        """Integration test: Full DMG mounting, plist reading, and unmounting workflow.

        This test verifies the complete interaction between DMG mounting,
        file system operations, plist reading, and cleanup.
        """
        dmg_path = "/path/to/test.dmg"
        internal_path = "TestApp.app"
        mount_point = self.tmp_dir.name

        # Create a test plist file in the mount point
        bundle_dir = os.path.join(mount_point, "TestApp.app", "Contents")
        os.makedirs(bundle_dir, exist_ok=True)
        plist_path = os.path.join(bundle_dir, "Info.plist")

        test_plist_data = {"CFBundleShortVersionString": "4.0.0"}
        with open(plist_path, "wb") as f:
            plistlib.dump(test_plist_data, f)

        self.processor.env = {
            "info_path": f"{dmg_path}/{internal_path}",
            "plist_keys": {"CFBundleShortVersionString": "version"},
        }

        # Mock the DMG-specific operations but use real file operations
        with patch.object(self.processor, "parsePathForDMG") as mock_parse:
            with patch.object(self.processor, "mount") as mock_mount:
                with patch.object(self.processor, "unmount") as mock_unmount:
                    with patch.object(
                        self.processor, "get_bundle_info_path"
                    ) as mock_bundle:
                        with patch.object(self.processor, "output"):

                            # Setup mocks for DMG operations
                            mock_parse.return_value = (dmg_path, True, internal_path)
                            mock_mount.return_value = mount_point
                            mock_bundle.return_value = plist_path

                            # Execute the workflow
                            self.processor.main()

        # Verify the complete workflow was executed correctly
        mock_parse.assert_called_once()
        mock_mount.assert_called_once_with(dmg_path)
        mock_unmount.assert_called_once_with(dmg_path)

        # Verify the plist was actually read and processed
        self.assertEqual(self.processor.env["version"], "4.0.0")

    def test_dmg_mount_failure_cleanup(self):
        """Integration test: Verify cleanup occurs when DMG mounting fails."""
        dmg_path = "/path/to/nonexistent.dmg"

        self.processor.env = {
            "info_path": f"{dmg_path}/TestApp.app",
            "plist_keys": {"CFBundleShortVersionString": "version"},
        }

        mount_cleanup_called = False

        def mock_mount_side_effect(path):
            raise OSError("Failed to mount DMG")

        def mock_unmount_side_effect(path):
            nonlocal mount_cleanup_called
            mount_cleanup_called = True

        with patch.object(self.processor, "parsePathForDMG") as mock_parse:
            with patch.object(
                self.processor, "mount", side_effect=mock_mount_side_effect
            ):
                with patch.object(
                    self.processor, "unmount", side_effect=mock_unmount_side_effect
                ) as mock_unmount:
                    with patch.object(self.processor, "output"):

                        mock_parse.return_value = (dmg_path, True, "TestApp.app")

                        # This should raise an exception but still call unmount for cleanup
                        with self.assertRaises(OSError):
                            self.processor.main()

        # Verify cleanup was attempted even after failure
        mock_unmount.assert_called_once_with(dmg_path)


if __name__ == "__main__":
    unittest.main()
