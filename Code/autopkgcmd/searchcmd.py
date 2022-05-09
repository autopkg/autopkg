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

import json
import os
from typing import List
from urllib.parse import quote

from autopkgcmd.opts import common_parse, gen_common_parser
from autopkglib import log_err
from autopkglib.github import (
    DEFAULT_SEARCH_USER,
    GitHubSession,
    print_gh_search_results,
)


def search_recipes(argv: List[str]):
    """Search recipes on GitHub"""
    verb = argv[1]
    parser = gen_common_parser()
    parser.set_usage(
        f"Usage: %prog {verb} [options] search_term\n"
        "Search for recipes on GitHub. The AutoPkg organization "
        "at github.com/autopkg\n"
        "is the canonical 'repository' of recipe repos, "
        "which is what is searched by\n"
        "default."
    )
    parser.add_option(
        "-u",
        "--user",
        default=DEFAULT_SEARCH_USER,
        help=(
            "Alternate GitHub user whose repos to search. "
            f"Defaults to '{DEFAULT_SEARCH_USER}'."
        ),
    )
    parser.add_option(
        "-p",
        "--path-only",
        action="store_true",
        default=False,
        help=(
            "Restrict search results to the recipe's path "
            "only. Note that the search API currently does not "
            "support fuzzy matches, so only exact directory or "
            "filenames (minus the extensions) will be "
            "returned."
        ),
    )
    parser.add_option(
        "-t",
        "--use-token",
        action="store_true",
        default=False,
        help=(
            "Use a public-scope GitHub token for a higher "
            "rate limit. If a token doesn't exist, you'll "
            "be prompted for your account credentials to "
            "create one."
        ),
    )

    # Parse arguments
    (options, arguments) = common_parse(parser, argv)
    if len(arguments) < 1:
        log_err("No search query specified!")
        return 1

    results_limit = 100
    term = quote(arguments[0])

    results = GitHubSession().search_for_name(
        term, options.path_only, options.user, options.use_token, results_limit
    )
    if not results:
        return 2

    print_gh_search_results(results)

    print()
    print("To add a new recipe repo, use 'autopkg repo-add <repo name>'")

    if len(results) > results_limit:
        print()
        print(
            "Warning: Search yielded more than 100 results. Please try a "
            "more specific search term."
        )
        return 3
    return 0


def check_search_cache(cache_path):
    """Update local search index, if it's missing or out of date."""

    gh = GitHubSession()
    cache_endpoint = (
        "/repos/homebysix/autopkg-recipe-index/contents/index.json?ref=main"
    )

    # Retrieve metadata about search index file from GitHub API
    cache_meta = gh.call_api(cache_endpoint, accept="application/vnd.github.v3+json")
    if cache_meta[1] != 200:
        print("WARNING: Unable to retrieve search index metadata from GitHub API.")
        return

    # Warn if search index file is approaching 100 MB
    # https://docs.github.com/en/rest/repos/contents#size-limits
    search_index_size_msg = (
        "WARNING: Search index size is %s GitHub's API limit for raw content "
        "retrieval (100 MB). Please open an issue here if one was not already "
        "created: https://github.com/autopkg/autopkg/issues"
    )
    if cache_meta[0]["size"] > (90 * 1024 * 1024):
        print(search_index_size_msg % "nearing")
    elif cache_meta[0]["size"] > (100 * 1024 * 1024):
        print(search_index_size_msg % "greater than")

    # If cache exists locally, check whether it's current
    if os.path.isfile(cache_path) and os.path.isfile(cache_path + ".etag"):
        with open(cache_path + ".etag", "r", encoding="utf-8") as openfile:
            local_etag = openfile.read().strip('"')
        if local_etag == cache_meta[0]["sha"]:
            # Local cache is already current
            return

    # Write etag file
    with open(cache_path + ".etag", "w", encoding="utf-8") as openfile:
        openfile.write(cache_meta[0]["sha"])

    # Write cache file
    cache_contents = gh.call_api(cache_endpoint, accept="application/vnd.github.v3.raw")
    if cache_contents[1] != 200:
        print("WARNING: Unable to retrieve search index contents from GitHub API.")
        return
    with open(cache_path, "w", encoding="utf-8") as openfile:
        openfile.write(json.dumps(cache_contents[0], indent=2))


def get_table_row(row_items, col_widths, header=False):
    """This function takes table row content (list of strings) and column
    widths (list of integers) as input and outputs a string representing a
    table row in Markdown, with normalized "pretty" spacing that is readable
    when unrendered."""

    output = ""
    header_sep = "\n"
    column_space = 4
    for idx, cell in enumerate(row_items):
        padding = col_widths[idx] - len(cell) + column_space
        header_sep += "-" * len(cell) + " " * padding
        output += f"{cell}{' ' * padding}"

    if header:
        return output + header_sep

    return output


def normalize_keyword(keyword):
    """Normalizes capitalization, punctuation, and spacing of search keywords
    for better matching."""
    # TODO: Consider implementing fuzzywuzzy or some other fuzzy search method
    keyword = keyword.lower()
    replacements = {" ": "", ".": "", ",": "", "-": ""}
    for old, new in replacements.items():
        keyword = keyword.replace(old, new)

    return keyword


def new_search_recipes(argv: List[str]):
    """Search recipes in the AutoPkg org on GitHub using a cached index file."""
    verb = argv[1]
    parser = gen_common_parser()
    parser.set_usage(
        f"Usage: %prog {verb} [options] search_term\n"
        "Search for recipes on GitHub using a cached index file. The AutoPkg "
        "organization at github.com/autopkg\nis the canonical 'repository' of "
        "recipe repos, which is what is searched by\ndefault."
    )

    # Parse arguments
    (options, arguments) = common_parse(parser, argv)
    if len(arguments) < 1:
        log_err("No search query specified!")
        return 1

    results_limit = 100

    # Update and load local search index cache
    cache_path = os.path.expanduser("~/Library/AutoPkg/search_index.json")
    check_search_cache(cache_path)
    with open(cache_path, "rb") as openfile:
        search_index = json.load(openfile)

    # Perform the search against shortnames
    result_ids = []
    for candidate, identifiers in search_index["shortnames"].items():
        if normalize_keyword(arguments[0]) in normalize_keyword(candidate):
            result_ids.extend(identifiers)

    # Perform the search against other recipe info
    searchable_keys = ("name", "munki_display_name", "jamf_display_name")
    for identifier, info in search_index["identifiers"].items():
        if info.get("deprecated"):
            continue
        for key in searchable_keys:
            if info.get(key):
                if normalize_keyword(arguments[0]) in normalize_keyword(info[key]):
                    result_ids.append(identifier)
    if not result_ids:
        return 2
    result_ids = list(set(result_ids))

    # Collect result info into result list
    header_items = ("Name", "Repo", "Path")
    result_items = []
    for result_id in result_ids:
        name = os.path.split(search_index["identifiers"][result_id]["path"])[-1]
        repo = search_index["identifiers"][result_id]["repo"]
        path = search_index["identifiers"][result_id]["path"]
        if repo.startswith("autopkg/"):
            repo = repo.replace("autopkg/", "")
        result_items.append((name, repo, path))
    col_widths = [
        max([len(x[i]) for x in result_items] + [len(header_items[i])])
        for i in range(0, len(header_items))
    ]

    # Print result table
    print()
    print(get_table_row(header_items, col_widths, header=True))
    for row in result_items:
        print(get_table_row(row, col_widths))
    print()
    print("To add a new recipe repo, use 'autopkg repo-add <repo name>'")

    # Warn if more results than the result limit
    if len(result_items) > results_limit:
        print()
        print(
            f"Warning: Search yielded more than {results_limit} results. Please try a "
            "more specific search term."
        )
        return 3
    return 0
