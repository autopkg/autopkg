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

from typing import List
from urllib.parse import quote

from autopkgcmd.opts import common_parse, gen_common_parser
from autopkglib.common import log_err
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
