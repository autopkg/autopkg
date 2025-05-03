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

"""
e2e_compare_branch_exitcodes.py

This script is intended to test a new feature or bugfix branch of AutoPkg against a known stable
branch (e.g. main/master).

A specified number of recipes are selected at random from a provided path. Each recipe is run twice
(once without cache, once with) on the control branch, then run twice again on the experimental
branch. If the exit codes produced by the control branch differ from the exit codes produced by the
experimental branch for the same recipe, the discrepancy is reported.
"""

import os
import subprocess
import sys
from random import shuffle

# Path to your local github.com/autopkg/autopkg clone
AUTOPKG_REPO = os.path.expanduser("~/Developer/autopkg")

# Path to a folder that contains AutoPkg recipes
RECIPE_REPOS = os.path.expanduser("~/Developer/repo-lasso/repos/autopkg")

# Types of recipes you wish to test (recommended: download, pkg)
# Munki tools and a valid Munki repo required to test munki recipes
TYPES_TO_TEST = ["download", "pkg"]
TYPES_TO_TEST = list([f".{x}.recipe" for x in TYPES_TO_TEST])
TYPES_TO_TEST.extend([f"{x}.yaml" for x in TYPES_TO_TEST])
TYPES_TO_TEST = tuple(TYPES_TO_TEST)

# How many recipes you wish to run the test on
RECIPE_COUNT = 100

# Control (known good) and experimental branch names
CONTROL_BRANCH = "master"
EXPER_BRANCH = "dev-2.7.x"


def clear_cache():
    """Clear the AutoPkg Cache folder."""
    cache_path = os.path.expanduser("~/Library/AutoPkg/Cache")
    cmd = ["rm", "-rf", cache_path]
    subprocess.run(cmd, check=False)


def test_recipe(filepath, autopkg_path="/usr/local/bin/autopkg"):
    """Test a specified recipe twice — once with a clear cache and once with
    cache primed."""
    clear_cache()
    results = {"1st": None, "2nd": None}
    for attempt in results.keys():
        cmd = [autopkg_path, "run", "--quiet", filepath]
        proc = subprocess.run(cmd, check=False, capture_output=True)
        results[attempt] = proc.returncode
        print("  %s run finished with exit code %d" % (attempt, proc.returncode))
        if ".munki." in filepath:
            _ = subprocess.run(
                ["/usr/local/munki/makecatalogs"], check=False, capture_output=True
            )

    return results["1st"], results["2nd"]


def main():
    """Main process."""

    # Gather list of eligible recipes.
    found_recipes = []
    for root, dirs, files in os.walk(RECIPE_REPOS):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        found_recipes.extend(
            [
                os.path.relpath(os.path.join(root, x))
                for x in files
                if x.endswith(TYPES_TO_TEST)
            ]
        )

    # Randomize the desired number of recipes to test on
    shuffle(found_recipes)
    found_recipes = found_recipes[:RECIPE_COUNT]

    # Iterate through all test recipes, capturing exit codes
    error_list = []
    try:
        for idx, recipe in enumerate(found_recipes):
            print("Processing %s (%d of %d)..." % (recipe, idx + 1, len(found_recipes)))

            print(f"  Testing on autopkg {CONTROL_BRANCH} branch")
            subprocess.run(
                ["git", "-C", AUTOPKG_REPO, "checkout", CONTROL_BRANCH],
                check=False,
                capture_output=True,
                text=True,
            )
            c1, c2 = test_recipe(recipe, os.path.join(AUTOPKG_REPO, "Code/autopkg"))

            print(f"  Testing on autopkg {EXPER_BRANCH} branch")
            subprocess.run(
                ["git", "-C", AUTOPKG_REPO, "checkout", EXPER_BRANCH],
                check=False,
                capture_output=True,
                text=True,
            )
            x1, x2 = test_recipe(recipe, os.path.join(AUTOPKG_REPO, "Code/autopkg"))
            if not all((c1 == x1, c2 == x2)):
                print("  Inconsistency detected: %s" % recipe)
                error_list.append(recipe)
    except KeyboardInterrupt:
        print("\nCtrl-C received.")
    finally:
        if error_list:
            print("Inconsistencies encountered:")
            print("\n".join(error_list))
            sys.exit(1)
        else:
            print("No inconsistencies encountered.")


if __name__ == "__main__":
    main()
