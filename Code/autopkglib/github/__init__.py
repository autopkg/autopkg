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
from typing import List, Optional

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
        super(GitHubSession, self).__init__()
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

    def _get_token(self, token_path: str = TOKEN_LOCATION) -> Optional[str]:
        """Reads token from perferences or TOKEN_LOCATION.
            Otherwise returns None.
        """
        token_location = token_path
        token = get_pref("GITHUB_TOKEN")
        if not token and os.path.exists(token_location):
            try:
                with open(token_location, "r") as tokenf:
                    token = tokenf.read()
            except OSError as err:
                log_err(f"Couldn't read token file at {token_location}! Error: {err}")
                token = None
        # TODO: validate token given we found one but haven't checked its
        # auth status
        return token
    
    def get_or_setup_token(self):
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
    ) -> List[str]:
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
    ):
        """Search GitHub for results for a given name."""

        query = f"q={name}+extension:recipe+user:{user}"
        if path_only:
            query += "+in:path,filepath"
        else:
            query += "+in:path,file"
        query += f"&per_page={results_limit}"

        results = self.code_search(query, use_token=use_token)

        if not results or not results.get("total_count"):
            log("Nothing found.")
            return []

        results_items = results["items"]

        if not results_items:
            log("Nothing found.")
            return []
        return results_items

    def code_search(self, query: str, use_token: bool = False):
        """Search GitHub code repos"""
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
        query: str = None,
        data=None,
        headers=None,
        accept="application/vnd.github.v3+json",
    ):
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

        try:
            with open(temp_content) as f:
                resp_data = json.load(f)
        except json.JSONDecodeError:
            resp_data = None

        return (resp_data, self.http_result_code)


def print_gh_search_results(results_items):
    """Pretty print our GitHub search results"""
    if not results_items:
        return
    column_spacer = 4
    max_name_length = max([len(r["name"]) for r in results_items]) + column_spacer
    max_repo_length = (
        max([len(r["repository"]["name"]) for r in results_items]) + column_spacer
    )
    spacers = (max_name_length, max_repo_length)

    print()
    format_str = "%-{}s %-{}s %-40s".format(*spacers)
    print(format_str % ("Name", "Repo", "Path"))
    print(format_str % ("----", "----", "----"))
    results_items.sort(key=lambda x: x["repository"]["name"])
    for result in results_items:
        repo = result["repository"]
        name = result["name"]
        path = result["path"]
        if repo["full_name"].startswith("autopkg"):
            repo_name = repo["name"]
        else:
            repo_name = repo["full_name"]
        print(format_str % (name, repo_name, path))
