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

import importlib.util
import os
import sys
import types
import unittest
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

try:
    import xattr  # noqa: F401
except ImportError:
    xattr_module = types.ModuleType("xattr")

    class FakeXattr:
        def __init__(self, path):
            self.path = path

        def list(self):
            return []

        def remove(self, name):
            pass

    xattr_module.xattr = FakeXattr
    sys.modules["xattr"] = xattr_module

AUTOPKGSERVER_DIR = Path(__file__).parent.parent / "autopkgserver"


def load_worker_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Only load the worker modules on Darwin: itemcopier imports the POSIX-only
# grp and pwd, so importing it on Windows fails at test discovery time. Every
# test class below is skipped off Darwin anyway.
if sys.platform == "darwin":
    import grp

    common = load_worker_module("_common", AUTOPKGSERVER_DIR / "_common.py")
    installer = load_worker_module(
        "autopkgserver_installer_worker", AUTOPKGSERVER_DIR / "installer.py"
    )
    itemcopier = load_worker_module(
        "autopkgserver_itemcopier_worker", AUTOPKGSERVER_DIR / "itemcopier.py"
    )
else:
    # Dummy objects for non-Darwin platforms, referenced only inside skipped tests.
    common = grp = installer = itemcopier = None


@unittest.skipUnless(sys.platform == "darwin", "autopkgserver is macOS-only")
class TestCommonPathContainment(unittest.TestCase):
    """Tests for the workers' shared pre-resolved path helper."""

    def test_accepts_root_and_child(self):
        self.assertTrue(common.is_path_under("/cache", "/cache"))
        self.assertTrue(common.is_path_under("/cache/recipe/file", "/cache"))

    def test_rejects_sibling_prefix_and_mixed_roots(self):
        self.assertFalse(common.is_path_under("/cache-evil/file", "/cache"))
        self.assertFalse(common.is_path_under("relative/file", "/cache"))


@unittest.skipUnless(sys.platform == "darwin", "autopkgserver is macOS-only")
class TestInstallerValidation(unittest.TestCase):
    """Test class for Installer request validation."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.recipe_cache = os.path.join(self.tmp_dir.name, "cache", "com.test.pkg")
        os.makedirs(self.recipe_cache)
        self.private_tmp = os.path.join(self.tmp_dir.name, "private_tmp")
        os.makedirs(self.private_tmp)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _installer(self, package_path, recipe_cache_dir=None):
        request = {
            "package": package_path,
            "recipe_cache_dir": recipe_cache_dir or self.recipe_cache,
        }
        return installer.Installer(MagicMock(), MagicMock(), request)

    def test_accepts_package_in_recipe_cache(self):
        """Should accept a package under the effective recipe cache."""
        package_path = os.path.join(self.recipe_cache, "Test.pkg")
        Path(package_path).touch()

        worker = self._installer(package_path)
        worker.verify_request()

        self.assertEqual(worker.package_path, os.path.realpath(package_path))

    def test_accepts_package_in_private_tmp(self):
        """Should accept a package under the private temporary mount root."""
        mountpoint = os.path.join(self.private_tmp, "mount")
        os.makedirs(mountpoint)
        package_path = os.path.join(mountpoint, "Test.pkg")
        Path(package_path).touch()

        with (
            patch.object(installer, "PRIVATE_TMP", self.private_tmp),
            patch.object(
                installer.os.path,
                "ismount",
                side_effect=lambda path: (
                    os.path.realpath(path) == os.path.realpath(mountpoint)
                ),
            ),
        ):
            worker = self._installer(package_path)
            worker.verify_request()

        self.assertEqual(worker.package_path, os.path.realpath(package_path))

    def test_rejects_package_in_loose_private_tmp_path(self):
        """Should reject private temporary paths that are not in a mount."""
        package_path = os.path.join(self.private_tmp, "Test.pkg")
        Path(package_path).touch()

        with (
            patch.object(installer, "PRIVATE_TMP", self.private_tmp),
            patch.object(installer.os.path, "ismount", return_value=False),
        ):
            worker = self._installer(package_path)
            with self.assertRaises(installer.InstallerError):
                worker.verify_request()

    def test_rejects_package_outside_allowed_roots(self):
        """Should reject a package outside the request user's allowed roots."""
        package_path = os.path.join(self.tmp_dir.name, "elsewhere", "Test.pkg")
        os.makedirs(os.path.dirname(package_path))
        Path(package_path).touch()

        with (patch.object(installer, "PRIVATE_TMP", self.private_tmp),):
            worker = self._installer(package_path)
            with self.assertRaises(installer.InstallerError):
                worker.verify_request()

    def test_rejects_package_symlink_escape_from_cache(self):
        """Should reject cache packages that resolve outside the cache."""
        package_path = os.path.join(self.tmp_dir.name, "elsewhere", "Test.pkg")
        os.makedirs(os.path.dirname(package_path))
        Path(package_path).touch()
        symlink_path = os.path.join(self.recipe_cache, "Linked.pkg")
        os.symlink(package_path, symlink_path)

        worker = self._installer(symlink_path)
        with self.assertRaises(installer.InstallerError):
            worker.verify_request()

    def test_rejects_missing_recipe_cache_dir(self):
        """Should require the effective recipe cache directory."""
        package_path = os.path.join(self.recipe_cache, "Test.pkg")
        Path(package_path).touch()
        request = {"package": package_path}
        worker = installer.Installer(MagicMock(), MagicMock(), request)

        with self.assertRaises(installer.InstallerError):
            worker.verify_request()

    def test_do_install_does_not_wrap_keyboard_interrupt(self):
        """Should let process termination exceptions propagate."""
        package_path = os.path.join(self.recipe_cache, "Test.pkg")
        worker = self._installer(package_path)
        worker.package_path = package_path

        with (
            patch.object(installer.subprocess, "Popen", side_effect=KeyboardInterrupt),
            self.assertRaises(KeyboardInterrupt),
        ):
            worker.do_install()

    def test_do_install_preserves_installer_errors(self):
        """Should not wrap errors that already use the worker's error type."""
        package_path = os.path.join(self.recipe_cache, "Test.pkg")
        worker = self._installer(package_path)
        worker.package_path = package_path
        expected = installer.InstallerError("installer failed")

        with (
            patch.object(installer.subprocess, "Popen", side_effect=expected),
            self.assertRaises(installer.InstallerError) as raised,
        ):
            worker.do_install()

        self.assertIs(raised.exception, expected)

    def test_install_preserves_installer_errors(self):
        """Should not wrap validation errors in another InstallerError."""
        package_path = os.path.join(self.recipe_cache, "Test.pkg")
        worker = self._installer(package_path)
        expected = installer.InstallerError("invalid request")

        with (
            patch.object(worker, "verify_request", side_effect=expected),
            self.assertRaises(installer.InstallerError) as raised,
        ):
            worker.install()

        self.assertIs(raised.exception, expected)

    def test_install_chains_unexpected_errors(self):
        """Should retain the cause when adapting an unexpected exception."""
        package_path = os.path.join(self.recipe_cache, "Test.pkg")
        worker = self._installer(package_path)
        expected = RuntimeError("unexpected failure")

        with (
            patch.object(worker, "verify_request", side_effect=expected),
            self.assertRaises(installer.InstallerError) as raised,
        ):
            worker.install()

        self.assertIs(raised.exception.__cause__, expected)

    def test_install_does_not_wrap_keyboard_interrupt(self):
        """Should let process termination exceptions propagate."""
        package_path = os.path.join(self.recipe_cache, "Test.pkg")
        worker = self._installer(package_path)

        with (
            patch.object(worker, "verify_request", side_effect=KeyboardInterrupt),
            self.assertRaises(KeyboardInterrupt),
        ):
            worker.install()


@unittest.skipUnless(sys.platform == "darwin", "autopkgserver is macOS-only")
class TestItemCopierValidation(unittest.TestCase):
    """Test class for ItemCopier request validation."""

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.home = os.path.join(self.tmp_dir.name, "home")
        self.cache = os.path.join(self.home, "Library", "AutoPkg", "Cache")
        os.makedirs(self.cache)
        self.private_tmp = os.path.join(self.tmp_dir.name, "private_tmp")
        self.mountpoint = os.path.join(self.private_tmp, "mount")
        os.makedirs(self.mountpoint)
        Path(os.path.join(self.mountpoint, "Test.app")).touch()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _request(self, **item_overrides):
        item = {
            "source_item": "Test.app",
            "destination_path": os.path.join(self.cache, "installed"),
        }
        item.update(item_overrides)
        return {"mount_point": self.mountpoint, "items_to_copy": [item]}

    def _copier(self, request):
        return itemcopier.ItemCopier(MagicMock(), MagicMock(), request)

    @contextmanager
    def _patched_environment(self, mounted=True):
        with (
            patch.object(itemcopier, "PRIVATE_TMP", self.private_tmp),
            patch.object(
                itemcopier.os.path,
                "ismount",
                side_effect=lambda path: (
                    mounted
                    and os.path.realpath(path) == os.path.realpath(self.mountpoint)
                ),
            ),
        ):
            yield

    def test_accepts_confined_paths_and_safe_mode(self):
        """Should accept confined source paths and safe modes."""
        with self._patched_environment():
            worker = self._copier(self._request(mode="0755"))
            worker.verify_request()

        self.assertEqual(worker.mountpoint, os.path.realpath(self.mountpoint))

    def test_accepts_arbitrary_absolute_destination(self):
        """Should let trusted recipes choose an absolute destination outside
        the recipe cache, resolving it without rewriting or confining it."""
        destination_path = "/Library/Application Support/Test"
        item = {"source_item": "Test.app", "destination_path": destination_path}
        with self._patched_environment():
            worker = self._copier(self._request(destination_path=destination_path))
            worker.verify_request()
            source_itempath, destpath, full_destpath = worker.paths_for_item(item)

        self.assertEqual(worker.mountpoint, os.path.realpath(self.mountpoint))
        self.assertEqual(
            source_itempath, os.path.join(os.path.realpath(self.mountpoint), "Test.app")
        )
        self.assertEqual(destpath, os.path.realpath(destination_path))
        self.assertEqual(
            full_destpath, os.path.join(os.path.realpath(destination_path), "Test.app")
        )

    def test_rejects_unmounted_mount_point(self):
        """Should reject source roots that are not mounted volumes."""
        with self._patched_environment(mounted=False):
            worker = self._copier(self._request())
            with self.assertRaises(itemcopier.ItemCopierError):
                worker.verify_request()

    def test_rejects_mount_point_outside_private_tmp(self):
        """Should reject mount points outside the private temporary root."""
        outside_mount = os.path.join(self.tmp_dir.name, "outside_mount")
        os.makedirs(outside_mount)
        request = self._request()
        request["mount_point"] = outside_mount

        with self._patched_environment():
            worker = self._copier(request)
            with self.assertRaises(itemcopier.ItemCopierError):
                worker.verify_request()

    def test_rejects_source_parent_reference(self):
        """Should reject source paths with parent-directory references."""
        with self._patched_environment():
            worker = self._copier(self._request(source_item="../Test.app"))
            with self.assertRaises(itemcopier.ItemCopierError):
                worker.verify_request()

    def test_rejects_source_symlink_escape(self):
        """Should reject source symlinks that resolve outside the mount point."""
        outside_path = os.path.join(self.tmp_dir.name, "outside")
        Path(outside_path).touch()
        os.symlink(outside_path, os.path.join(self.mountpoint, "Linked.app"))

        with self._patched_environment():
            worker = self._copier(self._request(source_item="Linked.app"))
            with self.assertRaises(itemcopier.ItemCopierError):
                worker.verify_request()

    def test_rejects_destination_parent_reference(self):
        """Should reject destination paths with parent-directory references."""
        destination_path = os.path.join(self.cache, "..", "installed")
        with self._patched_environment():
            worker = self._copier(self._request(destination_path=destination_path))
            with self.assertRaises(itemcopier.ItemCopierError):
                worker.verify_request()

    def test_rejects_destination_item_parent_reference(self):
        """Should reject destination item paths with parent-directory references."""
        with self._patched_environment():
            worker = self._copier(self._request(destination_item="../Test.app"))
            with self.assertRaises(itemcopier.ItemCopierError):
                worker.verify_request()

    def test_rejects_relative_destination(self):
        """Should reject relative destination paths."""
        with self._patched_environment():
            worker = self._copier(self._request(destination_path="Applications"))
            with self.assertRaises(itemcopier.ItemCopierError):
                worker.verify_request()

    def test_rejects_setuid_and_setgid_modes(self):
        """Should reject modes that set setuid or setgid bits."""
        worker = self._copier(self._request())

        for mode in ("4755", "04755", "2755", "02755", "u+s", "g+rwxs", "a=rwxs"):
            with self.subTest(mode=mode):
                with self.assertRaises(itemcopier.ItemCopierError):
                    worker.verify_mode(mode)

    def test_accepts_safe_modes(self):
        """Should accept modes that do not set setuid or setgid bits."""
        worker = self._copier(self._request())

        for mode in ("0755", "755", "o-w", "u-s", "u=rwX,go=rX"):
            with self.subTest(mode=mode):
                worker.verify_mode(mode)

    @contextmanager
    def _patched_copy(self):
        """Run a real copy, stubbing only what a non-root test user can't do.

        Ownership is requested as root:admin, so os.lchown has to be stubbed;
        everything else (removal, copying, xattr lookup) runs for real."""
        copied_attrs = MagicMock()
        copied_attrs.list.return_value = []
        with (
            self._patched_environment(),
            patch.object(itemcopier.os, "lchown") as lchown,
            patch.object(
                itemcopier.subprocess, "call", return_value=0
            ) as subprocess_call,
            patch.object(
                itemcopier.xattr, "xattr", return_value=copied_attrs
            ) as xattr_call,
        ):
            yield lchown, subprocess_call, xattr_call

    def test_copy_items_processes_all_items(self):
        """Should copy every requested item, then set owner, group, and mode."""
        destination_path = os.path.join(self.cache, "installed")
        os.makedirs(destination_path)
        Path(os.path.join(self.mountpoint, "Second.app")).touch()
        request = self._request(destination_path=destination_path)
        request["items_to_copy"].append(
            {
                "source_item": "Second.app",
                "destination_path": destination_path,
            }
        )
        real_destination_path = os.path.realpath(destination_path)
        dest_paths = [
            os.path.join(real_destination_path, "Test.app"),
            os.path.join(real_destination_path, "Second.app"),
        ]
        admin_gid = grp.getgrnam("admin").gr_gid

        with self._patched_copy() as (lchown, subprocess_call, xattr_call):
            worker = self._copier(request)
            worker.verify_request()
            self.assertTrue(worker.copy_items())

        # The copies are real files now, not a mocked-out /bin/cp invocation.
        for dest_path in dest_paths:
            self.assertTrue(os.path.isfile(dest_path))
        self.assertEqual(
            [args for args, _ in lchown.call_args_list],
            [(dest_path, 0, admin_gid) for dest_path in dest_paths],
        )
        # chmod is the one remaining shell-out; it takes symbolic modes.
        self.assertEqual(
            [args[0] for args, _ in subprocess_call.call_args_list],
            [["/bin/chmod", "-R", "o-w", dest_path] for dest_path in dest_paths],
        )
        self.assertEqual(
            [args[0] for args, _ in xattr_call.call_args_list],
            dest_paths,
        )

    def test_copy_items_replaces_an_existing_file_destination(self):
        """A destination that is a file, not a directory, must still be
        replaced. shutil.rmtree alone would raise NotADirectoryError here."""
        destination_path = os.path.join(self.cache, "installed")
        os.makedirs(destination_path)
        dest_path = os.path.join(os.path.realpath(destination_path), "Test.app")
        Path(dest_path).write_text("stale")
        Path(os.path.join(self.mountpoint, "Test.app")).write_text("fresh")

        with self._patched_copy():
            worker = self._copier(self._request(destination_path=destination_path))
            worker.verify_request()
            self.assertTrue(worker.copy_items())

        self.assertEqual(Path(dest_path).read_text(), "fresh")

    def test_copy_items_copies_a_directory_and_keeps_symlinks_as_links(self):
        """A bundle is a directory tree, and its internal symlinks have to stay
        symlinks rather than being resolved into copies of their targets."""
        source_bundle = os.path.join(self.mountpoint, "Bundle.app")
        os.makedirs(os.path.join(source_bundle, "Contents"))
        Path(os.path.join(source_bundle, "Contents", "real")).write_text("data")
        os.symlink("real", os.path.join(source_bundle, "Contents", "alias"))
        destination_path = os.path.join(self.cache, "installed")
        os.makedirs(destination_path)
        dest_bundle = os.path.join(os.path.realpath(destination_path), "Bundle.app")

        with self._patched_copy():
            worker = self._copier(
                self._request(
                    source_item="Bundle.app", destination_path=destination_path
                )
            )
            worker.verify_request()
            self.assertTrue(worker.copy_items())

        self.assertEqual(
            Path(os.path.join(dest_bundle, "Contents", "real")).read_text(), "data"
        )
        self.assertTrue(os.path.islink(os.path.join(dest_bundle, "Contents", "alias")))

    def test_resolve_id_accepts_names_and_numeric_ids(self):
        """chown(8) and chgrp(8) take either, so the native path has to too."""
        self.assertEqual(
            itemcopier.resolve_id("admin", lambda n: grp.getgrnam(n).gr_gid, "group"),
            grp.getgrnam("admin").gr_gid,
        )
        self.assertEqual(itemcopier.resolve_id("80", lambda n: None, "group"), 80)
        self.assertEqual(itemcopier.resolve_id(80, lambda n: None, "group"), 80)

    def test_resolve_id_rejects_an_unknown_name(self):
        """An unknown name used to surface only as a chown exit code."""
        with self.assertRaises(itemcopier.ItemCopierError):
            itemcopier.resolve_id(
                "no.such.group", lambda n: grp.getgrnam(n).gr_gid, "group"
            )

    def test_copy_items_does_not_wrap_keyboard_interrupt_from_xattr(self):
        """Should let process termination exceptions propagate."""
        destination_path = os.path.join(self.cache, "installed")
        os.makedirs(destination_path)
        request = self._request(destination_path=destination_path)
        copied_attrs = MagicMock()
        copied_attrs.list.side_effect = KeyboardInterrupt

        with (
            self._patched_environment(),
            patch.object(itemcopier.os, "lchown"),
            patch.object(itemcopier.subprocess, "call", return_value=0),
            patch.object(itemcopier.xattr, "xattr", return_value=copied_attrs),
        ):
            worker = self._copier(request)
            worker.verify_request()
            with self.assertRaises(KeyboardInterrupt):
                worker.copy_items()

    def test_copy_does_not_wrap_keyboard_interrupt(self):
        """Should let process termination exceptions propagate."""
        worker = self._copier(self._request())

        with (
            patch.object(worker, "verify_request", side_effect=KeyboardInterrupt),
            self.assertRaises(KeyboardInterrupt),
        ):
            worker.copy()

    def test_copy_preserves_itemcopier_errors(self):
        """Should not wrap validation errors in another ItemCopierError."""
        worker = self._copier(self._request())
        expected = itemcopier.ItemCopierError("invalid request")

        with (
            patch.object(worker, "verify_request", side_effect=expected),
            self.assertRaises(itemcopier.ItemCopierError) as raised,
        ):
            worker.copy()

        self.assertIs(raised.exception, expected)

    def test_copy_chains_unexpected_errors(self):
        """Should retain the cause when adapting an unexpected exception."""
        worker = self._copier(self._request())
        expected = RuntimeError("unexpected failure")

        with (
            patch.object(worker, "verify_request", side_effect=expected),
            self.assertRaises(itemcopier.ItemCopierError) as raised,
        ):
            worker.copy()

        self.assertIs(raised.exception.__cause__, expected)


if __name__ == "__main__":
    unittest.main()
