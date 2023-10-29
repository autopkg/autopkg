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
import re
from typing import List
from urllib.parse import quote_plus

from autopkgcmd.opts import common_parse, gen_common_parser
from autopkglib.apgithub import (
    DEFAULT_SEARCH_USER,
    GitHubSession,
    print_gh_search_results,
)
from autopkglib.common import log, log_err
from autopkglib.URLGetter import URLGetter


def check_search_cache(cache_path: str):
    """Update local search index, if it's missing or out of date."""

    token = GitHubSession().auth_token.token
    api = URLGetter()

    # Retrieve metadata about search index file from GitHub API
    cache_endpoint = "repos/autopkg/index/contents/index.json?ref=main"
    headers = {
        "Authentication": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    curl_cmd = api.prepare_curl_cmd()
    api.add_curl_headers(curl_cmd, headers)
    curl_cmd.extend(["--url", f"https://api.github.com/{cache_endpoint}"])
    stdout, _, returncode = api.execute_curl(curl_cmd)
    if returncode != 0:
        log_err("WARNING: Unable to retrieve search index metadata from GitHub API.")
        return
    cache_meta = json.loads(stdout)

    # Warn if search index file is approaching 100 MB
    # https://docs.github.com/en/rest/repos/contents#size-limits
    search_index_size_msg = (
        "WARNING: Search index size is %s GitHub's API limit for raw content "
        "retrieval (100 MB). Please open an issue here if one was not already "
        "created: https://github.com/autopkg/autopkg/issues"
    )
    if cache_meta["size"] > (90 * 1024 * 1024):
        log_err(search_index_size_msg % "nearing")
    elif cache_meta["size"] > (100 * 1024 * 1024):
        log_err(search_index_size_msg % "greater than")

    # If cache exists locally, check whether it's current
    if os.path.isfile(cache_path) and os.path.isfile(cache_path + ".etag"):
        with open(cache_path + ".etag", "r", encoding="utf-8") as openfile:
            local_etag = openfile.read().strip('"')
        if local_etag == cache_meta["sha"]:
            # Local cache is already current
            return

    # Write etag file
    with open(cache_path + ".etag", "w", encoding="utf-8") as openfile:
        openfile.write(cache_meta["sha"])

    # Write cache file
    log("Refreshing local search index...")
    headers = {
        "Authentication": f"Bearer {token}",
        "Accept": "application/vnd.github.v3.raw",
    }
    curl_cmd = api.prepare_curl_cmd()
    api.add_curl_headers(curl_cmd, headers)
    curl_cmd.extend(
        ["--url", f"https://api.github.com/{cache_endpoint}", "-o", cache_path]
    )
    stdout, _, returncode = api.execute_curl(curl_cmd)
    if returncode != 0:
        log_err("WARNING: Unable to retrieve search index contents from GitHub API.")
        return


def normalize_keyword(keyword: str):
    """Normalizes capitalization, punctuation, and spacing of search keywords
    for better matching."""
    # TODO: Consider implementing fuzzywuzzy or some other fuzzy search method
    keyword = keyword.lower()
    replacements = {" ": "", ".": "", ",": "", "-": ""}
    for old, new in replacements.items():
        keyword = keyword.replace(old, new)

    return keyword


def get_search_results(keyword: str):
    """Return an array of recipe search results."""
    # Update and load local search index cache
    cache_path = os.path.expanduser("~/Library/AutoPkg/search_index.json")
    check_search_cache(cache_path)
    with open(cache_path, "rb") as openfile:
        search_index = json.load(openfile)

    # Perform the search against shortnames
    result_ids = []
    for candidate, identifiers in search_index["shortnames"].items():
        if normalize_keyword(keyword) in normalize_keyword(candidate):
            result_ids.extend(identifiers)

    # Perform the search against other recipe info
    searchable_keys = ("name", "munki_display_name", "jamf_display_name")
    for identifier, info in search_index["identifiers"].items():
        if info.get("deprecated"):
            continue
        for key in searchable_keys:
            if info.get(key):
                if normalize_keyword(keyword) in normalize_keyword(info[key]):
                    result_ids.append(identifier)
    if not result_ids:
        log_err("Nothing found.")
        return []
    result_ids = list(set(result_ids))

    # Collect result info into result list
    results = []
    for result_id in result_ids:
        repo = search_index["identifiers"][result_id]["repo"]
        if repo.startswith("autopkg/"):
            repo = repo.replace("autopkg/", "")
        result_item = {
            "Name": os.path.split(search_index["identifiers"][result_id]["path"])[-1],
            "Repo": repo,
            "Path": search_index["identifiers"][result_id]["path"],
        }
        results.append(result_item)
    return results


def search_recipes(argv: List[str]):
    """Search recipes in the AutoPkg org on GitHub using a cached index file."""
    verb = argv[1]
    parser = gen_common_parser()
    parser.set_usage(
        f"Usage: %prog {verb} [options] search_term\n"
        "Search for recipes on GitHub using a cached index file. The AutoPkg "
        "organization at github.com/autopkg\nis the canonical 'repository' of "
        "recipe repos, which is what is searched by\ndefault."
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
        "-u",
        "--user",
        default=DEFAULT_SEARCH_USER,
        help=(
            "Alternate GitHub user or organization whose repos to search. "
            f"Defaults to '{DEFAULT_SEARCH_USER}'."
        ),
    )
    parser.add_option(
        "-t",
        "--use-token",
        action="store_true",
        default=False,
        help=(
            "Used a public-scope GitHub token for a higher "
            "rate limit. This option is deprecated and no longer "
            "needed since AutoPkg 3.0+ uses a cached search index."
        ),
    )

    # Parse arguments
    (options, arguments) = common_parse(parser, argv)
    if len(arguments) < 1:
        log_err("No search query specified!")
        return 1

    if options.use_token:
        log_err("WARNING: Deprecated option '--use-token' provided, ignoring.")

    if options.user:
        # https://docs.github.com/en/enterprise-cloud@latest/admin/identity-and-access-management/managing-iam-for-your-enterprise/username-considerations-for-external-authentication#about-username-normalization
        if not re.match(r"^[A-Za-z0-9\-]+$", options.user):
            log_err(
                "WARNING: GitHub user/org names contain only alphanumeric characters and dashes."
            )
        options.user = re.sub(r"[^A-Za-z0-9\-]", "", options.user)
        keyword = quote_plus(arguments[0]).lower()
        url = (
            f"https://github.com/search?q={keyword}+org%3A"
            f"{options.user}+lang%3Axml+OR+lang%3Ayaml&type=code"
        )
        log(
            "'autopkg search' no longer directly searches GitHub users or orgs "
            "other than the autopkg org.\nHowever, this page may provide some "
            f"useful results:\n{url}"
        )
        return 0

    # Retrieve search results and print them, sorted by repo
    results = get_search_results(arguments[0])
    print_gh_search_results(results)
    log("To add a new recipe repo, use 'autopkg repo-add <repo name>'")

    # Warn if more results than the result limit
    results_limit = 100
    if len(results) > results_limit:
        print()
        log_err(
            f"WARNING: Search yielded more than {results_limit} results. Please try a "
            "more specific search term."
        )
        return 3
    return 0
