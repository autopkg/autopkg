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
from urllib.parse import quote_plus

from autopkgcmd.opts import common_parse, gen_common_parser
from autopkglib import ProcessorError, log, log_err
from autopkglib.github import (
    DEFAULT_SEARCH_USER,
    GitHubSession,
    print_gh_search_results,
)
from autopkglib.URLGetter import URLGetter

# Search index location in autopkg/index repo
SEARCH_INDEX_PATH = "v1/index.json"
SEARCH_INDEX_BRANCH = "main"


def handle_cache_error(cache_path: str, reason: str) -> None:
    """Handle errors when updating search cache.

    Args:
        cache_path: Path to the cached index file
        reason: The reason for the error (will be appended with context)

    Raises:
        ProcessorError: If no cache exists and download fails
    """
    if os.path.isfile(cache_path):
        log_err(f"WARNING: {reason}. Using cached version.")
        return

    # Try raw URL only if we don't have etag (never got metadata from API)
    if not os.path.isfile(cache_path + ".etag"):
        log("GitHub API unavailable, attempting download from raw URL...")
        raw_url = (
            f"https://raw.githubusercontent.com/autopkg/index/"
            f"{SEARCH_INDEX_BRANCH}/{SEARCH_INDEX_PATH}"
        )
        try:
            url = URLGetter()
            url.download_to_file(raw_url, cache_path)
            # Write a placeholder etag to prevent re-downloading raw URL
            with open(cache_path + ".etag", "w", encoding="utf-8") as openfile:
                openfile.write("Search index temporarily sourced from raw GitHub URL.")
            log("Successfully downloaded search index from raw URL.")
            return
        except ProcessorError:
            pass  # Fall through to error below

    error_msg = f"{reason}, and no cached index available."
    log_err(f"ERROR: {error_msg}")
    raise ProcessorError(error_msg)


def check_search_cache(cache_path: str) -> None:
    """Update local search index, if it's missing or out of date."""

    # Use URLGetter to interact with GitHub API
    api = URLGetter()

    # Use GitHub token if one exists
    token = GitHubSession().token
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    # Retrieve metadata about search index file from GitHub API
    cache_endpoint = (
        f"repos/autopkg/index/contents/{SEARCH_INDEX_PATH}?ref={SEARCH_INDEX_BRANCH}"
    )
    headers["Accept"] = "application/vnd.github.v3+json"
    curl_cmd = api.prepare_curl_cmd()
    api.add_curl_headers(curl_cmd, headers)
    curl_cmd.extend(["--url", f"https://api.github.com/{cache_endpoint}"])

    try:
        stdout, _, returncode = api.execute_curl(curl_cmd)
    except ProcessorError:
        handle_cache_error(cache_path, "Unable to check for search index updates")
        return

    if returncode != 0:
        handle_cache_error(
            cache_path, "Unable to retrieve search index metadata from GitHub API"
        )
        return

    try:
        cache_meta = json.loads(stdout)
    except json.JSONDecodeError:
        handle_cache_error(cache_path, "Invalid response from GitHub API")
        return

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
    headers["Accept"] = "application/vnd.github.v3.raw"
    curl_cmd = api.prepare_curl_cmd()
    api.add_curl_headers(curl_cmd, headers)
    curl_cmd.extend(
        ["--url", f"https://api.github.com/{cache_endpoint}", "-o", cache_path]
    )

    try:
        stdout, _, returncode = api.execute_curl(curl_cmd)
    except ProcessorError:
        handle_cache_error(cache_path, "Unable to download updated search index")
        return

    if returncode != 0:
        handle_cache_error(
            cache_path, "Unable to retrieve search index contents from GitHub API"
        )
        return


def normalize_keyword(keyword: str) -> str:
    """Normalizes capitalization, punctuation, and spacing of search keywords
    for better matching."""
    # TODO: Consider implementing fuzzywuzzy or some other fuzzy search method
    keyword = keyword.lower()
    replacements = {" ": "", ".": "", ",": "", "-": ""}
    for old, new in replacements.items():
        keyword = keyword.replace(old, new)

    return keyword


def get_search_results(keyword: str, path_only: bool = False) -> list[dict]:
    """Return an array of recipe search results."""
    from autopkglib import get_pref

    # Update and load local search index cache
    cache_dir = get_pref("CACHE_DIR") or os.path.expanduser("~/Library/AutoPkg/Cache")
    cache_path = os.path.join(cache_dir, "search_index.json")
    check_search_cache(cache_path)
    with open(cache_path, "rb") as openfile:
        search_index = json.load(openfile)

    # Perform the search against shortnames
    result_ids = []
    for candidate, identifiers in search_index["shortnames"].items():
        if normalize_keyword(keyword) in normalize_keyword(candidate):
            result_ids.extend(identifiers)

    # Perform the search against other recipe info
    if path_only:
        searchable_keys: tuple[str, ...] = ("path",)
    else:
        searchable_keys: tuple[str, ...] = (
            "name",
            "app_display_name",
        )
    for identifier, info in search_index["identifiers"].items():
        for key in searchable_keys:
            if info.get(key):
                if normalize_keyword(keyword) in normalize_keyword(info[key]):
                    result_ids.append(identifier)
    if not result_ids:
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


def search_recipes(argv: list[str]) -> int:
    """Search recipes in the AutoPkg org on GitHub using a cached index file."""
    verb = argv[1]
    parser = gen_common_parser()
    parser.set_usage(
        f"Usage: %prog {verb} [options] search_term\n"
        "Search for AutoPkg recipes hosted in the AutoPkg organization at\n"
        "github.com/autopkg. Uses an index that is updated every 4 hours and\n"
        "cached locally. Search term is matched against recipe names, app\n"
        "names, and paths. Deprecated recipes are omitted from results."
    )
    parser.add_option(
        "-p",
        "--path-only",
        action="store_true",
        default=False,
        help=(
            "Restrict search results to the recipe's path only. Useful for\n"
            "finding recipes in specific directories or repositories."
        ),
    )
    parser.add_option(
        "-t",
        "--use-token",
        action="store_true",
        default=False,
        help=(
            "Deprecated. GitHub personal access token will be used\n"
            "automatically if one is provided. See this wiki page for details:\n"
            "https://github.com/autopkg/autopkg/wiki/FAQ#how-do-i-provide-a-github-personal-access-token-to-autopkg"
        ),
    )
    parser.add_option(
        "-u",
        "--user",
        default=DEFAULT_SEARCH_USER,
        help=(
            "Deprecated. GitHub user or organization to search, other than the\n"
            "default 'autopkg' org. As of AutoPkg 2.9.0, this no longer\n"
            "performs direct searches; instead, it provides a GitHub search URL."
        ),
    )

    # Parse arguments
    (options, arguments) = common_parse(parser, argv)
    if len(arguments) < 1 or not arguments[0].strip():
        log_err("ERROR: No search query specified!")
        return 1

    if options.use_token:
        log_err("WARNING: Deprecated option '--use-token' provided, ignoring.")

    if options.user != "autopkg":
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
    # (print_gh_search_results now includes autopkgweb recommendation and warnings)
    results = get_search_results(arguments[0], path_only=options.path_only)
    print_gh_search_results(results)

    return 0
