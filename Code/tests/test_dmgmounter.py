#!/usr/local/autopkg/python

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from autopkglib import ProcessorError
from autopkglib.DmgMounter import DmgMounter


class TestDmgMounterPathConfinement(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mount_point = os.path.join(self.tmpdir, "mount")
        self.outside_dir = os.path.join(self.tmpdir, "outside")
        os.makedirs(self.mount_point)
        os.makedirs(self.outside_dir)
        self.processor = DmgMounter()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _symlink_or_skip(self, target, link_name):
        try:
            os.symlink(target, link_name)
        except (AttributeError, NotImplementedError, OSError) as err:
            self.skipTest(f"symlink creation is unavailable: {err}")

    def test_path_in_mount_accepts_child_path(self):
        self.assertEqual(
            self.processor.path_in_mount(self.mount_point, "App/Test.app"),
            os.path.join(self.mount_point, "App", "Test.app"),
        )

    def test_path_in_mount_rejects_parent_reference(self):
        with self.assertRaises(ProcessorError):
            self.processor.path_in_mount(self.mount_point, "../outside.pkg")

    def test_path_in_mount_rejects_normalized_parent_reference(self):
        with self.assertRaises(ProcessorError):
            self.processor.path_in_mount(self.mount_point, "dir/../../outside.pkg")

    def test_path_in_mount_rejects_absolute_inner_path(self):
        with self.assertRaises(ProcessorError):
            self.processor.path_in_mount(self.mount_point, "/outside.pkg")

    def test_path_in_mount_rejects_symlink_escape(self):
        link_path = os.path.join(self.mount_point, "link")
        self._symlink_or_skip(self.outside_dir, link_path)

        with self.assertRaises(ProcessorError):
            self.processor.path_in_mount(self.mount_point, "link/outside.pkg")

    def test_glob_paths_in_mount_accepts_matches_inside_mount(self):
        pkg_path = os.path.join(self.mount_point, "Inside.pkg")
        with open(pkg_path, "w", encoding="utf-8"):
            pass

        pattern, matches = self.processor.glob_paths_in_mount(self.mount_point, "*.pkg")

        self.assertEqual(pattern, os.path.join(self.mount_point, "*.pkg"))
        self.assertEqual(matches, [pkg_path])

    def test_glob_paths_in_mount_rejects_symlink_match_escape(self):
        outside_pkg = os.path.join(self.outside_dir, "Outside.pkg")
        with open(outside_pkg, "w", encoding="utf-8"):
            pass
        link_path = os.path.join(self.mount_point, "Linked.pkg")
        self._symlink_or_skip(outside_pkg, link_path)

        with self.assertRaises(ProcessorError):
            self.processor.glob_paths_in_mount(self.mount_point, "*.pkg")

    def test_dmg_has_sla_wraps_launch_error(self):
        with patch("subprocess.Popen", side_effect=OSError(2, "missing")):
            with self.assertRaisesRegex(ProcessorError, "hdiutil execution failed"):
                self.processor.dmg_has_sla("/path/to/test.dmg")


if __name__ == "__main__":
    unittest.main()
