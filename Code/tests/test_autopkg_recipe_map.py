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

"""Tests for the recipe map backported from dev-3.x.

Covers:
* Lookup helpers (find_recipe_by_id_in_map, find_recipe_by_name_in_map,
  find_identifier_from_name, find_name_from_identifier).
* Persistence (write_recipe_map_to_disk, handle_reading_recipe_map_file,
  validate_recipe_map).
* Rebuild behaviour (map_key_to_paths, calculate_recipe_map).
* read_recipe_map auto-create UX divergence from dev-3.x.
* The `autopkg generate-recipe-map` verb.

All filesystem I/O is done against per-test temporary directories so
these tests are hermetic and safe to run in parallel with others."""

import importlib
import importlib.machinery
import io
import json
import os
import plistlib
import sys
import tempfile
import unittest
from unittest.mock import patch

import autopkglib

autopkg_path = os.path.join(os.path.dirname(__file__), "..", "autopkg")
loader = importlib.machinery.SourceFileLoader("autopkg", autopkg_path)
autopkg = loader.load_module()
sys.modules["autopkg"] = autopkg


# Sample on-disk recipe used to populate temp repos.
SAMPLE_RECIPE = {
    "Description": "Sample test recipe.",
    "Identifier": "com.example.test.sample",
    "Input": {"NAME": "Sample"},
    "MinimumVersion": "2.3",
    "Process": [{"Processor": "URLDownloader"}],
}

SAMPLE_OVERRIDE = {
    "Identifier": "local.sample.override",
    "Input": {"NAME": "Sample"},
    "ParentRecipe": "com.example.test.sample",
}


def _write_plist_recipe(path, recipe_dict):
    """Write a plist-format recipe to ``path``."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        plistlib.dump(recipe_dict, f)


class _RecipeMapIsolationMixin:
    """Mixin that resets ``autopkglib.globalRecipeMap`` between tests and
    redirects ``DEFAULT_RECIPE_MAP`` to a temp location so tests never
    touch the developer's real ``~/Library/AutoPkg`` directory."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="autopkg_recipe_map_test_")
        self.addCleanup(self._cleanup_tmp)

        self._saved_map = dict(autopkglib.globalRecipeMap)
        self._saved_default = autopkglib.DEFAULT_RECIPE_MAP
        autopkglib.globalRecipeMap = {
            "identifiers": {},
            "shortnames": {},
            "overrides": {},
            "overrides-identifiers": {},
        }
        autopkglib.DEFAULT_RECIPE_MAP = os.path.join(self.tmpdir, "recipe_map.json")
        # Mirror the constant into the autopkg module so verb code that
        # references it (e.g. generate-recipe-map's log line) picks up
        # the test-local path too.
        autopkg.DEFAULT_RECIPE_MAP = autopkglib.DEFAULT_RECIPE_MAP

    def tearDown(self):
        autopkglib.globalRecipeMap = self._saved_map
        autopkglib.DEFAULT_RECIPE_MAP = self._saved_default
        autopkg.DEFAULT_RECIPE_MAP = self._saved_default

    def _cleanup_tmp(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)


class TestRecipeMapLookups(_RecipeMapIsolationMixin, unittest.TestCase):
    """Covers find_recipe_by_id_in_map / find_recipe_by_name_in_map and
    the reverse lookup helpers."""

    def setUp(self):
        super().setUp()
        # Write a real recipe on disk so valid_recipe_file returns True.
        self.recipe_path = os.path.join(self.tmpdir, "Sample.recipe")
        _write_plist_recipe(self.recipe_path, SAMPLE_RECIPE)
        self.override_path = os.path.join(self.tmpdir, "Override.recipe")
        _write_plist_recipe(self.override_path, SAMPLE_OVERRIDE)

        autopkglib.globalRecipeMap = {
            "identifiers": {SAMPLE_RECIPE["Identifier"]: self.recipe_path},
            "shortnames": {"Sample": self.recipe_path},
            "overrides": {"Override": self.override_path},
            "overrides-identifiers": {
                SAMPLE_OVERRIDE["Identifier"]: self.override_path
            },
        }

    def test_find_by_id_prefers_override(self):
        """An override identifier beats a stock recipe identifier."""
        result = autopkglib.find_recipe_by_id_in_map(SAMPLE_OVERRIDE["Identifier"])
        self.assertEqual(result, self.override_path)

    def test_find_by_id_skip_overrides(self):
        """skip_overrides=True ignores the overrides-identifiers dict."""
        # Seed an override with the same identifier as a stock recipe.
        autopkglib.globalRecipeMap["overrides-identifiers"][
            SAMPLE_RECIPE["Identifier"]
        ] = self.override_path
        result = autopkglib.find_recipe_by_id_in_map(
            SAMPLE_RECIPE["Identifier"], skip_overrides=True
        )
        self.assertEqual(result, self.recipe_path)

    def test_find_by_id_returns_none_for_missing(self):
        self.assertIsNone(
            autopkglib.find_recipe_by_id_in_map("com.example.does.not.exist")
        )

    def test_find_by_id_returns_none_for_stale_path(self):
        """If the cached path is missing on disk the lookup returns None."""
        autopkglib.globalRecipeMap["identifiers"][SAMPLE_RECIPE["Identifier"]] = (
            "/nonexistent/path.recipe"
        )
        # Override identifier still resolves though...
        autopkglib.globalRecipeMap["overrides-identifiers"] = {}
        self.assertIsNone(
            autopkglib.find_recipe_by_id_in_map(SAMPLE_RECIPE["Identifier"])
        )

    def test_find_by_name_prefers_override(self):
        """Shortname lookup prefers an override by name."""
        # Add an override with the same shortname as the stock recipe.
        autopkglib.globalRecipeMap["overrides"]["Sample"] = self.override_path
        result = autopkglib.find_recipe_by_name_in_map("Sample")
        self.assertEqual(result, self.override_path)

    def test_find_by_name_skip_overrides(self):
        autopkglib.globalRecipeMap["overrides"]["Sample"] = self.override_path
        result = autopkglib.find_recipe_by_name_in_map("Sample", skip_overrides=True)
        self.assertEqual(result, self.recipe_path)

    def test_find_by_name_returns_none_for_missing(self):
        self.assertIsNone(autopkglib.find_recipe_by_name_in_map("NopeRecipe"))

    def test_find_name_from_identifier(self):
        self.assertEqual(
            autopkglib.find_name_from_identifier(SAMPLE_RECIPE["Identifier"]),
            "Sample",
        )

    def test_find_name_from_identifier_missing_logs_and_returns_none(self):
        with patch.object(autopkglib, "log_err") as mock_log_err:
            self.assertIsNone(
                autopkglib.find_name_from_identifier("com.example.missing")
            )
            mock_log_err.assert_called()

    def test_find_identifier_from_name(self):
        self.assertEqual(
            autopkglib.find_identifier_from_name("Sample"),
            SAMPLE_RECIPE["Identifier"],
        )

    def test_find_identifier_from_name_missing_logs_and_returns_none(self):
        with patch.object(autopkglib, "log_err") as mock_log_err:
            self.assertIsNone(autopkglib.find_identifier_from_name("Nope"))
            mock_log_err.assert_called()


class TestRecipeMapPersistence(_RecipeMapIsolationMixin, unittest.TestCase):
    """write_recipe_map_to_disk / handle_reading_recipe_map_file /
    validate_recipe_map."""

    def test_write_then_read_roundtrip(self):
        autopkglib.globalRecipeMap.clear()
        autopkglib.globalRecipeMap.update(
            {
                "identifiers": {"com.example.a": "/tmp/a.recipe"},
                "shortnames": {"A": "/tmp/a.recipe"},
                "overrides": {},
                "overrides-identifiers": {},
            }
        )
        autopkglib.write_recipe_map_to_disk()
        self.assertTrue(os.path.exists(autopkglib.DEFAULT_RECIPE_MAP))
        result = autopkglib.handle_reading_recipe_map_file()
        # Persisted file additionally carries a schema_version key; the
        # four sub-dicts must match.
        self.assertEqual(
            result.get("schema_version"), autopkglib.RECIPE_MAP_SCHEMA_VERSION
        )
        for key in ("identifiers", "shortnames", "overrides", "overrides-identifiers"):
            self.assertEqual(result[key], autopkglib.globalRecipeMap[key])

    def test_write_is_sorted_for_stable_diffs(self):
        """The file should use sort_keys=True so repeated regenerations
        produce byte-identical output."""
        autopkglib.globalRecipeMap = {
            "identifiers": {"com.example.b": "/b.recipe", "com.example.a": "/a.recipe"},
            "shortnames": {"B": "/b.recipe", "A": "/a.recipe"},
            "overrides": {},
            "overrides-identifiers": {},
        }
        autopkglib.write_recipe_map_to_disk()
        with open(autopkglib.DEFAULT_RECIPE_MAP) as f:
            text = f.read()
        # Keys should appear in alphabetical order.
        self.assertLess(text.find('"com.example.a"'), text.find('"com.example.b"'))
        self.assertLess(text.find('"identifiers"'), text.find('"shortnames"'))

    def test_read_missing_file_returns_empty_dict_silently(self):
        """A brand-new install has no map file; that must be a non-fatal
        condition (not a log_err)."""
        # File does not exist in the temp dir.
        with patch.object(autopkglib, "log_err") as mock_log_err:
            result = autopkglib.handle_reading_recipe_map_file()
            self.assertEqual(result, {})
            mock_log_err.assert_not_called()

    def test_read_corrupt_file_logs_and_returns_empty(self):
        with open(autopkglib.DEFAULT_RECIPE_MAP, "w") as f:
            f.write("not valid json {{{")
        with patch.object(autopkglib, "log_err") as mock_log_err:
            result = autopkglib.handle_reading_recipe_map_file()
            self.assertEqual(result, {})
            mock_log_err.assert_called()

    def test_write_tolerates_osError(self):
        """A permission error during write should log a warning, not raise."""
        with (
            patch("builtins.open", side_effect=OSError("nope")),
            patch.object(autopkglib, "log_err") as mock_log_err,
        ):
            # Must not raise.
            autopkglib.write_recipe_map_to_disk()
            mock_log_err.assert_called()

    def test_validate_recipe_map_happy_path(self):
        self.assertTrue(
            autopkglib.validate_recipe_map(
                {
                    "identifiers": {},
                    "shortnames": {},
                    "overrides": {},
                    "overrides-identifiers": {},
                }
            )
        )

    def test_validate_recipe_map_missing_key(self):
        self.assertFalse(
            autopkglib.validate_recipe_map(
                {"identifiers": {}, "shortnames": {}, "overrides": {}}
            )
        )

    def test_validate_recipe_map_extra_keys_are_fine(self):
        """Forward-compat: future keys shouldn't cause validation failure."""
        self.assertTrue(
            autopkglib.validate_recipe_map(
                {
                    "identifiers": {},
                    "shortnames": {},
                    "overrides": {},
                    "overrides-identifiers": {},
                    "future_key": {},
                }
            )
        )


class TestMapKeyToPaths(_RecipeMapIsolationMixin, unittest.TestCase):
    """map_key_to_paths should walk a directory one level deep and emit
    first-wins entries keyed correctly for both identifiers and shortnames."""

    def setUp(self):
        super().setUp()
        self.recipe_a = os.path.join(self.tmpdir, "RecipeA.recipe")
        self.recipe_b = os.path.join(self.tmpdir, "sub", "RecipeB.recipe")
        self.recipe_c = os.path.join(self.tmpdir, "sub", "deeper", "RecipeC.recipe")
        _write_plist_recipe(
            self.recipe_a, {**SAMPLE_RECIPE, "Identifier": "com.example.a"}
        )
        _write_plist_recipe(
            self.recipe_b, {**SAMPLE_RECIPE, "Identifier": "com.example.b"}
        )
        _write_plist_recipe(
            self.recipe_c, {**SAMPLE_RECIPE, "Identifier": "com.example.c"}
        )

    def test_shortnames_key(self):
        result = autopkglib.map_key_to_paths("shortnames", self.tmpdir)
        # Top-level and one-level-deep are found; deeper ones are not.
        self.assertIn("RecipeA", result)
        self.assertIn("RecipeB", result)
        self.assertNotIn("RecipeC", result)
        self.assertEqual(result["RecipeA"], self.recipe_a)

    def test_identifiers_key_reads_from_file(self):
        result = autopkglib.map_key_to_paths("identifiers", self.tmpdir)
        self.assertIn("com.example.a", result)
        self.assertIn("com.example.b", result)
        self.assertEqual(result["com.example.a"], self.recipe_a)

    def test_overrides_identifiers_key_reads_identifier_field(self):
        """The 'overrides-identifiers' keyname should also read the
        Identifier field (the helper tests for the substring
        'identifiers')."""
        # Place an override-shaped file in its own dir.
        override_dir = os.path.join(self.tmpdir, "ovr")
        override_path = os.path.join(override_dir, "ov.recipe")
        _write_plist_recipe(override_path, SAMPLE_OVERRIDE)
        result = autopkglib.map_key_to_paths("overrides-identifiers", override_dir)
        self.assertEqual(result, {SAMPLE_OVERRIDE["Identifier"]: override_path})

    def test_first_wins_for_duplicates(self):
        """Duplicate shortnames should preserve the first discovery."""
        # Two recipes with the same shortname in different subdirs.
        dup_a = os.path.join(self.tmpdir, "dir1", "DuplicateName.recipe")
        dup_b = os.path.join(self.tmpdir, "dir2", "DuplicateName.recipe")
        _write_plist_recipe(dup_a, {**SAMPLE_RECIPE, "Identifier": "com.example.dup1"})
        _write_plist_recipe(dup_b, {**SAMPLE_RECIPE, "Identifier": "com.example.dup2"})
        result = autopkglib.map_key_to_paths("shortnames", self.tmpdir)
        # Only one entry; first-wins semantics.
        self.assertIn("DuplicateName", result)
        self.assertIn(result["DuplicateName"], {dup_a, dup_b})


class TestCalculateRecipeMap(_RecipeMapIsolationMixin, unittest.TestCase):
    """End-to-end tests for calculate_recipe_map: honours prefs, writes to
    disk only when appropriate, and skips '.' by default."""

    def setUp(self):
        super().setUp()
        # Two "repos": one recipes dir, one overrides dir.
        self.recipes_dir = os.path.join(self.tmpdir, "repo")
        self.overrides_dir = os.path.join(self.tmpdir, "ovrs")
        os.makedirs(self.recipes_dir)
        os.makedirs(self.overrides_dir)
        _write_plist_recipe(
            os.path.join(self.recipes_dir, "Sample.recipe"), SAMPLE_RECIPE
        )
        _write_plist_recipe(
            os.path.join(self.overrides_dir, "Override.recipe"), SAMPLE_OVERRIDE
        )

    def _run_with_prefs(self, **overrides):
        def _fake_get_pref(key):
            return overrides.get(key)

        return patch.object(autopkglib, "get_pref", side_effect=_fake_get_pref)

    def test_populates_all_four_dicts(self):
        with self._run_with_prefs(
            RECIPE_SEARCH_DIRS=[self.recipes_dir],
            RECIPE_OVERRIDE_DIRS=[self.overrides_dir],
        ):
            autopkglib.calculate_recipe_map()

        rm = autopkglib.globalRecipeMap
        self.assertEqual(
            rm["identifiers"],
            {
                SAMPLE_RECIPE["Identifier"]: os.path.join(
                    self.recipes_dir, "Sample.recipe"
                )
            },
        )
        self.assertEqual(
            rm["shortnames"],
            {"Sample": os.path.join(self.recipes_dir, "Sample.recipe")},
        )
        self.assertEqual(
            rm["overrides"],
            {"Override": os.path.join(self.overrides_dir, "Override.recipe")},
        )
        self.assertEqual(
            rm["overrides-identifiers"],
            {
                SAMPLE_OVERRIDE["Identifier"]: os.path.join(
                    self.overrides_dir, "Override.recipe"
                )
            },
        )

    def test_persists_when_no_extras(self):
        with self._run_with_prefs(
            RECIPE_SEARCH_DIRS=[self.recipes_dir],
            RECIPE_OVERRIDE_DIRS=[self.overrides_dir],
        ):
            autopkglib.calculate_recipe_map()
        self.assertTrue(os.path.exists(autopkglib.DEFAULT_RECIPE_MAP))

    def test_does_not_persist_when_extras_supplied(self):
        """Passing extra_search_dirs / extra_override_dirs keeps the
        result in-memory only so callers can build transient views."""
        with self._run_with_prefs(
            RECIPE_SEARCH_DIRS=[],
            RECIPE_OVERRIDE_DIRS=[],
        ):
            autopkglib.calculate_recipe_map(
                extra_search_dirs=[self.recipes_dir],
                extra_override_dirs=[self.overrides_dir],
            )
        self.assertFalse(os.path.exists(autopkglib.DEFAULT_RECIPE_MAP))
        # Map is still populated in-memory.
        self.assertEqual(len(autopkglib.globalRecipeMap["identifiers"]), 1)

    def test_skips_cwd_by_default(self):
        """'.' should not be walked unless explicitly requested."""
        with self._run_with_prefs(
            RECIPE_SEARCH_DIRS=[".", self.recipes_dir],
            RECIPE_OVERRIDE_DIRS=[self.overrides_dir],
        ):
            # We mock glob.glob to detect if '.' was walked.
            seen_dirs = []
            real_glob = autopkglib.glob.glob

            def tracking_glob(pattern, *args, **kwargs):
                seen_dirs.append(pattern)
                return real_glob(pattern, *args, **kwargs)

            with patch.object(autopkglib.glob, "glob", side_effect=tracking_glob):
                autopkglib.calculate_recipe_map()

        # No pattern should be anchored at the current working directory.
        cwd = os.path.abspath(".")
        self.assertFalse(
            any(p.startswith(cwd + os.sep) for p in seen_dirs),
            f"'.' should have been skipped but was scanned: {seen_dirs}",
        )

    def test_skip_cwd_false_includes_cwd(self):
        """When skip_cwd=False '.' is walked and resolved to an absolute
        path."""
        with self._run_with_prefs(
            RECIPE_SEARCH_DIRS=["."],
            RECIPE_OVERRIDE_DIRS=[self.overrides_dir],
        ):
            with patch.object(
                autopkglib, "map_key_to_paths", return_value={}
            ) as mk_mock:
                autopkglib.calculate_recipe_map(skip_cwd=False)

        # Every call's repo_dir arg should be absolute (no bare '.').
        called_dirs = [call_args.args[1] for call_args in mk_mock.call_args_list]
        self.assertFalse(
            any(d == "." for d in called_dirs),
            f"'.' should have been resolved to abspath: {called_dirs}",
        )


class TestReadRecipeMapAutoCreate(_RecipeMapIsolationMixin, unittest.TestCase):
    """The dev-2.x port diverges from dev-3.x here: a missing/invalid map
    MUST auto-rebuild rather than exit the process."""

    def test_auto_creates_when_file_missing(self):
        """Normal call with no map on disk should trigger a rebuild, not
        exit the interpreter."""
        self.assertFalse(os.path.exists(autopkglib.DEFAULT_RECIPE_MAP))
        with (
            patch.object(autopkglib, "calculate_recipe_map") as mock_calc,
            patch.object(autopkglib, "sys") as mock_sys,
        ):
            autopkglib.read_recipe_map()
            mock_calc.assert_called_once()
            # Must NOT have exited.
            mock_sys.exit.assert_not_called()

    def test_auto_creates_when_file_is_invalid(self):
        """A map file missing required keys is treated the same as missing."""
        with open(autopkglib.DEFAULT_RECIPE_MAP, "w") as f:
            json.dump({"identifiers": {}}, f)  # missing required keys
        with (
            patch.object(autopkglib, "calculate_recipe_map") as mock_calc,
            patch.object(autopkglib, "sys") as mock_sys,
        ):
            autopkglib.read_recipe_map()
            mock_calc.assert_called_once()
            mock_sys.exit.assert_not_called()

    def test_loads_valid_map_without_rebuild(self):
        valid = {
            "identifiers": {"com.example.a": "/a.recipe"},
            "shortnames": {"A": "/a.recipe"},
            "overrides": {},
            "overrides-identifiers": {},
        }
        with open(autopkglib.DEFAULT_RECIPE_MAP, "w") as f:
            json.dump(valid, f)
        with patch.object(autopkglib, "calculate_recipe_map") as mock_calc:
            autopkglib.read_recipe_map()
            mock_calc.assert_not_called()
        self.assertEqual(
            autopkglib.globalRecipeMap["identifiers"], valid["identifiers"]
        )

    def test_rebuild_true_is_still_accepted(self):
        """The dev-3.x flag must remain supported for API compatibility."""
        with patch.object(autopkglib, "calculate_recipe_map") as mock_calc:
            autopkglib.read_recipe_map(rebuild=True)
            mock_calc.assert_called_once()

    def test_allow_continuing_is_still_accepted(self):
        """Likewise for allow_continuing — retained as a no-op."""
        with patch.object(autopkglib, "calculate_recipe_map") as mock_calc:
            autopkglib.read_recipe_map(allow_continuing=True)
            mock_calc.assert_called_once()


class TestGenerateRecipeMapVerb(_RecipeMapIsolationMixin, unittest.TestCase):
    """The new ``autopkg generate-recipe-map`` subcommand."""

    def setUp(self):
        super().setUp()
        self.recipes_dir = os.path.join(self.tmpdir, "repo")
        self.overrides_dir = os.path.join(self.tmpdir, "ovrs")
        os.makedirs(self.recipes_dir)
        os.makedirs(self.overrides_dir)
        _write_plist_recipe(
            os.path.join(self.recipes_dir, "Sample.recipe"), SAMPLE_RECIPE
        )
        _write_plist_recipe(
            os.path.join(self.overrides_dir, "Override.recipe"), SAMPLE_OVERRIDE
        )

    def _run(self, argv_tail, options_kwargs=None, prefs=None):
        """Helper that drives the verb through its argparse-mocked harness.

        Fully controls ``get_pref`` AND ``get_override_dirs`` because the
        latter falls back to DEFAULT_USER_OVERRIDES_DIR (the real user's
        ~/Library/AutoPkg/RecipeOverrides) when the pref is empty."""
        from unittest.mock import Mock

        options = Mock()
        options.search_dirs = (options_kwargs or {}).get("search_dirs")
        options.override_dirs = (options_kwargs or {}).get("override_dirs")
        options.include_cwd = (options_kwargs or {}).get("include_cwd", False)

        argv = [None, "generate-recipe-map", *argv_tail]
        prefs = prefs or {}
        overrides_fallback = prefs.get("RECIPE_OVERRIDE_DIRS") or []

        with (
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.common_parse", return_value=(options, [])),
            patch("autopkg.add_search_and_override_dir_options"),
            patch.object(autopkglib, "get_pref", side_effect=lambda k: prefs.get(k)),
            patch.object(
                autopkglib, "get_override_dirs", return_value=overrides_fallback
            ),
        ):
            mock_parser.return_value = Mock()
            return autopkg.generate_recipe_map(argv)

    def test_registered_in_subcommands(self):
        """The verb should show up in the main() dispatch dict."""
        # We call main with an unknown-but-fallthrough-to-help path to
        # collect the subcommand table via the display_help function.
        captured = []

        def fake_display_help(argv, subcommands):
            captured.append(subcommands)
            return 1

        with patch("autopkg.display_help", side_effect=fake_display_help):
            autopkg.main([None, "help"])

        self.assertTrue(captured, "main() did not call display_help")
        self.assertIn("generate-recipe-map", captured[0])
        self.assertIn("function", captured[0]["generate-recipe-map"])
        self.assertIs(
            captured[0]["generate-recipe-map"]["function"],
            autopkg.generate_recipe_map,
        )

    def test_generates_and_persists_map(self):
        """Invoking the verb with explicit search/override dirs must
        produce a persisted recipe map covering those dirs."""
        rc = self._run(
            [],
            options_kwargs={
                "search_dirs": [self.recipes_dir],
                "override_dirs": [self.overrides_dir],
            },
            # No background prefs — test only the CLI-supplied dirs.
            prefs={"RECIPE_SEARCH_DIRS": [], "RECIPE_OVERRIDE_DIRS": []},
        )
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(autopkglib.DEFAULT_RECIPE_MAP))

        with open(autopkglib.DEFAULT_RECIPE_MAP) as f:
            on_disk = json.load(f)
        self.assertEqual(
            set(on_disk.keys()),
            {
                "identifiers",
                "shortnames",
                "overrides",
                "overrides-identifiers",
                "schema_version",
            },
        )
        self.assertEqual(
            on_disk["schema_version"],
            autopkglib.RECIPE_MAP_SCHEMA_VERSION,
        )
        self.assertIn(SAMPLE_RECIPE["Identifier"], on_disk["identifiers"])
        self.assertIn(SAMPLE_OVERRIDE["Identifier"], on_disk["overrides-identifiers"])

    def test_generates_without_extras_uses_prefs(self):
        """No CLI dirs => use the configured prefs. Should still persist."""
        rc = self._run(
            [],
            prefs={
                "RECIPE_SEARCH_DIRS": [self.recipes_dir],
                "RECIPE_OVERRIDE_DIRS": [self.overrides_dir],
            },
        )
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(autopkglib.DEFAULT_RECIPE_MAP))
        with open(autopkglib.DEFAULT_RECIPE_MAP) as f:
            on_disk = json.load(f)
        self.assertIn(SAMPLE_RECIPE["Identifier"], on_disk["identifiers"])


class TestAutopkgUserFolder(unittest.TestCase):
    """autopkg_user_folder must be defensive against permission errors so
    it doesn't break tests that mock os.path.expanduser."""

    def test_returns_expanded_path(self):
        with tempfile.TemporaryDirectory() as td:
            with patch("os.path.expanduser", return_value=td):
                result = autopkglib.autopkg_user_folder()
            self.assertEqual(os.path.abspath(result), os.path.abspath(td))

    def test_tolerates_read_only_filesystem(self):
        with patch("os.makedirs", side_effect=OSError("read-only")):
            # Must not raise.
            result = autopkglib.autopkg_user_folder()
            self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
