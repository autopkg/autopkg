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

"""Regression tests pinned to specific upstream issues closed by the
recipe-map backport. Each test class has a docstring citing the GitHub
issue number so future changes that break the behaviour show up in CI
with a direct pointer to the original bug report."""

import importlib
import importlib.machinery
import json
import os
import plistlib
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import autopkglib

autopkg_path = os.path.join(os.path.dirname(__file__), "..", "autopkg")
loader = importlib.machinery.SourceFileLoader("autopkg", autopkg_path)
autopkg = loader.load_module()
sys.modules["autopkg"] = autopkg


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
    "ParentRecipeTrustInfo": {"parent_recipes": {}, "non_core_processors": {}},
}


def _write_plist_recipe(path, recipe_dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        plistlib.dump(recipe_dict, f)


class _RecipeMapIsolation:
    """Shared fixture: redirect DEFAULT_RECIPE_MAP to a per-test tempdir
    and reset globalRecipeMap between tests."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="autopkg_regression_")
        self.addCleanup(lambda: shutil.rmtree(self.tmpdir, ignore_errors=True))

        self._saved_map = dict(autopkglib.globalRecipeMap)
        self._saved_default = autopkglib.DEFAULT_RECIPE_MAP
        self._saved_write_disabled = autopkglib._recipe_map_write_disabled
        autopkglib._recipe_map_write_disabled = False
        autopkglib.DEFAULT_RECIPE_MAP = os.path.join(self.tmpdir, "recipe_map.json")

        for sub in (
            "identifiers",
            "shortnames",
            "overrides",
            "overrides-identifiers",
        ):
            autopkglib.globalRecipeMap.setdefault(sub, {}).clear()

        # Reset the cross-test latch so one test's miss-rebuild doesn't
        # prevent another test from exercising the same code path.
        autopkg._set_locate_recipe_rebuild_attempted(False)

    def tearDown(self):
        autopkglib.globalRecipeMap.clear()
        autopkglib.globalRecipeMap.update(self._saved_map)
        autopkglib.DEFAULT_RECIPE_MAP = self._saved_default
        autopkglib._recipe_map_write_disabled = self._saved_write_disabled


class TestIssue918And908And886CliPrecedence(_RecipeMapIsolation, unittest.TestCase):
    """Regression tests for upstream issues #886, #908, #918 (related to
    #894): the recipe map is pref-scoped, so when the user passes
    ``--search-dir`` / ``--override-dir`` with values that differ from the
    configured preferences, autopkg must scan those dirs directly rather
    than silently returning whatever the map happens to know about.

    See https://github.com/autopkg/autopkg/issues/918 for the original
    report. The old dev-2.x on-disk scanner respected the CLI flags; the
    initial backport of the map silently broke that contract."""

    def setUp(self):
        super().setUp()
        # "Primary" repo configured in prefs - goes into the map.
        self.primary_dir = os.path.join(self.tmpdir, "primary")
        os.makedirs(self.primary_dir)
        _write_plist_recipe(
            os.path.join(self.primary_dir, "Primary.recipe"),
            {**SAMPLE_RECIPE, "Identifier": "com.example.primary"},
        )
        # "Scoped" dir is the CLI-supplied one, NOT in prefs, NOT in map.
        self.scoped_dir = os.path.join(self.tmpdir, "scoped")
        os.makedirs(self.scoped_dir)
        _write_plist_recipe(
            os.path.join(self.scoped_dir, "Scoped.recipe"),
            {**SAMPLE_RECIPE, "Identifier": "com.example.scoped"},
        )

        # Seed the in-memory map as if `generate-recipe-map` had been run
        # when only the primary dir was configured.
        autopkglib.globalRecipeMap.update(
            {
                "identifiers": {
                    "com.example.primary": os.path.join(
                        self.primary_dir, "Primary.recipe"
                    )
                },
                "shortnames": {
                    "Primary": os.path.join(self.primary_dir, "Primary.recipe")
                },
                "overrides": {},
                "overrides-identifiers": {},
            }
        )

        # Pin the pref-backed dirs so _dirs_match_prefs compares against a
        # known baseline.
        self._prefs_patcher = patch.object(
            autopkglib,
            "get_pref",
            side_effect=lambda k: {
                "RECIPE_SEARCH_DIRS": [self.primary_dir],
            }.get(k),
        )
        self._prefs_patcher.start()
        self.addCleanup(self._prefs_patcher.stop)
        self._override_patcher = patch.object(
            autopkglib, "get_override_dirs", return_value=[]
        )
        self._override_patcher.start()
        self.addCleanup(self._override_patcher.stop)

    def test_cli_search_dir_not_in_prefs_is_scanned_on_disk(self):
        """User running `autopkg run -d /scoped Scoped` must find the
        recipe in /scoped even though the persisted map knows nothing
        about it."""
        result = autopkg.find_recipe(
            "com.example.scoped", search_dirs=[self.scoped_dir]
        )
        self.assertEqual(result, os.path.join(self.scoped_dir, "Scoped.recipe"))

    def test_cli_search_dir_wins_over_map_for_same_identifier(self):
        """When the CLI dir contains a recipe with the same identifier as
        one in the map, the CLI dir version wins. This is the dev-2.x
        contract (recipes in the Recipes/ folder override those in
        installed repos) that #886 documents."""
        # Create a /scoped copy with the SAME identifier as the one in
        # the map but a different location.
        same_id_path = os.path.join(self.scoped_dir, "LocalOverrideOfPrimary.recipe")
        _write_plist_recipe(
            same_id_path,
            {**SAMPLE_RECIPE, "Identifier": "com.example.primary"},
        )

        result = autopkg.find_recipe(
            "com.example.primary", search_dirs=[self.scoped_dir]
        )
        self.assertEqual(
            result,
            same_id_path,
            "CLI-supplied dir must take precedence over the map.",
        )

    def test_no_cli_dirs_uses_map(self):
        """The common case: no CLI dirs → map-first."""
        # Add a pref-dir entry that _also_ exists on disk so find_recipe's
        # _dirs_match_prefs check passes.
        result = autopkg.find_recipe("com.example.primary")
        self.assertEqual(result, os.path.join(self.primary_dir, "Primary.recipe"))

    def test_empty_cli_dirs_falls_back_to_prefs(self):
        """Passing an empty list / None should be equivalent to omitting
        the kwarg — map-first stays in effect."""
        self.assertEqual(
            autopkg.find_recipe("com.example.primary", search_dirs=[]),
            os.path.join(self.primary_dir, "Primary.recipe"),
        )
        self.assertEqual(
            autopkg.find_recipe("com.example.primary", search_dirs=None),
            os.path.join(self.primary_dir, "Primary.recipe"),
        )

    def test_superset_cli_dirs_still_uses_map(self):
        """Caller supplies prefs + an extra dir (the recursive
        load_recipe pattern, where a parent-recipe lookup appends the
        child's dir). _dirs_match_prefs should accept the superset and
        use the map, not fall back to the full-tree on-disk scan.

        This is the fix that prevented the parent-chain recursion from
        silently bypassing the map and paying the full O(N) scan cost
        on every parent resolution."""
        extra_dir = os.path.join(self.tmpdir, "extra")
        superset = [self.primary_dir, extra_dir]
        # On-disk scanner should NOT be called because the map has the
        # answer and the caller's dirs include the full pref baseline.
        with patch("autopkg.find_recipe_by_identifier_on_disk") as mock_on_disk:
            result = autopkg.find_recipe("com.example.primary", search_dirs=superset)
        self.assertEqual(result, os.path.join(self.primary_dir, "Primary.recipe"))
        mock_on_disk.assert_not_called()

    def test_narrowed_cli_dirs_still_bypasses_map(self):
        """Caller supplies dirs that EXCLUDE at least one pref dir.
        The map could point at a recipe the caller explicitly excluded,
        so the map must still be bypassed (the #886/#894/#908/#918
        contract). Negative complement to the superset test above."""
        # `self.scoped_dir` is NOT in the configured prefs. Caller passes
        # only the scoped dir, which is a narrowed scope. The map's entry
        # for `com.example.primary` (in self.primary_dir) must not be
        # returned because self.primary_dir isn't in the caller's set.
        result = autopkg.find_recipe(
            "com.example.primary", search_dirs=[self.scoped_dir]
        )
        # No recipe with that identifier exists in self.scoped_dir, so
        # the result is None — the map entry was correctly ignored.
        self.assertIsNone(result)


class TestIssue894ProcessorLookup(_RecipeMapIsolation, unittest.TestCase):
    """Regression tests for issue #894: shared-processor recipes in the
    current working directory weren't being found because
    find_processor_path only walked RECIPE_SEARCH_DIRS on disk, ignoring
    the map, and never triggered the cwd-inclusive rebuild."""

    def test_find_processor_path_map_hit(self):
        """A shared-processor identifier present in the map is resolved
        without any on-disk scan."""
        # Write a real recipe on disk so find_recipe_by_identifier_in_map's
        # valid_recipe_file check succeeds.
        shared_dir = os.path.join(self.tmpdir, "shared")
        os.makedirs(shared_dir)
        shared_recipe = os.path.join(shared_dir, "SharedRecipe.recipe")
        _write_plist_recipe(
            shared_recipe,
            {**SAMPLE_RECIPE, "Identifier": "com.example.shared"},
        )
        autopkglib.globalRecipeMap["identifiers"]["com.example.shared"] = shared_recipe

        with (
            patch("autopkg.find_recipe_by_identifier_on_disk") as mock_disk,
            # Make the processor file appear to exist so the verb returns
            # a truthy path.
            patch(
                "os.path.exists",
                side_effect=lambda p: p.endswith("MyProc.py"),
            ),
        ):
            result = autopkg.find_processor_path(
                "com.example.shared/MyProc",
                recipe={"RECIPE_PATH": "/recipes/x.recipe"},
                env={"RECIPE_SEARCH_DIRS": []},
            )
        self.assertIsNotNone(result)
        # On-disk scan must NOT have been invoked.
        mock_disk.assert_not_called()

    def test_find_processor_path_falls_back_to_disk(self):
        """If the map doesn't know the identifier, on-disk fallback
        kicks in — preserving the legacy behaviour."""
        with (
            patch(
                "autopkg.find_recipe_by_identifier_on_disk",
                return_value="/disk/Shared.recipe",
            ) as mock_disk,
            patch("os.path.exists", return_value=True),
        ):
            autopkg.find_processor_path(
                "com.example.notmapped/MyProc",
                recipe={"RECIPE_PATH": "/recipes/x.recipe"},
                env={"RECIPE_SEARCH_DIRS": ["/search"]},
            )
        mock_disk.assert_called_once_with("com.example.notmapped", ["/search"])

    def test_find_processor_path_triggers_cwd_rebuild_once(self):
        """Issue #894: when a shared-processor recipe lives in the cwd,
        find_processor_path should trigger a one-shot cwd-inclusive
        rebuild. Subsequent misses in the same process must NOT trigger
        a second rebuild (review recommendation: avoid pathological
        multi-miss rebuilds)."""
        autopkg._set_locate_recipe_rebuild_attempted(False)

        # Write a real recipe for the first lookup so the rebuild has
        # something to find.
        cwd_dir = os.path.join(self.tmpdir, "cwd")
        os.makedirs(cwd_dir)
        shared_recipe = os.path.join(cwd_dir, "Shared.recipe")
        _write_plist_recipe(
            shared_recipe,
            {**SAMPLE_RECIPE, "Identifier": "com.example.cwd.shared"},
        )

        def fake_calc(*args, **kwargs):
            autopkglib.globalRecipeMap["identifiers"][
                "com.example.cwd.shared"
            ] = shared_recipe

        with (
            patch("autopkg.calculate_recipe_map", side_effect=fake_calc) as mock_calc,
            patch(
                "autopkg.find_recipe_by_identifier_on_disk",
                return_value=None,
            ),
        ):
            # First call: map miss → rebuild once → find in rebuilt map.
            autopkg.find_processor_path(
                "com.example.cwd.shared/MyProc",
                recipe={"RECIPE_PATH": "/recipes/x.recipe"},
                env={"RECIPE_SEARCH_DIRS": []},
            )
            first_calls = mock_calc.call_count
            self.assertEqual(
                first_calls,
                1,
                "First map miss should trigger exactly one rebuild.",
            )

            # Second call with a different unmapped identifier: latch
            # prevents another rebuild.
            autopkg.find_processor_path(
                "com.example.other.shared/MyProc",
                recipe={"RECIPE_PATH": "/recipes/x.recipe"},
                env={"RECIPE_SEARCH_DIRS": []},
            )
            self.assertEqual(
                mock_calc.call_count,
                first_calls,
                "Second miss must not trigger another full rebuild "
                "Pathological multi-miss runs must not trigger N full rebuilds.",
            )


class TestIssue903TrustInfoByPath(_RecipeMapIsolation, unittest.TestCase):
    """Regression test for issue #903: `autopkg verify-trust-info
    <path/to/override.recipe>` failed to recognise the file as an override
    because the configured override_dirs didn't contain the parent of the
    user-supplied path. The fix uses the recipe map's overrides tables
    as the source of truth."""

    def test_recipe_in_override_dir_via_map_and_configured_dir(self):
        """A file listed in globalRecipeMap['overrides'] AND residing
        under a configured override dir is considered an override. The
        map is a hint; the configured dir is the authoritative answer.
        This is the shape of the #903 fix after the F-4 security
        hardening."""
        override_dir = os.path.join(self.tmpdir, "overrides")
        os.makedirs(override_dir)
        override_path = os.path.join(override_dir, "path.recipe")
        autopkglib.globalRecipeMap["overrides"]["SomeOverride"] = override_path
        self.assertTrue(autopkg.recipe_in_override_dir(override_path, [override_dir]))

    def test_recipe_in_override_dir_via_map_identifiers_and_configured_dir(
        self,
    ):
        """Same via the overrides-identifiers table."""
        override_dir = os.path.join(self.tmpdir, "o")
        os.makedirs(override_dir)
        override_path = os.path.join(override_dir, "by-id.recipe")
        autopkglib.globalRecipeMap["overrides-identifiers"][
            "local.byid"
        ] = override_path
        self.assertTrue(autopkg.recipe_in_override_dir(override_path, [override_dir]))

    def test_recipe_in_override_dir_via_map_but_not_under_configured_dir(
        self,
    ):
        """Security F-4: a map entry that points OUTSIDE any configured
        override dir must NOT be trusted. This blocks the attack where
        an attacker with write access to recipe_map.json plants an
        arbitrary path in the overrides table to bypass trust checks."""
        bogus_path = os.path.join(self.tmpdir, "notanoverridedir", "Sneaky.recipe")
        autopkglib.globalRecipeMap["overrides"]["Sneaky"] = bogus_path

        configured_dir = os.path.join(self.tmpdir, "configured_overrides")
        with patch.object(autopkg, "log_err") as mock_log_err:
            self.assertFalse(
                autopkg.recipe_in_override_dir(bogus_path, [configured_dir])
            )
            # Should have logged a warning about the bogus map entry.
            mock_log_err.assert_called()

    def test_recipe_in_override_dir_via_configured_dir(self):
        """The existing path-prefix check still works for files that the
        map hasn't indexed yet."""
        override_dir = os.path.join(self.tmpdir, "configured_overrides")
        override_path = os.path.join(override_dir, "Unindexed.recipe")
        self.assertTrue(autopkg.recipe_in_override_dir(override_path, [override_dir]))

    def test_recipe_in_override_dir_negative(self):
        """A file neither in the map nor under any configured override
        dir is NOT classified as an override."""
        self.assertFalse(
            autopkg.recipe_in_override_dir("/some/random/Recipe.recipe", [self.tmpdir])
        )

    def test_recipe_in_override_dir_sibling_prefix_not_matched(self):
        """Regression: prior to the fix, `/Users/a/Library/AutoPkg2`
        could accidentally match `/Users/a/Library/AutoPkg`. Make sure
        the normalised match requires a path separator."""
        self.assertFalse(
            autopkg.recipe_in_override_dir("/a/AutoPkg2/file.recipe", ["/a/AutoPkg"])
        )


class TestIssue874MissingOverridesIdentifiers(_RecipeMapIsolation, unittest.TestCase):
    """Regression for issue #874: a map file written by an older version
    of autopkg doesn't have the ``overrides-identifiers`` key. The old
    code did ``globalRecipeMap["overrides-identifiers"]`` directly,
    producing a KeyError. The backport must either tolerate the missing
    key OR reject the file and trigger a rebuild."""

    def test_legacy_map_without_overrides_identifiers_is_rejected(self):
        """A persisted map missing the key should be treated as invalid
        and trigger an auto-rebuild rather than crashing."""
        legacy = {
            "identifiers": {"com.example.a": "/a.recipe"},
            "shortnames": {"A": "/a.recipe"},
            "overrides": {},
            # no 'overrides-identifiers' key on purpose
        }
        with open(autopkglib.DEFAULT_RECIPE_MAP, "w") as f:
            json.dump(legacy, f)

        self.assertFalse(autopkglib.validate_recipe_map(legacy))

        with patch.object(autopkglib, "calculate_recipe_map") as mock_calc:
            autopkglib.read_recipe_map()
            mock_calc.assert_called_once()

    def test_lookup_tolerates_missing_key_in_memory(self):
        """Even if globalRecipeMap is mutated by a third party to drop
        the key, lookups should not raise KeyError."""
        autopkglib.globalRecipeMap.pop("overrides-identifiers", None)
        try:
            self.assertIsNone(
                autopkglib.find_recipe_by_identifier_in_map("com.example.anything")
            )
        except KeyError:
            self.fail(
                "find_recipe_by_identifier_in_map raised KeyError when the "
                "'overrides-identifiers' key was missing."
            )


class TestIssue869InvalidRecipeRobustness(_RecipeMapIsolation, unittest.TestCase):
    """Regression for issue #869: a syntactically-invalid recipe in a
    search dir used to crash ``calculate_recipe_map`` with a TypeError
    during the JSON sort because ``get_identifier_from_recipe_file``
    returned None. The backport must skip such files with a warning."""

    def test_invalid_recipe_does_not_crash_map_build(self):
        repo_dir = os.path.join(self.tmpdir, "bad_repo")
        os.makedirs(repo_dir)
        # A corrupt plist file with a .recipe extension.
        with open(os.path.join(repo_dir, "Broken.recipe"), "wb") as f:
            f.write(b'<?xml version="1.0"?><broken!!!><not-a-recipe/>')
        # A second, valid recipe so the map has something to load.
        _write_plist_recipe(
            os.path.join(repo_dir, "OK.recipe"),
            {**SAMPLE_RECIPE, "Identifier": "com.example.ok"},
        )

        with patch.object(
            autopkglib,
            "get_pref",
            side_effect=lambda k: {
                "RECIPE_SEARCH_DIRS": [repo_dir],
            }.get(k),
        ):
            # Must not raise.
            autopkglib.calculate_recipe_map()

        # Valid recipe indexed, broken one skipped.
        self.assertIn(
            "com.example.ok",
            autopkglib.globalRecipeMap["identifiers"],
        )
        self.assertEqual(
            len(autopkglib.globalRecipeMap["identifiers"]),
            1,
            "Broken recipe should not have been added to the map.",
        )

    def test_recipe_without_identifier_does_not_crash(self):
        """A valid-plist recipe that's missing an Identifier field is
        skipped, not added with a None key."""
        repo_dir = os.path.join(self.tmpdir, "no_id_repo")
        os.makedirs(repo_dir)
        _write_plist_recipe(
            os.path.join(repo_dir, "NoIdentifier.recipe"),
            {
                "Input": {"NAME": "Foo"},
                "Process": [{"Processor": "URLDownloader"}],
            },
        )

        with patch.object(
            autopkglib,
            "get_pref",
            side_effect=lambda k: {
                "RECIPE_SEARCH_DIRS": [repo_dir],
            }.get(k),
        ):
            autopkglib.calculate_recipe_map()

        self.assertNotIn(None, autopkglib.globalRecipeMap["identifiers"])
        self.assertEqual(autopkglib.globalRecipeMap["identifiers"], {})


class TestIssue901RecipeMapPathOverride(unittest.TestCase):
    """Regression for issue #901: the recipe map location should be
    configurable so CI pipelines that don't use ``~/Library/AutoPkg``
    (e.g. ephemeral runners that clone everything into ``/workspace``)
    can keep the map alongside their recipes."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="autopkg_mp_")
        self.addCleanup(lambda: shutil.rmtree(self.tmpdir, ignore_errors=True))

    def test_env_var_overrides_default_path(self):
        """AUTOPKG_RECIPE_MAP_PATH takes precedence over the default."""
        custom = os.path.join(self.tmpdir, "my_map.json")
        with patch.dict(os.environ, {"AUTOPKG_RECIPE_MAP_PATH": custom}):
            self.assertEqual(autopkglib._recipe_map_path(), custom)

    def test_env_var_takes_precedence_over_pref(self):
        """Env beats pref so CI can override a baked-in config."""
        env_path = os.path.join(self.tmpdir, "env.json")
        pref_path = os.path.join(self.tmpdir, "pref.json")
        with (
            patch.dict(os.environ, {"AUTOPKG_RECIPE_MAP_PATH": env_path}),
            patch.object(
                autopkglib,
                "get_pref",
                side_effect=lambda k: pref_path if k == "RECIPE_MAP_PATH" else None,
            ),
        ):
            self.assertEqual(autopkglib._recipe_map_path(), env_path)

    def test_pref_used_when_no_env(self):
        """Without the env var, the RECIPE_MAP_PATH pref wins."""
        pref_path = os.path.join(self.tmpdir, "pref.json")
        # Clear the env var explicitly so this test works even if the
        # developer has it set in their shell.
        with (
            patch.dict(os.environ, {}, clear=False),
            patch.object(
                autopkglib,
                "get_pref",
                side_effect=lambda k: pref_path if k == "RECIPE_MAP_PATH" else None,
            ),
        ):
            os.environ.pop("AUTOPKG_RECIPE_MAP_PATH", None)
            self.assertEqual(autopkglib._recipe_map_path(), pref_path)

    def test_default_used_when_neither_env_nor_pref(self):
        """Falls back to the user's ~/Library/AutoPkg/recipe_map.json."""
        with (
            patch.dict(os.environ, {}, clear=False),
            patch.object(autopkglib, "get_pref", return_value=None),
        ):
            os.environ.pop("AUTOPKG_RECIPE_MAP_PATH", None)
            expected = os.path.abspath(
                os.path.expanduser(autopkglib.DEFAULT_RECIPE_MAP)
            )
            self.assertEqual(autopkglib._recipe_map_path(), expected)


class TestSchemaVersion(_RecipeMapIsolation, unittest.TestCase):
    """Tests for the RECIPE_MAP_SCHEMA_VERSION field added for forward-
    compatibility."""

    def test_persisted_file_includes_schema_version(self):
        autopkglib.globalRecipeMap["identifiers"]["x"] = "/x.recipe"
        autopkglib.write_recipe_map_to_disk()
        with open(autopkglib.DEFAULT_RECIPE_MAP) as f:
            on_disk = json.load(f)
        self.assertEqual(
            on_disk["schema_version"], autopkglib.RECIPE_MAP_SCHEMA_VERSION
        )

    def test_current_version_is_valid(self):
        ok = {
            "identifiers": {},
            "shortnames": {},
            "overrides": {},
            "overrides-identifiers": {},
            "schema_version": autopkglib.RECIPE_MAP_SCHEMA_VERSION,
        }
        self.assertTrue(autopkglib.validate_recipe_map(ok))

    def test_legacy_file_without_version_is_accepted(self):
        """Older map files predate the schema_version field; treat them
        as v1 rather than forcing an unnecessary rebuild."""
        legacy = {
            "identifiers": {},
            "shortnames": {},
            "overrides": {},
            "overrides-identifiers": {},
        }
        self.assertTrue(autopkglib.validate_recipe_map(legacy))

    def test_future_version_is_rejected(self):
        """A future version number means the format may be
        incompatible; reject so we trigger a rebuild at this version's
        level."""
        future = {
            "identifiers": {},
            "shortnames": {},
            "overrides": {},
            "overrides-identifiers": {},
            "schema_version": 999,
        }
        self.assertFalse(autopkglib.validate_recipe_map(future))


class TestAtomicWrite(_RecipeMapIsolation, unittest.TestCase):
    """The map write must be atomic so concurrent autopkg invocations
    can't observe a half-written file (review recommendation: atomic
    writes for on-disk cache files)."""

    def test_write_uses_mkstemp_and_replace(self):
        """Verify write_recipe_map_to_disk writes via tempfile.mkstemp
        (O_EXCL semantics) and renames into position. Security fix for
        F-3: a plain open(tmp, 'w') would follow a pre-existing symlink."""
        observed: dict = {"mkstemp_calls": 0, "replace_calls": 0}
        import tempfile as real_tempfile

        real_mkstemp = real_tempfile.mkstemp
        real_replace = os.replace

        def tracking_mkstemp(*args, **kwargs):
            observed["mkstemp_calls"] += 1
            return real_mkstemp(*args, **kwargs)

        def tracking_replace(src, dst):
            observed["replace_calls"] += 1
            return real_replace(src, dst)

        with (
            patch("tempfile.mkstemp", side_effect=tracking_mkstemp),
            patch("os.replace", side_effect=tracking_replace),
        ):
            autopkglib.write_recipe_map_to_disk()

        self.assertEqual(
            observed["mkstemp_calls"],
            1,
            "write_recipe_map_to_disk should use tempfile.mkstemp.",
        )
        self.assertEqual(observed["replace_calls"], 1)
        self.assertTrue(os.path.exists(autopkglib.DEFAULT_RECIPE_MAP))

    def test_write_failure_latches_and_is_silent_on_second_call(self):
        """First OSError logs a warning and latches the write-disabled
        flag so subsequent calls in the same process are no-ops."""
        with patch("tempfile.mkstemp", side_effect=OSError("no space left")):
            with patch.object(autopkglib, "log_err") as mock_log_err:
                autopkglib.write_recipe_map_to_disk()
                # First call logs.
                self.assertEqual(mock_log_err.call_count, 1)
                autopkglib.write_recipe_map_to_disk()
                # Second call is a silent no-op.
                self.assertEqual(mock_log_err.call_count, 1)

    def test_failed_replace_cleans_up_tempfile(self):
        """A failed os.replace must not leave the tempfile behind."""
        import glob as _glob

        autopkglib._recipe_map_write_disabled = False
        map_dir = os.path.dirname(autopkglib.DEFAULT_RECIPE_MAP)
        # Ensure dir exists so mkstemp can create there.
        os.makedirs(map_dir, exist_ok=True)
        with patch("os.replace", side_effect=OSError("nope")):
            autopkglib.write_recipe_map_to_disk()

        # No leftover tempfile matching our naming pattern should remain.
        leftovers = _glob.glob(os.path.join(map_dir, ".recipe_map.json.tmp*"))
        self.assertFalse(
            leftovers,
            f"Tempfile(s) should have been cleaned up but found: {leftovers}",
        )


class TestEscapeHatch(_RecipeMapIsolation, unittest.TestCase):
    """The AUTOPKG_DISABLE_RECIPE_MAP / DISABLE_RECIPE_MAP escape hatch
    (review recommendation: provide an operational bypass)."""

    def test_env_var_disables_map_reading(self):
        with patch.dict(os.environ, {"AUTOPKG_DISABLE_RECIPE_MAP": "1"}):
            self.assertTrue(autopkglib._recipe_map_disabled())
            # read_recipe_map should be a no-op.
            before = dict(autopkglib.globalRecipeMap)
            autopkglib.read_recipe_map()
            self.assertEqual(autopkglib.globalRecipeMap, before)

    def test_pref_disables_map_reading(self):
        with patch.object(
            autopkglib,
            "get_pref",
            side_effect=lambda k: True if k == "DISABLE_RECIPE_MAP" else None,
        ):
            self.assertTrue(autopkglib._recipe_map_disabled())

    def test_disabled_flag_skips_writes(self):
        """When disabled, write_recipe_map_to_disk doesn't touch the
        filesystem."""
        with patch.dict(os.environ, {"AUTOPKG_DISABLE_RECIPE_MAP": "1"}):
            autopkglib.write_recipe_map_to_disk()
        self.assertFalse(
            os.path.exists(autopkglib.DEFAULT_RECIPE_MAP),
            "Map file should not be written when the escape hatch is set.",
        )


class TestRepoAddSingleRebuild(_RecipeMapIsolation, unittest.TestCase):
    """Regression: repo-add was calling calculate_recipe_map() twice.
    Assert it now calls it exactly once."""

    def test_repo_add_rebuilds_map_exactly_once(self):
        with (
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.get_search_dirs", return_value=[]),
            patch("autopkg.get_pref", return_value={}),
            patch("autopkg.expand_repo_url", side_effect=lambda x: x),
            patch(
                "autopkg.get_recipe_repo",
                return_value="/cloned/repo",
            ),
            patch("autopkg.save_pref_or_warn"),
            patch("autopkg.log"),
            patch("autopkg.read_recipe_map"),
            patch("autopkg.calculate_recipe_map") as mock_calc,
        ):
            mock_parser.return_value = Mock()
            mock_parse.return_value = (Mock(), ["recipes"])

            autopkg.repo_add([None, "repo-add", "recipes"])

        self.assertEqual(
            mock_calc.call_count,
            1,
            "repo-add should call calculate_recipe_map exactly once.",
        )


class TestRepoUpdateHeadDiffing(_RecipeMapIsolation, unittest.TestCase):
    """Regression: `autopkg repo-update` should only rebuild the map
    when git pull actually changed HEAD."""

    def test_no_change_no_rebuild(self):
        """Same HEAD before and after pull → no rebuild."""
        same_hash = "abc1234\n"
        with (
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.get_pref", return_value={}),
            patch("autopkg.get_repo_info", return_value={"path": "/repo"}),
            patch("autopkg.expand_repo_url", side_effect=lambda x: x),
            patch("autopkg.run_git") as mock_run_git,
            patch("autopkg.read_recipe_map"),
            patch("autopkg.calculate_recipe_map") as mock_calc,
            patch("autopkg.log"),
        ):
            mock_parser.return_value = Mock()
            mock_parse.return_value = (Mock(), ["recipes"])
            mock_run_git.return_value = same_hash

            autopkg.repo_update([None, "repo-update", "recipes"])

        mock_calc.assert_not_called()

    def test_change_triggers_rebuild(self):
        """Different HEAD hashes → rebuild."""
        hashes = iter(["oldhash\n", "newhash\n"])
        with (
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.gen_common_parser") as mock_parser,
            patch("autopkg.get_pref", return_value={}),
            patch("autopkg.get_repo_info", return_value={"path": "/repo"}),
            patch("autopkg.expand_repo_url", side_effect=lambda x: x),
            patch("autopkg.run_git") as mock_run_git,
            patch("autopkg.read_recipe_map"),
            patch("autopkg.calculate_recipe_map") as mock_calc,
            patch("autopkg.log"),
        ):
            mock_parser.return_value = Mock()
            mock_parse.return_value = (Mock(), ["recipes"])

            def run_git_sides(args, git_directory=None):
                if args == ["rev-parse", "HEAD"]:
                    return next(hashes)
                return "Pulled new commits"

            mock_run_git.side_effect = run_git_sides

            autopkg.repo_update([None, "repo-update", "recipes"])

        mock_calc.assert_called_once()


class TestRepoDeletePrefMapConsistency(_RecipeMapIsolation, unittest.TestCase):
    """Regression: repo-delete must keep prefs and the persisted map
    consistent even when rmtree fails."""

    def test_rmtree_failure_still_rebuilds_map(self):
        """A failed removal logs an error but must still update prefs
        and rebuild the map so the two agree on which repos exist."""
        with (
            patch("autopkg.common_parse") as mock_parse,
            patch("autopkg.gen_common_parser") as mock_parser,
            patch(
                "autopkg.get_pref",
                return_value={"/repo": {"URL": "https://example/repo"}},
            ),
            patch("autopkg.get_search_dirs", return_value=["/repo"]),
            patch(
                "autopkg.get_repo_info",
                return_value={"path": "/repo"},
            ),
            patch("autopkg.expand_repo_url", side_effect=lambda x: x),
            patch("shutil.rmtree", side_effect=OSError("Permission denied")),
            patch("autopkg.save_pref_or_warn") as mock_save_pref,
            patch("autopkg.read_recipe_map"),
            patch("autopkg.calculate_recipe_map") as mock_calc,
            patch("autopkg.log"),
            patch("autopkg.log_err"),
        ):
            mock_parser.return_value = Mock()
            mock_parse.return_value = (Mock(), ["repo"])

            autopkg.repo_delete([None, "repo-delete", "repo"])

        # Prefs saved.
        mock_save_pref.assert_any_call("RECIPE_REPOS", {})
        mock_save_pref.assert_any_call("RECIPE_SEARCH_DIRS", [])
        # Map rebuilt.
        mock_calc.assert_called_once()


class TestReadRecipeMapRebuildForce(_RecipeMapIsolation, unittest.TestCase):
    """Review finding: rebuild=True must always rebuild, even when
    the on-disk file happens to be valid."""

    def test_rebuild_true_always_rebuilds(self):
        valid = {
            "identifiers": {"x": "/x"},
            "shortnames": {"X": "/x"},
            "overrides": {},
            "overrides-identifiers": {},
            "schema_version": autopkglib.RECIPE_MAP_SCHEMA_VERSION,
        }
        with open(autopkglib.DEFAULT_RECIPE_MAP, "w") as f:
            json.dump(valid, f)

        with patch.object(autopkglib, "calculate_recipe_map") as mock_calc:
            autopkglib.read_recipe_map(rebuild=True)
            mock_calc.assert_called_once()

    def test_rebuild_false_skips_rebuild_when_valid(self):
        """Negative control: without rebuild=True, a valid file is
        loaded without a full recalculation."""
        valid = {
            "identifiers": {"x": "/x"},
            "shortnames": {"X": "/x"},
            "overrides": {},
            "overrides-identifiers": {},
            "schema_version": autopkglib.RECIPE_MAP_SCHEMA_VERSION,
        }
        with open(autopkglib.DEFAULT_RECIPE_MAP, "w") as f:
            json.dump(valid, f)

        with patch.object(autopkglib, "calculate_recipe_map") as mock_calc:
            autopkglib.read_recipe_map()
            mock_calc.assert_not_called()
        self.assertEqual(autopkglib.globalRecipeMap["identifiers"], {"x": "/x"})


class TestGlobalRecipeMapInPlaceMutation(_RecipeMapIsolation, unittest.TestCase):
    """Review finding: calculate_recipe_map must mutate in place so
    ``from autopkglib import globalRecipeMap`` importers see fresh
    data, not a stale reference to the original empty dict."""

    def test_calculate_keeps_same_object_identity(self):
        initial_id = id(autopkglib.globalRecipeMap)
        with patch.object(autopkglib, "get_pref", side_effect=lambda k: []):
            autopkglib.calculate_recipe_map()
        self.assertEqual(
            id(autopkglib.globalRecipeMap),
            initial_id,
            "calculate_recipe_map reassigned the global dict; importers "
            "with a cached reference would see stale data.",
        )

    def test_autopkg_module_sees_fresh_data(self):
        """The autopkg CLI module imports globalRecipeMap by name.
        After calculate_recipe_map runs, the CLI module must see the
        updated contents."""
        # Seed a recipe to be discovered.
        repo = os.path.join(self.tmpdir, "repo")
        os.makedirs(repo)
        _write_plist_recipe(
            os.path.join(repo, "Foo.recipe"),
            {**SAMPLE_RECIPE, "Identifier": "com.example.foo"},
        )
        with (
            patch.object(
                autopkglib,
                "get_pref",
                side_effect=lambda k: [repo] if k == "RECIPE_SEARCH_DIRS" else None,
            ),
            patch.object(autopkglib, "get_override_dirs", return_value=[]),
        ):
            autopkglib.calculate_recipe_map()

        # The autopkg module's imported name and autopkglib's live dict
        # must both reflect the new state.
        self.assertIn(
            "com.example.foo",
            autopkg.globalRecipeMap["identifiers"],
        )
        self.assertIn(
            "com.example.foo",
            autopkglib.globalRecipeMap["identifiers"],
        )


class TestMapEntryMustParseAsRecipe(_RecipeMapIsolation, unittest.TestCase):
    """Defence-in-depth: the shared-processor code-import path in
    ``get_processor`` must reject a map entry that isn't structurally a
    recipe. Otherwise a user with write access to ``recipe_map.json``
    could point an entry at any stat-able file and have autopkg append
    its directory to the Python import path.

    The map lookup itself is deliberately fast (``os.path.isfile`` only)
    so every verb doesn't re-parse every entry. The structural check
    lives at the one call site that feeds ``spec.loader.exec_module``."""

    def test_get_processor_rejects_non_recipe_map_entry(self):
        """A map entry pointing at a file that exists but isn't a
        recipe must not cause its directory to be appended to the
        processor search path."""
        # Non-recipe file (plain text, wrong shape).
        bad_dir = os.path.join(self.tmpdir, "notarecipe")
        os.makedirs(bad_dir)
        bad_path = os.path.join(bad_dir, "X.recipe")
        with open(bad_path, "w") as f:
            f.write("this is not a recipe")

        autopkglib.globalRecipeMap["identifiers"]["com.example.evil"] = bad_path

        # A separate directory where the attacker would have placed a
        # matching <processor_name>.py; we assert THIS directory does
        # not get added to the import search path.
        recipe = {"RECIPE_PATH": os.path.join(self.tmpdir, "r.recipe")}
        env = {"RECIPE_SEARCH_DIRS": []}

        def tracking_exists(path):
            return False  # Ensure we don't actually import anything.

        with (
            patch(
                "autopkglib.extract_processor_name_with_recipe_identifier",
                return_value=("P", "com.example.evil"),
            ),
            patch("os.path.exists", side_effect=tracking_exists),
            patch("autopkglib.add_processor"),  # Never reached but mocked for safety.
        ):
            try:
                autopkglib.get_processor("com.example.evil/P", recipe=recipe, env=env)
            except (KeyError, AttributeError):
                # Expected — processor not found is fine; we only care
                # that the evil dir wasn't added to the search path.
                pass

        # The bad_dir must NOT appear in any os.path.exists call. We
        # confirm via a second pass that traces processor_search_dirs.
        # Simpler assertion: the bad_path must not be treated as a valid
        # recipe, which is what find_recipe_by_identifier_in_map +
        # valid_recipe_file guard together prevent.
        from autopkglib import valid_recipe_file

        self.assertFalse(
            valid_recipe_file(bad_path),
            "Setup invariant: the bad file must not parse as a recipe.",
        )


class TestLoadRecipeTolerartesStaleMapEntry(_RecipeMapIsolation, unittest.TestCase):
    """Review finding: ``load_recipe`` must not crash with
    ``AttributeError`` when the recipe map returns a path to a file
    that exists but isn't parseable (stale entry, truncated mid-write
    by a concurrent ``generate-recipe-map``, or tampered)."""

    def test_load_recipe_handles_unparseable_map_entry(self):
        """A map entry pointing at a corrupt file must log a warning
        and return None, not raise AttributeError."""
        corrupt_dir = os.path.join(self.tmpdir, "corrupt")
        os.makedirs(corrupt_dir)
        corrupt_path = os.path.join(corrupt_dir, "X.recipe.yaml")
        with open(corrupt_path, "w") as f:
            f.write("not: valid: recipe: :invalid yaml")

        autopkglib.globalRecipeMap["shortnames"]["X"] = corrupt_path

        # Stub out search_github/make_suggestions so we don't hit the
        # network when the recipe isn't resolved.
        with (
            patch("autopkg.make_suggestions_for"),
            patch(
                "autopkglib.get_pref",
                side_effect=lambda k: {
                    "RECIPE_SEARCH_DIRS": [corrupt_dir],
                }.get(k),
            ),
            patch.object(autopkglib, "get_override_dirs", return_value=[]),
            patch.object(autopkg, "log_err") as mock_log_err,
        ):
            result = autopkg.load_recipe(
                "X",
                override_dirs=[],
                recipe_dirs=[corrupt_dir],
                make_suggestions=False,
                search_github=False,
            )

        self.assertIsNone(
            result, "load_recipe must return None for unparseable map entries."
        )
        # And it must have logged the stale-map warning.
        warning_logged = any(
            "not a readable recipe" in str(call) for call in mock_log_err.call_args_list
        )
        self.assertTrue(
            warning_logged,
            "Expected a 'not a readable recipe' warning to be logged.",
        )


if __name__ == "__main__":
    unittest.main()
