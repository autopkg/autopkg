#!/usr/local/autopkg/python
#
# Refactoring 2018 Michal Moravec
# Copyright 2014 Timothy Sutton
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
"""Routines for working with the GitHub API"""

import json
import os
import re
import tempfile
from typing import Any, List

from autopkglib import get_pref, log, log_err
from autopkglib.URLGetter import URLGetter

BASE_URL = "https://api.github.com"
TOKEN_LOCATION = os.path.expanduser("~/.autopkg_gh_token")
DEFAULT_SEARCH_USER = "autopkg"


class GitHubSession(URLGetter):
    """Handles a session with the GitHub API"""

    def __init__(
        self, curl_path=None, curl_opts=None, github_url=None, token_path=TOKEN_LOCATION
    ):
        super().__init__()
        self.env = {}
        self.env["url"] = None
        if curl_path:
            self.env["CURL_PATH"] = curl_path
        if curl_opts:
            self.env["curl_opts"] = curl_opts
        if github_url:
            self.url = github_url
        else:
            self.url = BASE_URL
        self.http_result_code = None
        if token_path.startswith("~"):
            token_abspath = os.path.expanduser(token_path)
        else:
            token_abspath = token_path
        self.token = self._get_token(token_path=token_abspath)

    def _get_token(self, token_path: str = TOKEN_LOCATION) -> str | None:
        """Reads token from preferences or provided token path.
        Defaults to TOKEN_LOCATION for the token path.
        Otherwise returns None.
        """
        token = get_pref("GITHUB_TOKEN")
        if not token and os.path.exists(token_path):
            try:
                with open(token_path) as tokenf:
                    token = tokenf.read().strip()
            except OSError as err:
                log_err(f"Couldn't read token file at {token_path}! Error: {err}")
                token = None
        # TODO: validate token given we found one but haven't checked its
        # auth status
        return token

    def get_or_setup_token(self) -> str:
        """Setup a GitHub OAuth token string. Will help to create one if necessary.
        The string will be stored in TOKEN_LOCATION and used again
        if it exists."""

        token = self._get_token()
        if not token and not os.path.exists(TOKEN_LOCATION):
            print(
                """Create a new token in your GitHub settings page:

    https://github.com/settings/tokens

To save the token, paste it to the following prompt."""
            )

            token = input("Token: ")
            if token:
                log(f"Writing token file {TOKEN_LOCATION}.")
                try:
                    with open(TOKEN_LOCATION, "w") as tokenf:
                        tokenf.write(token)
                    os.chmod(TOKEN_LOCATION, 0o600)
                except OSError as err:
                    log_err(
                        f"Couldn't write token file at {TOKEN_LOCATION}! Error: {err}"
                    )
            else:
                log("Skipping token file creation.")

        self.token = token
        return token

    def prepare_curl_cmd(
        self, method, accept, headers, data, temp_content
    ) -> list[str]:
        """Assemble curl command and return it."""
        curl_cmd = [
            self.curl_binary(),
            "--location",
            "--silent",
            "--show-error",
            "--fail",
            "--dump-header",
            "-",
        ]

        curl_cmd.extend(["-X", method])
        curl_cmd.extend(["--header", "User-Agent: AutoPkg"])
        curl_cmd.extend(["--header", f"Accept: {accept}"])

        # Pass the GitHub token as a header
        if self.token:
            curl_cmd.extend(["--header", f"Authorization: token {self.token}"])

        self.add_curl_common_opts(curl_cmd)

        # Additional headers if defined
        if headers:
            for header, value in headers.items():
                curl_cmd.extend(["--header", f"{header}: {value}"])

        # Set the data header if defined
        if data:
            data = json.dumps(data)
            curl_cmd.extend(["-d", data, "--header", "Content-Type: application/json"])

        # Final argument to curl is the URL
        curl_cmd.extend(["--url", self.env["url"]])
        curl_cmd.extend(["--output", temp_content])

        return curl_cmd

    def download_with_curl(self, curl_cmd):
        """Download file using curl and return raw headers."""

        p_stdout, p_stderr, retcode = self.execute_curl(curl_cmd)

        if retcode:  # Non-zero exit code from curl => problem with download
            curl_err = self.parse_curl_error(p_stderr)
            log_err(
                f"Curl failure: Could not retrieve URL {self.env['url']}: {curl_err}"
            )

            if retcode == 22:
                # 22 means any 400 series return code. Note: header seems not to
                # be dumped to STDOUT for immediate failures. Hence
                # http_result_code is likely blank/000. Read it from stderr.
                if re.search(r"URL returned error: [0-9]+", p_stderr):
                    m = re.match(r".* (?P<status_code>\d+) .*", p_stderr)
                    if m.group("status_code"):
                        self.http_result_code = m.group("status_code")

        return p_stdout

    def search_for_name(
        self,
        name: str,
        path_only: bool = False,
        user: str = DEFAULT_SEARCH_USER,
        use_token: bool = False,
        results_limit: int = 100,
    ) -> list[dict]:
        """Search GitHub for results for a given name.

        Note: This method now uses a cached search index instead of the GitHub
        Code Search API. The user, use_token, and results_limit parameters are
        deprecated but kept for backward compatibility.
        """
        # Import here to avoid circular dependency
        from autopkgcmd.searchcmd import get_search_results

        # Warn if non-default user is specified
        if user != DEFAULT_SEARCH_USER:
            log(
                f"WARNING: Searching non-autopkg users/orgs ('{user}') is "
                "no longer supported. Searching the autopkg org only."
            )

        # Warn if token flag is used (no longer needed with cached index)
        if use_token:
            log("WARNING: --use-token flag is deprecated and no longer " "needed.")

        # Suppress unused parameter warning - kept for backward compatibility
        _ = results_limit

        # Get results from cached index
        results = get_search_results(name, path_only=path_only)

        # Return empty list if no results
        # (get_search_results already logs "Nothing found")
        if not results:
            return []

        # Transform results to maintain backward compatibility with old format
        # Old format had: name, path, repository{name, full_name}, html_url
        # New format has: Name, Repo, Path
        results_items = []
        for item in results:
            # Build a compatible result structure
            repo_name = item["Repo"]
            # Add back "autopkg/" prefix if it was stripped
            if "/" not in repo_name:
                full_repo = f"autopkg/{repo_name}"
            else:
                full_repo = repo_name

            result_item = {
                "name": item["Name"],
                "path": item["Path"],
                "repository": {
                    "name": repo_name.split("/")[-1],  # Just the repo name
                    "full_name": full_repo,  # owner/repo
                },
                "html_url": (
                    f"https://github.com/{full_repo}/blob/master/" f"{item['Path']}"
                ),
            }
            results_items.append(result_item)

        return results_items

    def code_search(self, query: str, use_token: bool = False) -> dict | None:
        """Search GitHub code repos.

        DEPRECATED as of AutoPkg 2.9.0 in favor of cached search index. This function
        will be removed in a future release."""
        if use_token:
            _ = self.get_or_setup_token()
        # Do the search, including text match metadata
        (results, code) = self.call_api(
            "/search/code",
            query=query,
            accept="application/vnd.github.v3.text-match+json",
        )

        if code == 403:
            log_err(
                "You've probably hit the GitHub's search rate limit, officially 5 "
                "requests per minute.\n"
            )
            if results:
                log_err("Server response follows:\n")
                log_err(results.get("message", None))
                log_err(results.get("documentation_url", None))

            return None
        if results is None or code is None:
            log_err("A GitHub API error occurred!")
            return None
        return results

    def call_api(
        self,
        endpoint: str,
        method: str = "GET",
        query: str | None = None,
        data=None,
        headers=None,
        accept="application/vnd.github.v3+json",
    ) -> tuple[Any, int]:
        """Return a tuple of a serialized JSON response and HTTP status code
        from a call to a GitHub API endpoint. Certain APIs return no JSON
        result and so the first item in the tuple (the response) will be None.

        endpoint: REST endpoint, beginning with a forward-slash
        method: optional alternate HTTP method to use other than GET
        query: optional additional query to include with URI (passed directly)
        data: optional dict that will be sent as JSON with request
        headers: optional dict of additional headers to send with request
        accept: optional Accept media type for exceptional APIs (like release
                assets)."""

        # Compose the URL
        self.env["url"] = self.url + endpoint
        if query:
            self.env["url"] += "?" + query

        temp_content = tempfile.NamedTemporaryFile().name
        # Prepare curl command
        curl_cmd = self.prepare_curl_cmd(method, accept, headers, data, temp_content)

        # Execute curl command and parse headers
        raw_headers = self.download_with_curl(curl_cmd)
        header = self.parse_headers(raw_headers)
        if header["http_result_code"] != "000":
            self.http_result_code = int(header["http_result_code"])

        resp_data = None
        try:
            with open(temp_content) as f:
                resp_data = json.load(f)
        except UnicodeDecodeError:
            with open(temp_content, "rb") as f:
                resp_data = json.load(f)
        except json.JSONDecodeError as e:
            self.output(f"JSONDecodeError: {e}")

        return (resp_data, self.http_result_code)


def get_table_row(row_items, col_widths, header=False):
    """Format table row content (e.g. search results) with proper spacing for output.

    Args:
        row_items: Iterable of cell content (strings or values convertible to strings)
        col_widths: List of integers specifying width for each column
        header: If True, appends a separator line after the row for Markdown headers

    Returns:
        String representing a formatted table row with proper spacing.
        If header=True, includes a separator line with dashes.
    """
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


def print_gh_search_results(results: List):
    """Pretty print our GitHub search results."""
    if not results:
        log_err("Nothing found.")
        return

    # Limit results to print
    results_limit = 100
    limited_results = results[:results_limit]

    col_widths = [
        max([len(x[k]) for x in limited_results] + [len(k)])
        for k in limited_results[0].keys()
    ]
    print()
    print(get_table_row(limited_results[0].keys(), col_widths, header=True))
    for result_item in sorted(limited_results, key=lambda x: x["Repo"].lower()):
        print(get_table_row(result_item.values(), col_widths))
    print()
    print("To add a new recipe repo, use `autopkg repo-add <repo name>`")
    print()
    print(
        "If you don't see the recipe you're looking for, try searching "
        "https://autopkgweb.com/ (maintained by @jannheider)."
    )

    # Warn if we have too many results (likely not helpful)
    if len(results) > results_limit:
        print()
        log_err(
            f"WARNING: Only showing first {results_limit} out of {len(results)} "
            "total results. Please try a more specific search term."
        )
