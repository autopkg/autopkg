#!/usr/local/autopkg/python
#
# Copyright 2023 Elliot Jordan
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

"""
e2e_compare_branch_exitcodes.py

This script is intended to test a new feature or bugfix branch of AutoPkg against a known stable
branch (e.g. main/master).

A specified number of recipes are selected at random from a provided path. Each recipe is run twice
(once without cache, once with) on the control branch, then run twice again on the experimental
branch. If the exit codes produced by the control branch differ from the exit codes produced by the
experimental branch for the same recipe, the discrepancy is reported.
"""

import argparse
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from random import shuffle

SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_AUTOPKG_REPO = SCRIPT_PATH.parents[2]

# Control (known good) and experimental branch names
DEFAULT_CTRL_BRANCH = "master"
DEFAULT_EXPR_BRANCH = "dev"

# Types of recipes you wish to test (recommended: download, pkg)
# Munki tools and a valid Munki repo required to test munki recipes
DEFAULT_TYPES_TO_TEST = ("download", "pkg")

# How many recipes you wish to run the test on
DEFAULT_RECIPE_COUNT = 25


def parse_args(argv=None):
    """Parse command-line arguments."""
    makecatalogs_path = shutil.which("makecatalogs")
    parser = argparse.ArgumentParser(
        description=(
            "Compare AutoPkg recipe exit codes between two branches of this "
            "checkout."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "recipe_repos",
        type=Path,
        help="Path to a folder that contains AutoPkg recipes.",
    )
    parser.add_argument(
        "--autopkg-repo",
        type=Path,
        default=DEFAULT_AUTOPKG_REPO,
        help="Path to a github.com/autopkg/autopkg clone.",
    )
    parser.add_argument(
        "--autopkg-bin",
        type=Path,
        help=(
            "Path to the autopkg executable to test. Defaults to "
            "AUTOPKG_REPO/Code/autopkg."
        ),
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path.home() / "Library" / "AutoPkg" / "Cache",
        help=(
            "Path to the AutoPkg cache directory to use and clear before each "
            "recipe's first run."
        ),
    )
    parser.add_argument(
        "--ctrl-branch",
        default=DEFAULT_CTRL_BRANCH,
        help="Known-good branch to compare against.",
    )
    parser.add_argument(
        "--expr-branch",
        default=DEFAULT_EXPR_BRANCH,
        help="Branch being tested.",
    )
    parser.add_argument(
        "--recipe-count",
        type=int,
        default=DEFAULT_RECIPE_COUNT,
        help="Number of randomly selected recipes to test.",
    )
    parser.add_argument(
        "--types",
        nargs="+",
        default=list(DEFAULT_TYPES_TO_TEST),
        metavar="TYPE",
        help=(
            "Recipe type components to test. For TYPE 'download', this matches "
            "*.download.recipe, *.download.recipe.plist, and "
            "*.download.recipe.yaml."
        ),
    )
    parser.add_argument(
        "--autopkg-option",
        action="append",
        default=[],
        dest="additional_opts",
        help=(
            "Additional option to pass to 'autopkg run'. Repeat this argument "
            "for multiple options. Use '--autopkg-option=-k' for options that "
            "start with a dash."
        ),
    )
    parser.add_argument(
        "--makecatalogs-path",
        type=Path,
        default=Path(makecatalogs_path) if makecatalogs_path else None,
        help="Path to makecatalogs. Only used when testing munki recipes.",
    )
    return parser.parse_args(argv)


def recipe_suffixes(recipe_types):
    """Return filename suffixes for the selected AutoPkg recipe types."""
    return tuple(
        f".{recipe_type}.recipe{suffix}"
        for recipe_type in recipe_types
        for suffix in ("", ".plist", ".yaml")
    )


def find_recipes(recipe_repos, suffixes):
    """Return recipe paths under recipe_repos that match the requested types."""
    recipes = []
    for root, dirs, files in os.walk(recipe_repos):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        recipes.extend(
            Path(root, filename) for filename in files if filename.endswith(suffixes)
        )
    return recipes


def clear_cache(cache_dir):
    """Clear the AutoPkg Cache folder."""
    shutil.rmtree(cache_dir, ignore_errors=True)


def test_recipe(
    filepath,
    autopkg_path,
    additional_opts,
    cache_dir,
    cache_prefs_path,
    makecatalogs_path=None,
):
    """Test a specified recipe twice — once with a clear cache and once with
    cache primed."""
    clear_cache(cache_dir)
    recipe_path = str(filepath)
    cmd = [
        str(autopkg_path),
        "run",
        "--prefs",
        str(cache_prefs_path),
        "--quiet",
        recipe_path,
    ]
    cmd.extend(additional_opts)

    exit_codes = []
    for attempt in ("1st", "2nd"):
        proc = subprocess.run(cmd, check=False, capture_output=True)
        exit_codes.append(proc.returncode)
        print("  %s run finished with exit code %d" % (attempt, proc.returncode))
        if ".munki." in recipe_path:
            if makecatalogs_path:
                subprocess.run(
                    [str(makecatalogs_path)], check=False, capture_output=True
                )
            else:
                print("  makecatalogs not found; skipping catalog rebuild")

    return tuple(exit_codes)


def write_cache_prefs(cache_dir):
    """Write a temporary prefs plist that points AutoPkg at the test cache."""
    with tempfile.NamedTemporaryFile(
        "wb", prefix="autopkg-e2e-", suffix=".plist", delete=False
    ) as prefs_file:
        plistlib.dump({"CACHE_DIR": str(cache_dir)}, prefs_file)
        return Path(prefs_file.name)


def create_worktree(autopkg_repo, branch, parent_dir):
    """Create a git worktree for branch under parent_dir and return its path."""
    worktree_path = parent_dir / branch
    proc = subprocess.run(
        [
            "git",
            "-C",
            str(autopkg_repo),
            "worktree",
            "add",
            "--force",
            str(worktree_path),
            branch,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode:
        if proc.stderr:
            sys.stderr.write(proc.stderr)
        sys.exit(proc.returncode)
    return worktree_path


def remove_worktrees(autopkg_repo, *worktree_paths):
    """Remove git worktrees, ignoring errors."""
    for path in worktree_paths:
        if path is None:
            continue
        subprocess.run(
            [
                "git",
                "-C",
                str(autopkg_repo),
                "worktree",
                "remove",
                "--force",
                str(path),
            ],
            check=False,
            capture_output=True,
        )


def test_recipes_for_branch(
    branch,
    recipes,
    recipe_repos,
    autopkg_bin,
    additional_opts,
    cache_dir,
    cache_prefs_path,
    makecatalogs_path,
):
    """Test all selected recipes on a branch via its worktree."""
    print(f"Testing on autopkg {branch} branch")

    branch_results = {}
    for idx, recipe in enumerate(recipes):
        recipe_label = recipe.relative_to(recipe_repos)
        print("Processing %s (%d of %d)..." % (recipe_label, idx + 1, len(recipes)))
        branch_results[recipe] = test_recipe(
            recipe,
            autopkg_bin,
            additional_opts,
            cache_dir,
            cache_prefs_path,
            makecatalogs_path,
        )

    return branch_results


def main() -> None:
    """Main process."""
    args = parse_args()
    recipe_repos = args.recipe_repos.expanduser().resolve()
    autopkg_repo = args.autopkg_repo.expanduser().resolve()
    explicit_bin = args.autopkg_bin.expanduser().resolve() if args.autopkg_bin else None
    cache_dir = args.cache_dir.expanduser().resolve()
    makecatalogs_path = (
        args.makecatalogs_path.expanduser().resolve()
        if args.makecatalogs_path
        else None
    )
    types_to_test = recipe_suffixes(args.types)

    if not recipe_repos.is_dir():
        sys.exit(f"Recipe repo path is not a directory: {recipe_repos}")
    if not autopkg_repo.is_dir():
        sys.exit(f"AutoPkg repo path is not a directory: {autopkg_repo}")
    if explicit_bin and not explicit_bin.is_file():
        sys.exit(f"AutoPkg executable not found: {explicit_bin}")
    if args.recipe_count < 1:
        sys.exit("Recipe count must be at least 1")

    found_recipes = find_recipes(recipe_repos, types_to_test)
    if not found_recipes:
        sys.exit(f"No matching recipes found in: {recipe_repos}")

    # Randomize the desired number of recipes to test on
    shuffle(found_recipes)
    found_recipes = found_recipes[: args.recipe_count]

    worktree_base = Path(tempfile.mkdtemp(prefix="autopkg-e2e-"))
    cache_prefs_path = write_cache_prefs(cache_dir)
    ctrl_worktree = None
    expr_worktree = None
    try:
        ctrl_worktree = create_worktree(autopkg_repo, args.ctrl_branch, worktree_base)
        ctrl_bin = explicit_bin or (ctrl_worktree / "Code" / "autopkg").resolve()
        ctrl_results = test_recipes_for_branch(
            args.ctrl_branch,
            found_recipes,
            recipe_repos,
            ctrl_bin,
            args.additional_opts,
            cache_dir,
            cache_prefs_path,
            makecatalogs_path,
        )
        expr_worktree = create_worktree(autopkg_repo, args.expr_branch, worktree_base)
        expr_bin = explicit_bin or (expr_worktree / "Code" / "autopkg").resolve()
        expr_results = test_recipes_for_branch(
            args.expr_branch,
            found_recipes,
            recipe_repos,
            expr_bin,
            args.additional_opts,
            cache_dir,
            cache_prefs_path,
            makecatalogs_path,
        )
    finally:
        remove_worktrees(autopkg_repo, ctrl_worktree, expr_worktree)
        shutil.rmtree(worktree_base, ignore_errors=True)
        cache_prefs_path.unlink(missing_ok=True)

    error_list = []
    for recipe in found_recipes:
        recipe_label = str(recipe.relative_to(recipe_repos))
        if ctrl_results[recipe] != expr_results[recipe]:
            print("  Inconsistency detected: %s" % recipe_label)
            error_list.append(recipe_label)

    if error_list:
        print("Inconsistencies encountered:")
        print("\n".join(error_list))
        sys.exit(1)

    print("No inconsistencies encountered.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCtrl-C received.")
        sys.exit(130)
