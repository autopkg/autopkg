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
import plistlib
import re
import sys
import tempfile
import unittest
from io import StringIO
from unittest.mock import patch

# Add the Code directory to the Python path to resolve autopkg dependencies
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests import load_autopkg_module

autopkg = load_autopkg_module()


class TestClearCache(unittest.TestCase):
    """Test cases for the `autopkg clear-cache` verb."""

    def setUp(self):
        """Silence recipe-map side effects (see test_autopkg_recipes for
        rationale)."""
        self._recipe_map_patches = [
            patch("autopkg.calculate_recipe_map"),
            patch("autopkg.read_recipe_map"),
        ]
        for patcher in self._recipe_map_patches:
            patcher.start()

    def tearDown(self):
        for patcher in self._recipe_map_patches:
            patcher.stop()

    def _write_recipe(self, path, recipe):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            plistlib.dump(recipe, f)

    def _run_clear_cache(
        self, argv_tail, cache_dir, search_dirs=None, override_dirs=None
    ):
        search_dirs = search_dirs or []
        override_dirs = override_dirs or []

        def pref(key):
            return cache_dir if key == "CACHE_DIR" else None

        with (
            patch("autopkg.get_pref", side_effect=pref),
            patch("autopkg.get_search_dirs", return_value=search_dirs),
            patch("autopkg.get_override_dirs", return_value=override_dirs),
            patch.dict(
                autopkg.globalRecipeMap,
                {
                    "identifiers": {},
                    "shortnames": {},
                    "overrides": {},
                    "overrides-identifiers": {},
                },
                clear=True,
            ),
            patch("sys.stdout", new_callable=StringIO) as stdout,
            patch("sys.stderr", new_callable=StringIO) as stderr,
        ):
            result = autopkg.clear_cache(["autopkg", "clear-cache", *argv_tail])
            return result, stdout.getvalue(), stderr.getvalue()

    def test_clear_cache_registered_in_subcommands(self):
        """The clear-cache verb should show up in the main() dispatch dict."""
        captured = []

        def fake_display_help(argv, subcommands):
            captured.append(subcommands)
            return 1

        with patch("autopkg.display_help", side_effect=fake_display_help):
            autopkg.main(["autopkg", "help"])

        self.assertTrue(captured)
        self.assertIs(captured[0]["clear-cache"]["function"], autopkg.clear_cache)

    def test_clear_cache_recipe_removes_resolved_identifier_cache(self):
        """Recipe shortname lookup removes only that recipe's cache directory."""
        recipe = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "Input": {},
            "Process": [],
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_dir = os.path.join(tmp_dir, "cache")
            recipes_dir = os.path.join(tmp_dir, "recipes")
            target = os.path.join(cache_dir, "com.example.test")
            os.makedirs(os.path.join(target, "downloads"))
            self._write_recipe(os.path.join(recipes_dir, "Test.recipe"), recipe)

            result, stdout, stderr = self._run_clear_cache(
                ["--search-dir", recipes_dir, "Test"],
                cache_dir,
                search_dirs=[recipes_dir],
            )

            self.assertEqual(result, 0, stderr)
            self.assertIn(f"Removing {target}", stdout)
            self.assertFalse(os.path.exists(target))
            self.assertTrue(os.path.isdir(cache_dir))

    def test_clear_cache_recipe_can_resolve_by_identifier(self):
        """Recipe identifier lookup matches run/info resolution behavior."""
        recipe = {
            "Description": "Test recipe",
            "Identifier": "com.example.identifier",
            "Input": {},
            "Process": [],
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_dir = os.path.join(tmp_dir, "cache")
            recipes_dir = os.path.join(tmp_dir, "recipes")
            target = os.path.join(cache_dir, "com.example.identifier")
            os.makedirs(target)
            self._write_recipe(
                os.path.join(recipes_dir, "DifferentName.recipe"), recipe
            )

            result, stdout, stderr = self._run_clear_cache(
                ["--search-dir", recipes_dir, "com.example.identifier"],
                cache_dir,
                search_dirs=[recipes_dir],
            )

            self.assertEqual(result, 0, stderr)
            self.assertIn(f"Removing {target}", stdout)
            self.assertFalse(os.path.exists(target))

    def test_clear_cache_recipe_dry_run_leaves_cache(self):
        """Dry-run reports the recipe cache path without deleting it."""
        recipe = {
            "Description": "Test recipe",
            "Identifier": "com.example.dryrun",
            "Input": {},
            "Process": [],
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_dir = os.path.join(tmp_dir, "cache")
            recipes_dir = os.path.join(tmp_dir, "recipes")
            target = os.path.join(cache_dir, "com.example.dryrun")
            os.makedirs(target)
            self._write_recipe(os.path.join(recipes_dir, "DryRun.recipe"), recipe)

            result, stdout, stderr = self._run_clear_cache(
                ["--dry-run", "--search-dir", recipes_dir, "DryRun"],
                cache_dir,
                search_dirs=[recipes_dir],
            )

            self.assertEqual(result, 0, stderr)
            self.assertIn(f"Would remove {target}", stdout)
            self.assertTrue(os.path.isdir(target))

    def test_clear_cache_recipe_missing_cache_is_error(self):
        """A resolved recipe with no cache directory is a non-zero result."""
        recipe = {
            "Description": "Test recipe",
            "Identifier": "com.example.missing",
            "Input": {},
            "Process": [],
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_dir = os.path.join(tmp_dir, "cache")
            recipes_dir = os.path.join(tmp_dir, "recipes")
            os.makedirs(cache_dir)
            self._write_recipe(os.path.join(recipes_dir, "Missing.recipe"), recipe)

            result, stdout, stderr = self._run_clear_cache(
                ["--search-dir", recipes_dir, "Missing"],
                cache_dir,
                search_dirs=[recipes_dir],
            )

            self.assertEqual(result, 1)
            self.assertEqual(stdout, "")
            self.assertIn("Recipe cache directory does not exist", stderr)

    def test_clear_cache_recipe_requires_explicit_identifier(self):
        """Recipe cache deletion does not use the run-time pseudo identifier."""
        recipe = {
            "Description": "Test recipe",
            "Input": {},
            "Process": [],
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_dir = os.path.join(tmp_dir, "cache")
            recipes_dir = os.path.join(tmp_dir, "recipes")
            recipe_path = os.path.join(recipes_dir, "NoIdentifier.recipe")
            self._write_recipe(recipe_path, recipe)

            # Create a path-derived cache directory standing in for the
            # run-time pseudo identifier. Split on either separator and drop
            # empty/drive parts so the result is a safe relative directory
            # name on both POSIX and Windows.
            pseudo_identifier = "-".join(
                part
                for part in re.split(
                    r"[\\/]", autopkg.remove_recipe_extension(recipe_path)
                )
                if part and ":" not in part
            )
            pseudo_target = os.path.join(cache_dir, pseudo_identifier)
            os.makedirs(pseudo_target)

            result, stdout, stderr = self._run_clear_cache(
                ["--search-dir", recipes_dir, "NoIdentifier"],
                cache_dir,
                search_dirs=[recipes_dir],
            )

            self.assertEqual(result, 1)
            self.assertEqual(stdout, "")
            self.assertIn("Could not determine recipe identifier", stderr)
            self.assertTrue(os.path.isdir(pseudo_target))

    def test_clear_cache_all_removes_contents_not_cache_dir(self):
        """The all target clears cache contents but leaves CACHE_DIR itself."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_dir = os.path.join(tmp_dir, "cache")
            child_dir = os.path.join(cache_dir, "com.example.one")
            child_file = os.path.join(cache_dir, "autopkg_results.plist")
            os.makedirs(child_dir)
            with open(child_file, "w", encoding="utf-8") as f:
                f.write("results")

            result, stdout, stderr = self._run_clear_cache(["all"], cache_dir)

            self.assertEqual(result, 0, stderr)
            # Without -v, the all target prints a summary, not each item.
            self.assertIn(cache_dir, stdout)
            self.assertNotIn(child_dir, stdout)
            self.assertNotIn(child_file, stdout)
            self.assertTrue(os.path.isdir(cache_dir))
            self.assertEqual(os.listdir(cache_dir), [])

    def test_clear_cache_all_verbose_lists_recipe_dirs_not_files(self):
        """-v lists each one-level cache item but not their contents."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_dir = os.path.join(tmp_dir, "cache")
            child_dir = os.path.join(cache_dir, "com.example.one")
            nested_file = os.path.join(child_dir, "downloads", "App.dmg")
            os.makedirs(os.path.dirname(nested_file))
            with open(nested_file, "w", encoding="utf-8") as f:
                f.write("dmg")

            result, stdout, stderr = self._run_clear_cache(["-v", "all"], cache_dir)

            self.assertEqual(result, 0, stderr)
            self.assertIn(f"Removing {child_dir}", stdout)
            self.assertNotIn(nested_file, stdout)
            self.assertEqual(os.listdir(cache_dir), [])

    def test_clear_cache_all_very_verbose_lists_files(self):
        """-vv lists every file within each cache item."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_dir = os.path.join(tmp_dir, "cache")
            child_dir = os.path.join(cache_dir, "com.example.one")
            nested_file = os.path.join(child_dir, "downloads", "App.dmg")
            os.makedirs(os.path.dirname(nested_file))
            with open(nested_file, "w", encoding="utf-8") as f:
                f.write("dmg")

            result, stdout, stderr = self._run_clear_cache(["-vv", "all"], cache_dir)

            self.assertEqual(result, 0, stderr)
            self.assertIn(f"Removing {child_dir}", stdout)
            self.assertIn(f"Removing {nested_file}", stdout)
            self.assertEqual(os.listdir(cache_dir), [])

    def test_clear_cache_recipe_very_verbose_lists_files(self):
        """-vv on a recipe lists the files inside its cache directory."""
        recipe = {
            "Description": "Test recipe",
            "Identifier": "com.example.test",
            "Input": {},
            "Process": [],
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_dir = os.path.join(tmp_dir, "cache")
            recipes_dir = os.path.join(tmp_dir, "recipes")
            target = os.path.join(cache_dir, "com.example.test")
            nested_file = os.path.join(target, "downloads", "App.dmg")
            os.makedirs(os.path.dirname(nested_file))
            with open(nested_file, "w", encoding="utf-8") as f:
                f.write("dmg")
            self._write_recipe(os.path.join(recipes_dir, "Test.recipe"), recipe)

            result, stdout, stderr = self._run_clear_cache(
                ["-vv", "--search-dir", recipes_dir, "Test"],
                cache_dir,
                search_dirs=[recipes_dir],
            )

            self.assertEqual(result, 0, stderr)
            self.assertIn(f"Removing {target}", stdout)
            self.assertIn(f"Removing {nested_file}", stdout)
            self.assertFalse(os.path.exists(target))

    def test_clear_cache_all_empty_cache_is_success(self):
        """The all target treats an already-empty cache directory as success."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_dir = os.path.join(tmp_dir, "cache")
            os.makedirs(cache_dir)

            result, stdout, stderr = self._run_clear_cache(["all"], cache_dir)

            self.assertEqual(result, 0, stderr)
            self.assertEqual(stdout, "")
            self.assertEqual(os.listdir(cache_dir), [])

    def test_clear_cache_missing_cache_dir_is_error(self):
        """Missing CACHE_DIR is a non-zero result."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_dir = os.path.join(tmp_dir, "missing")

            result, stdout, stderr = self._run_clear_cache(["all"], cache_dir)

            self.assertEqual(result, 1)
            self.assertEqual(stdout, "")
            self.assertIn("Cache directory does not exist", stderr)

    def test_clear_cache_refuses_identifier_outside_cache_dir(self):
        """A hostile recipe identifier cannot escape CACHE_DIR."""
        recipe = {
            "Description": "Bad recipe",
            "Identifier": "../escape",
            "Input": {},
            "Process": [],
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_dir = os.path.join(tmp_dir, "cache")
            recipes_dir = os.path.join(tmp_dir, "recipes")
            os.makedirs(cache_dir)
            self._write_recipe(os.path.join(recipes_dir, "Bad.recipe"), recipe)

            result, stdout, stderr = self._run_clear_cache(
                ["--search-dir", recipes_dir, "Bad"],
                cache_dir,
                search_dirs=[recipes_dir],
            )

            self.assertEqual(result, 1)
            self.assertEqual(stdout, "")
            self.assertIn("resolves outside CACHE_DIR", stderr)
            self.assertFalse(os.path.exists(os.path.join(tmp_dir, "escape")))

    def test_clear_cache_override_uses_override_identifier(self):
        """Override resolution clears the override cache, matching run."""
        parent = {
            "Description": "Parent recipe",
            "Identifier": "com.example.parent",
            "Input": {"NAME": "Parent"},
            "Process": [],
        }
        override = {
            "Identifier": "local.parent.override",
            "Input": {"NAME": "Override"},
            "ParentRecipe": "com.example.parent",
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache_dir = os.path.join(tmp_dir, "cache")
            recipes_dir = os.path.join(tmp_dir, "recipes")
            overrides_dir = os.path.join(tmp_dir, "overrides")
            target = os.path.join(cache_dir, "local.parent.override")
            parent_target = os.path.join(cache_dir, "com.example.parent")
            os.makedirs(target)
            os.makedirs(parent_target)
            self._write_recipe(os.path.join(recipes_dir, "Parent.recipe"), parent)
            self._write_recipe(os.path.join(overrides_dir, "Parent.recipe"), override)

            result, stdout, stderr = self._run_clear_cache(
                [
                    "--search-dir",
                    recipes_dir,
                    "--override-dir",
                    overrides_dir,
                    "Parent",
                ],
                cache_dir,
                search_dirs=[recipes_dir],
                override_dirs=[overrides_dir],
            )

            self.assertEqual(result, 0, stderr)
            self.assertIn(f"Removing {target}", stdout)
            self.assertFalse(os.path.exists(target))
            self.assertTrue(os.path.isdir(parent_target))


if __name__ == "__main__":
    unittest.main()
