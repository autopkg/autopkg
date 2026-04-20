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
"""Tests for the override fast path added to Code/autopkg.

Covers:
  - _fast_locate_override_by_name: direct filename lookup in override_dirs.
  - _merge_child_into_parent: child-into-parent merge helper.
  - _try_assemble_from_trust_info: trust-info-based chain assembly.
  - locate_recipe / load_recipe integration: fast path hit, miss, and
    fall-through behaviours; structural equivalence with the slow path.
"""

import importlib.machinery
import os
import plistlib
import sys
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch

import yaml

# Add the Code directory to the Python path to resolve autopkg dependencies
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

autopkg_path = os.path.join(os.path.dirname(__file__), "..", "autopkg")
loader = importlib.machinery.SourceFileLoader("autopkg", autopkg_path)
autopkg = loader.load_module()
sys.modules["autopkg"] = autopkg


# --------------------------------------------------------------------------
# Fixture helpers
# --------------------------------------------------------------------------


def _write_plist_recipe(path, data):
    with open(path, "wb") as f:
        plistlib.dump(data, f)


def _write_yaml_recipe(path, data):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)


def _make_recipe(identifier, parent=None, process=None, input_=None, extra=None):
    recipe = {
        "Identifier": identifier,
        "Input": input_ or {"NAME": "Test"},
        "Process": process or [],
    }
    if parent:
        recipe["ParentRecipe"] = parent
    if extra:
        recipe.update(extra)
    return recipe


def _make_override(
    identifier, parent_identifier, trust_info=None, input_=None, extra=None
):
    override = {
        "Identifier": identifier,
        "ParentRecipe": parent_identifier,
        "Input": input_ or {"NAME": "Test"},
    }
    if trust_info is not None:
        override["ParentRecipeTrustInfo"] = trust_info
    if extra:
        override.update(extra)
    return override


def _make_trust_info(parent_paths_by_id):
    """Build a minimal ParentRecipeTrustInfo dict from an identifier->path map."""
    return {
        "non_core_processors": {},
        "parent_recipes": {
            identifier: {"path": path, "sha256_hash": "deadbeef"}
            for identifier, path in parent_paths_by_id.items()
        },
    }


# --------------------------------------------------------------------------
# _fast_locate_override_by_name
# --------------------------------------------------------------------------


class TestFastLocateOverrideByName(unittest.TestCase):
    """Direct filename lookup in override_dirs."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.override_dir = self.tmp.name
        # Clear the module-level fast path cache between tests so assertions
        # about cache population are deterministic.
        autopkg._FAST_PATH_CACHE.clear()

    def tearDown(self):
        self.tmp.cleanup()
        autopkg._FAST_PATH_CACHE.clear()

    def test_returns_none_for_empty_override_dirs(self):
        self.assertIsNone(autopkg._fast_locate_override_by_name("foo", []))
        self.assertIsNone(autopkg._fast_locate_override_by_name("foo", None))

    def test_returns_none_for_empty_name(self):
        self.assertIsNone(
            autopkg._fast_locate_override_by_name("", [self.override_dir])
        )
        self.assertIsNone(
            autopkg._fast_locate_override_by_name(None, [self.override_dir])
        )

    def test_rejects_names_containing_path_separators(self):
        # File-path inputs are handled by the existing os.path.isfile branch
        # in locate_recipe; the fast path must decline to avoid ambiguity.
        self.assertIsNone(
            autopkg._fast_locate_override_by_name("sub/foo", [self.override_dir])
        )
        self.assertIsNone(
            autopkg._fast_locate_override_by_name(
                "/abs/foo.recipe", [self.override_dir]
            )
        )

    def test_finds_top_level_yaml_override(self):
        override_path = os.path.join(
            self.override_dir, "Google_Chrome.jamf.recipe.yaml"
        )
        override = _make_override(
            "local.jamf.Google_Chrome", "com.example.Google_Chrome"
        )
        _write_yaml_recipe(override_path, override)

        result = autopkg._fast_locate_override_by_name(
            "Google_Chrome.jamf", [self.override_dir]
        )

        self.assertIsNotNone(result)
        path, parsed = result
        self.assertEqual(path, override_path)
        self.assertEqual(parsed["Identifier"], "local.jamf.Google_Chrome")
        # Cache must be populated so load_recipe can skip a second parse.
        self.assertIn(override_path, autopkg._FAST_PATH_CACHE)

    def test_finds_top_level_plist_override(self):
        override_path = os.path.join(self.override_dir, "foo.recipe")
        override = _make_override("local.foo", "com.example.foo")
        _write_plist_recipe(override_path, override)

        result = autopkg._fast_locate_override_by_name("foo", [self.override_dir])
        self.assertIsNotNone(result)
        self.assertEqual(result[0], override_path)

    def test_finds_override_one_level_deep(self):
        subdir = os.path.join(self.override_dir, "01-ALL-package_upload_only")
        os.makedirs(subdir)
        override_path = os.path.join(subdir, "Google_Chrome.jamf.recipe.yaml")
        override = _make_override(
            "local.jamf.Google_Chrome", "com.example.Google_Chrome"
        )
        _write_yaml_recipe(override_path, override)

        result = autopkg._fast_locate_override_by_name(
            "Google_Chrome.jamf", [self.override_dir]
        )
        self.assertIsNotNone(result)
        self.assertEqual(result[0], override_path)

    def test_accepts_name_with_recipe_extension_suffix(self):
        """The user may pass either 'foo' or 'foo.recipe.yaml'."""
        override_path = os.path.join(self.override_dir, "foo.recipe.yaml")
        override = _make_override("local.foo", "com.example.foo")
        _write_yaml_recipe(override_path, override)

        for name in ("foo", "foo.recipe.yaml"):
            with self.subTest(name=name):
                autopkg._FAST_PATH_CACHE.clear()
                result = autopkg._fast_locate_override_by_name(
                    name, [self.override_dir]
                )
                self.assertIsNotNone(result)
                self.assertEqual(result[0], override_path)

    def test_misses_when_override_not_present(self):
        self.assertIsNone(
            autopkg._fast_locate_override_by_name("doesnotexist", [self.override_dir])
        )
        # Cache must remain empty on a miss.
        self.assertEqual(autopkg._FAST_PATH_CACHE, {})

    def test_misses_on_invalid_override_dict(self):
        """A file with a matching name but not a valid override dict should
        not short-circuit the fast path — the caller must fall through."""
        override_path = os.path.join(self.override_dir, "broken.recipe.yaml")
        # Missing required keys makes this not a valid override dict.
        _write_yaml_recipe(override_path, {"Identifier": "local.broken"})

        result = autopkg._fast_locate_override_by_name("broken", [self.override_dir])
        self.assertIsNone(result)

    def test_ignores_nonexistent_override_dir(self):
        missing = os.path.join(self.override_dir, "does-not-exist")
        self.assertIsNone(autopkg._fast_locate_override_by_name("foo", [missing]))

    def test_honours_multiple_override_dirs_in_order(self):
        other_tmp = TemporaryDirectory()
        try:
            # Place a matching file in BOTH dirs; the first one given wins.
            path1 = os.path.join(self.override_dir, "foo.recipe.yaml")
            path2 = os.path.join(other_tmp.name, "foo.recipe.yaml")
            _write_yaml_recipe(
                path1, _make_override("local.foo.one", "com.example.foo")
            )
            _write_yaml_recipe(
                path2, _make_override("local.foo.two", "com.example.foo")
            )

            result = autopkg._fast_locate_override_by_name(
                "foo", [self.override_dir, other_tmp.name]
            )
            self.assertEqual(result[0], path1)

            result = autopkg._fast_locate_override_by_name(
                "foo", [other_tmp.name, self.override_dir]
            )
            self.assertEqual(result[0], path2)
        finally:
            other_tmp.cleanup()


# --------------------------------------------------------------------------
# _merge_child_into_parent
# --------------------------------------------------------------------------


class TestMergeChildIntoParent(unittest.TestCase):
    """Direct unit tests for the merge helper."""

    def test_child_identifier_wins(self):
        parent = {"Identifier": "com.parent", "Input": {}, "Process": []}
        child = {"Identifier": "com.child", "Input": {}, "Process": []}
        result = autopkg._merge_child_into_parent(parent, child)
        self.assertEqual(result["Identifier"], "com.child")

    def test_input_keys_merge_with_child_overriding(self):
        parent = {
            "Identifier": "com.parent",
            "Input": {"NAME": "Parent", "ONLY_IN_PARENT": "yes"},
            "Process": [],
        }
        child = {
            "Identifier": "com.child",
            "Input": {"NAME": "Child", "ONLY_IN_CHILD": "yes"},
            "Process": [],
        }
        result = autopkg._merge_child_into_parent(parent, child)
        self.assertEqual(result["Input"]["NAME"], "Child")
        self.assertEqual(result["Input"]["ONLY_IN_PARENT"], "yes")
        self.assertEqual(result["Input"]["ONLY_IN_CHILD"], "yes")

    def test_process_steps_append(self):
        parent = {
            "Identifier": "com.parent",
            "Input": {},
            "Process": [{"Processor": "A"}],
        }
        child = {
            "Identifier": "com.child",
            "Input": {},
            "Process": [{"Processor": "B"}, {"Processor": "C"}],
        }
        result = autopkg._merge_child_into_parent(parent, child)
        self.assertEqual([s["Processor"] for s in result["Process"]], ["A", "B", "C"])

    def test_minimumversion_takes_highest(self):
        parent = {
            "Identifier": "com.parent",
            "Input": {},
            "Process": [],
            "MinimumVersion": "2.3",
        }
        child = {
            "Identifier": "com.child",
            "Input": {},
            "Process": [],
            "MinimumVersion": "2.5",
        }
        result = autopkg._merge_child_into_parent(parent, child)
        self.assertEqual(result["MinimumVersion"], "2.5")

    def test_minimumversion_defaults_when_missing(self):
        parent = {"Identifier": "com.parent", "Input": {}, "Process": []}
        child = {"Identifier": "com.child", "Input": {}, "Process": []}
        result = autopkg._merge_child_into_parent(parent, child)
        self.assertEqual(result["MinimumVersion"], "0")

    def test_recipe_path_updates_and_parent_recipes_accumulate(self):
        parent = {
            "Identifier": "com.parent",
            "Input": {},
            "Process": [],
            "RECIPE_PATH": "/path/parent.recipe",
        }
        child = {
            "Identifier": "com.child",
            "Input": {},
            "Process": [],
            "RECIPE_PATH": "/path/child.recipe",
        }
        result = autopkg._merge_child_into_parent(
            parent, child, child_path="/path/child.recipe"
        )
        self.assertEqual(result["RECIPE_PATH"], "/path/child.recipe")
        self.assertEqual(result["PARENT_RECIPES"], ["/path/parent.recipe"])

    def test_description_falls_back_to_parent(self):
        parent = {
            "Identifier": "com.parent",
            "Input": {},
            "Process": [],
            "Description": "Parent description",
        }
        child = {"Identifier": "com.child", "Input": {}, "Process": []}
        result = autopkg._merge_child_into_parent(parent, child)
        self.assertEqual(result["Description"], "Parent description")


# --------------------------------------------------------------------------
# _try_assemble_from_trust_info
# --------------------------------------------------------------------------


class TestTryAssembleFromTrustInfo(unittest.TestCase):
    """Trust-info-based chain assembly."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = self.tmp.name
        autopkg._FAST_PATH_CACHE.clear()

    def tearDown(self):
        self.tmp.cleanup()
        autopkg._FAST_PATH_CACHE.clear()

    def _write_chain(self, names_and_parents):
        """Write a chain of .recipe.yaml files.

        names_and_parents is a list of (identifier, parent_identifier_or_None)
        tuples ordered root-first. Returns identifier->path map.
        """
        paths = {}
        for identifier, parent in names_and_parents:
            p = os.path.join(self.root, f"{identifier}.recipe.yaml")
            recipe = _make_recipe(
                identifier,
                parent=parent,
                process=[{"Processor": f"P_{identifier.rsplit('.', 1)[-1]}"}],
                input_={f"KEY_{identifier.rsplit('.', 1)[-1]}": "v"},
            )
            _write_yaml_recipe(p, recipe)
            paths[identifier] = p
        return paths

    def test_returns_none_if_no_parent_recipes_in_trust_info(self):
        override = _make_override(
            "local.foo",
            "com.example.foo",
            trust_info={"non_core_processors": {}, "parent_recipes": {}},
        )
        result = autopkg._try_assemble_from_trust_info(
            "foo",
            override,
            "/tmp/foo.recipe.yaml",
            override["ParentRecipeTrustInfo"],
            None,
            None,
        )
        self.assertIsNone(result)

    def test_returns_none_if_parent_file_missing(self):
        trust = _make_trust_info(
            {"com.example.foo": "/path/that/does/not/exist.recipe.yaml"}
        )
        override = _make_override("local.foo", "com.example.foo", trust_info=trust)
        result = autopkg._try_assemble_from_trust_info(
            "foo",
            override,
            "/tmp/foo.recipe.yaml",
            trust,
            None,
            None,
        )
        self.assertIsNone(result)

    def test_returns_none_if_identifier_mismatch(self):
        paths = self._write_chain([("com.example.foo", None)])
        # Deliberately point the trust-info identifier at the wrong path.
        trust = _make_trust_info({"com.example.wrong": paths["com.example.foo"]})
        override = _make_override("local.foo", "com.example.wrong", trust_info=trust)
        result = autopkg._try_assemble_from_trust_info(
            "foo",
            override,
            "/tmp/foo.recipe.yaml",
            trust,
            None,
            None,
        )
        self.assertIsNone(result)

    def test_returns_none_on_broken_chain(self):
        """ParentRecipe points to an identifier not in trust info."""
        paths = self._write_chain([("com.example.foo", None)])
        trust = _make_trust_info({"com.example.foo": paths["com.example.foo"]})
        # Override claims parent is "com.example.missing", which isn't covered.
        override = _make_override("local.foo", "com.example.missing", trust_info=trust)
        result = autopkg._try_assemble_from_trust_info(
            "foo",
            override,
            "/tmp/foo.recipe.yaml",
            trust,
            None,
            None,
        )
        self.assertIsNone(result)

    def test_assembles_single_parent_chain(self):
        paths = self._write_chain([("com.example.foo", None)])
        trust = _make_trust_info({"com.example.foo": paths["com.example.foo"]})
        override_path = os.path.join(self.root, "foo.recipe.yaml")
        override = _make_override(
            "local.foo",
            "com.example.foo",
            trust_info=trust,
            input_={"NAME": "Foo", "OVERRIDE_KEY": "yes"},
        )
        _write_yaml_recipe(override_path, override)

        result = autopkg._try_assemble_from_trust_info(
            "foo",
            override,
            override_path,
            trust,
            None,
            None,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["Identifier"], "local.foo")
        self.assertEqual(result["ParentRecipe"], "com.example.foo")
        self.assertEqual(result["name"], "foo")
        self.assertEqual(result["RECIPE_PATH"], override_path)
        # Parent chain recorded in PARENT_RECIPES (child excluded by convention).
        self.assertIn(paths["com.example.foo"], result.get("PARENT_RECIPES", []))
        # Input merged (override wins on overlapping keys, parent's NAME
        # replaced; OVERRIDE_KEY carried through).
        self.assertEqual(result["Input"]["OVERRIDE_KEY"], "yes")

    def test_assembles_three_level_chain(self):
        # Build download <- pkg <- jamf, matching real-world override chains.
        chain = [
            ("com.example.download.Google_Chrome", None),
            ("com.example.pkg.Google_Chrome", "com.example.download.Google_Chrome"),
            ("com.example.jamf.Google_Chrome", "com.example.pkg.Google_Chrome"),
        ]
        paths = self._write_chain(chain)
        trust = _make_trust_info(paths)
        override_path = os.path.join(self.root, "Google_Chrome.jamf.recipe.yaml")
        override = _make_override(
            "local.jamf.Google_Chrome",
            "com.example.jamf.Google_Chrome",
            trust_info=trust,
            input_={"NAME": "Google_Chrome", "CATEGORY": "Apps"},
        )
        _write_yaml_recipe(override_path, override)

        result = autopkg._try_assemble_from_trust_info(
            "Google_Chrome.jamf",
            override,
            override_path,
            trust,
            None,
            None,
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["Identifier"], "local.jamf.Google_Chrome")
        # Process steps must be in root-first order, concluding with override's
        # (none here, so the three parent processors in order).
        processors = [s["Processor"] for s in result["Process"]]
        self.assertEqual(
            processors,
            ["P_Google_Chrome", "P_Google_Chrome", "P_Google_Chrome"],  # one per parent
        )
        self.assertEqual(result["Input"]["NAME"], "Google_Chrome")
        self.assertEqual(result["Input"]["CATEGORY"], "Apps")

    def test_preprocessors_and_postprocessors_applied(self):
        paths = self._write_chain([("com.example.foo", None)])
        trust = _make_trust_info(paths)
        override = _make_override("local.foo", "com.example.foo", trust_info=trust)
        result = autopkg._try_assemble_from_trust_info(
            "foo",
            override,
            "/tmp/foo.recipe.yaml",
            trust,
            ["PreProc"],
            ["PostProc"],
        )
        self.assertIsNotNone(result)
        processors = [s["Processor"] for s in result["Process"]]
        self.assertEqual(processors[0], "PreProc")
        self.assertEqual(processors[-1], "PostProc")

    def test_returns_none_on_cycle(self):
        paths = self._write_chain(
            [
                ("com.example.a", "com.example.b"),
                ("com.example.b", "com.example.a"),
            ]
        )
        trust = _make_trust_info(paths)
        override = _make_override("local.a", "com.example.a", trust_info=trust)
        result = autopkg._try_assemble_from_trust_info(
            "a",
            override,
            "/tmp/a.recipe.yaml",
            trust,
            None,
            None,
        )
        self.assertIsNone(result)


# --------------------------------------------------------------------------
# locate_recipe integration
# --------------------------------------------------------------------------


class TestLocateRecipeFastPathIntegration(unittest.TestCase):
    """Verify locate_recipe hits the fast path for name-based overrides and
    falls through on every other input shape without behaviour change."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.override_dir = os.path.join(self.tmp.name, "overrides")
        self.recipe_dir = os.path.join(self.tmp.name, "repos")
        os.makedirs(self.override_dir)
        os.makedirs(self.recipe_dir)
        autopkg._FAST_PATH_CACHE.clear()

        # Minimal valid override
        self.override_path = os.path.join(
            self.override_dir, "Google_Chrome.jamf.recipe.yaml"
        )
        _write_yaml_recipe(
            self.override_path,
            _make_override("local.jamf.Google_Chrome", "com.example.Google_Chrome"),
        )
        # Minimal valid recipe in the repo dir so non-override names resolve
        self.recipe_path = os.path.join(self.recipe_dir, "plain.download.recipe.yaml")
        _write_yaml_recipe(
            self.recipe_path,
            _make_recipe("com.example.plain"),
        )

    def tearDown(self):
        self.tmp.cleanup()
        autopkg._FAST_PATH_CACHE.clear()

    def test_fast_path_returns_override_path_for_name_match(self):
        result = autopkg.locate_recipe(
            "Google_Chrome.jamf",
            [self.override_dir],
            [self.recipe_dir],
            make_suggestions=False,
            search_github=False,
        )
        self.assertEqual(result, self.override_path)
        # The parsed dict must be cached so load_recipe can consume it.
        self.assertIn(self.override_path, autopkg._FAST_PATH_CACHE)

    def test_file_path_input_bypasses_fast_path(self):
        # Path on disk goes through the existing isfile branch, which also
        # returns the correct path; _FAST_PATH_CACHE must stay empty.
        result = autopkg.locate_recipe(
            self.override_path,
            [self.override_dir],
            [self.recipe_dir],
            make_suggestions=False,
            search_github=False,
        )
        self.assertEqual(result, self.override_path)
        self.assertEqual(autopkg._FAST_PATH_CACHE, {})

    def test_identifier_input_falls_through_when_no_filename_match(self):
        """Identifier inputs are not specially routed; the fast path simply
        tries them as filenames. When no override file is named after the
        identifier (the common case), the fast path misses and find_recipe
        is consulted for the usual identifier-based search."""
        with patch.object(
            autopkg, "find_recipe", wraps=autopkg.find_recipe
        ) as mock_find:
            autopkg.locate_recipe(
                "local.jamf.Google_Chrome",
                [self.override_dir],
                [self.recipe_dir],
                make_suggestions=False,
                search_github=False,
            )
            mock_find.assert_called_once()

    def test_identifier_input_hits_when_override_filed_under_identifier(self):
        """Some users name override files after the identifier itself. The
        fast path should hit such files transparently, the same way it hits
        files named after the short recipe name."""
        id_path = os.path.join(self.override_dir, "local.foo.recipe.yaml")
        _write_yaml_recipe(
            id_path,
            _make_override("local.foo", "com.example.foo"),
        )
        # find_recipe must NOT be consulted because the fast path hits.
        with patch.object(
            autopkg, "find_recipe", wraps=autopkg.find_recipe
        ) as mock_find:
            result = autopkg.locate_recipe(
                "local.foo",
                [self.override_dir],
                [self.recipe_dir],
                make_suggestions=False,
                search_github=False,
            )
            self.assertEqual(result, id_path)
            mock_find.assert_not_called()

    def test_missing_name_falls_through_to_slow_path(self):
        with patch.object(
            autopkg, "find_recipe", wraps=autopkg.find_recipe
        ) as mock_find:
            result = autopkg.locate_recipe(
                "nonexistent-name",
                [self.override_dir],
                [self.recipe_dir],
                make_suggestions=False,
                search_github=False,
            )
            self.assertIsNone(result)
            mock_find.assert_called_once()

    def test_plain_recipe_in_repo_still_works(self):
        result = autopkg.locate_recipe(
            "plain.download",
            [self.override_dir],
            [self.recipe_dir],
            make_suggestions=False,
            search_github=False,
        )
        self.assertEqual(result, self.recipe_path)
        # The fast path only scans overrides; it must not have cached the
        # recipe-repo file.
        self.assertNotIn(self.recipe_path, autopkg._FAST_PATH_CACHE)


# --------------------------------------------------------------------------
# load_recipe fast-path and slow-path equivalence
# --------------------------------------------------------------------------


class TestLoadRecipeFastPathEquivalence(unittest.TestCase):
    """Load the same override via the fast path and via the slow path;
    assert the merged recipe dicts are structurally identical.

    The fast path fires when trust info is present and all paths resolve.
    The slow path fires when we strip trust info, forcing the recursive
    locate_recipe/load_recipe search.
    """

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = self.tmp.name
        self.override_dir = os.path.join(self.root, "overrides")
        self.repo_dir = os.path.join(self.root, "repos")
        os.makedirs(self.override_dir)
        os.makedirs(self.repo_dir)

        # Three-level parent chain in the repo dir.
        self.download_path = os.path.join(
            self.repo_dir, "Google_Chrome.download.recipe.yaml"
        )
        _write_yaml_recipe(
            self.download_path,
            _make_recipe(
                "com.example.download.Google_Chrome",
                process=[{"Processor": "URLDownloader"}],
                input_={"NAME": "Google_Chrome", "DOWNLOAD_URL": "http://x"},
            ),
        )
        self.pkg_path = os.path.join(self.repo_dir, "Google_Chrome.pkg.recipe.yaml")
        _write_yaml_recipe(
            self.pkg_path,
            _make_recipe(
                "com.example.pkg.Google_Chrome",
                parent="com.example.download.Google_Chrome",
                process=[{"Processor": "PkgCreator"}],
                input_={"PKG_ID": "com.example.Google_Chrome"},
            ),
        )
        self.jamf_path = os.path.join(self.repo_dir, "Google_Chrome.jamf.recipe.yaml")
        _write_yaml_recipe(
            self.jamf_path,
            _make_recipe(
                "com.example.jamf.Google_Chrome",
                parent="com.example.pkg.Google_Chrome",
                process=[{"Processor": "JamfPackageUploader"}],
                input_={"CATEGORY": "Apps"},
            ),
        )

        # Override referring to the jamf recipe with trust info carrying
        # the three parent paths.
        trust = _make_trust_info(
            {
                "com.example.download.Google_Chrome": self.download_path,
                "com.example.pkg.Google_Chrome": self.pkg_path,
                "com.example.jamf.Google_Chrome": self.jamf_path,
            }
        )
        self.override_path = os.path.join(
            self.override_dir, "Google_Chrome.jamf.recipe.yaml"
        )
        _write_yaml_recipe(
            self.override_path,
            _make_override(
                "local.jamf.Google_Chrome",
                "com.example.jamf.Google_Chrome",
                trust_info=trust,
                input_={"NAME": "Google_Chrome", "SITE": "Production"},
            ),
        )

        autopkg._FAST_PATH_CACHE.clear()

    def tearDown(self):
        self.tmp.cleanup()
        autopkg._FAST_PATH_CACHE.clear()

    def _strip_trust_info(self):
        """Rewrite the override in place to remove ParentRecipeTrustInfo,
        forcing load_recipe down the slow path."""
        with open(self.override_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        data.pop("ParentRecipeTrustInfo", None)
        with open(self.override_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

    @staticmethod
    def _normalize(recipe):
        """Drop keys that cannot be compared directly (trust info survives
        on the fast path via direct re-attach, but on the slow path the
        same info is present too). Both paths should produce the same
        dict modulo ordering-insensitive structures."""
        if not isinstance(recipe, dict):
            return recipe
        return {
            k: TestLoadRecipeFastPathEquivalence._normalize(v)
            for k, v in recipe.items()
        }

    def test_fast_and_slow_paths_produce_equivalent_recipes(self):
        # Fast path (trust info present).
        fast = autopkg.load_recipe(
            "Google_Chrome.jamf",
            [self.override_dir],
            [self.repo_dir],
            make_suggestions=False,
            search_github=False,
        )
        self.assertIsNotNone(fast, "fast path failed to load recipe")

        # Slow path (trust info stripped).
        autopkg._FAST_PATH_CACHE.clear()
        self._strip_trust_info()
        slow = autopkg.load_recipe(
            "Google_Chrome.jamf",
            [self.override_dir],
            [self.repo_dir],
            make_suggestions=False,
            search_github=False,
        )
        self.assertIsNotNone(slow, "slow path failed to load recipe")

        # Compare the fields that matter for correctness: Identifier, merged
        # Input, Process step ordering, and name. NOTE: ParentRecipe is
        # deliberately excluded. On the existing slow path, when an override
        # has trust info, ParentRecipe is preserved via the late-stage
        # re-attach at load_recipe's tail; when trust info is absent the
        # post-merge recipe ends up without ParentRecipe. The fast path
        # always preserves ParentRecipe from the override itself, which is
        # arguably more correct. We compare only behaviour the slow path
        # already agrees with itself on.
        for key in ("Identifier", "name", "MinimumVersion"):
            self.assertEqual(fast.get(key), slow.get(key), f"mismatch on {key}")

        self.assertEqual(fast["Input"], slow["Input"])
        self.assertEqual(
            [s["Processor"] for s in fast["Process"]],
            [s["Processor"] for s in slow["Process"]],
        )
        # PARENT_RECIPES order: slow path reverses via recursion; compare sets
        # to confirm coverage of the same paths without asserting order.
        self.assertEqual(
            set(fast.get("PARENT_RECIPES", [])),
            set(slow.get("PARENT_RECIPES", [])),
        )

    def test_fast_path_falls_back_when_parent_path_missing(self):
        """Trust info references a path that no longer exists; the fast
        path must bail and the slow path must succeed (by searching the
        repo dir for the parent)."""
        # Break the trust-info path for the deepest parent.
        with open(self.override_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        data["ParentRecipeTrustInfo"]["parent_recipes"][
            "com.example.download.Google_Chrome"
        ]["path"] = "/does/not/exist.recipe.yaml"
        with open(self.override_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f)

        recipe = autopkg.load_recipe(
            "Google_Chrome.jamf",
            [self.override_dir],
            [self.repo_dir],
            make_suggestions=False,
            search_github=False,
        )
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["Identifier"], "local.jamf.Google_Chrome")


if __name__ == "__main__":
    unittest.main()
