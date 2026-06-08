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
import shutil
import sys
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

    def test_parse_path_for_dmg_detects_windows_separator(self):
        dmg_path = r"C:\path\to\test.dmg\TestApp.app"

        result = self.processor.parsePathForDMG(dmg_path)

        self.assertEqual(result, (r"C:\path\to\test.dmg", ".dmg\\", "TestApp.app"))

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

    @unittest.skipUnless(sys.platform == "darwin", "Requires macOS")
    def test_dmg_has_sla_wraps_launch_error(self):
        with patch("subprocess.Popen", side_effect=OSError(2, "missing")):
            with self.assertRaisesRegex(ProcessorError, "hdiutil execution failed"):
                self.processor.dmg_has_sla("/path/to/test.dmg")

    def test_unmount_if_mounted_skips_when_not_mounted(self):
        self.processor.unmount_if_mounted("/not/mounted.dmg")

    def test_unmount_if_mounted_calls_unmount_when_mounted(self):
        self.processor.mounts["/path/to/image.dmg"] = self.mount_point
        with patch.object(self.processor, "unmount") as mock_unmount:
            self.processor.unmount_if_mounted("/path/to/image.dmg")
        mock_unmount.assert_called_once_with("/path/to/image.dmg")

    def test_unmount_if_mounted_preserves_unmount_error(self):
        self.processor.mounts["/path/to/image.dmg"] = self.mount_point
        unmount_error = ProcessorError("detach failed")
        with patch.object(self.processor, "unmount", side_effect=unmount_error):
            with self.assertRaises(ProcessorError) as ctx:
                self.processor.unmount_if_mounted("/path/to/image.dmg")
        self.assertIs(ctx.exception, unmount_error)


if __name__ == "__main__":
    unittest.main()
