#!/usr/bin/python
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

from autopkglib import get_pref, log, log_err
from autopkglib.URLGetter import URLGetter

BASE_URL = "https://api.github.com"
TOKEN_LOCATION = os.path.expanduser("~/.autopkg_gh_token")


class GitHubSession(URLGetter):
    """Handles a session with the GitHub API"""

    def __init__(self, curl_path=None, curl_opts=None):
        super(GitHubSession, self).__init__()
        self.env = {}
        self.env["url"] = None
        if curl_path:
            self.env["CURL_PATH"] = curl_path
        if curl_opts:
            self.env["curl_opts"] = curl_opts
        token = get_pref("GITHUB_TOKEN")
        self.http_result_code = None
        if token:
            self.token = token
        elif os.path.exists(TOKEN_LOCATION):
            try:
                with open(TOKEN_LOCATION, "r") as tokenf:
                    self.token = tokenf.read()
            except IOError as err:
                log_err(
                    "Couldn't read token file at %s! Error: %s" % (TOKEN_LOCATION, err)
                )
                self.token = None
        else:
            self.token = None

    def setup_token(self):
        """Setup a GitHub OAuth token string. Will help to create one if necessary.
        The string will be stored in TOKEN_LOCATION and used again
        if it exists."""

        if not os.path.exists(TOKEN_LOCATION):
            log(
                """Create a new token in your GitHub settings page:

    https://github.com/settings/tokens

To save the token, paste it to the following prompt."""
            )

            token = raw_input("Token: ")
            if token:
                log("""Writing token file %s.""" % TOKEN_LOCATION)
                try:
                    with open(TOKEN_LOCATION, "w") as tokenf:
                        tokenf.write(token)
                    os.chmod(TOKEN_LOCATION, 0o600)
                except IOError as err:
                    log_err(
                        "Couldn't write token file at %s! Error: %s"
                        % (TOKEN_LOCATION, err)
                    )
            else:
                log("Skipping token file creation.")
        else:
            try:
                with open(TOKEN_LOCATION, "r") as tokenf:
                    token = tokenf.read()
            except IOError as err:
                log_err(
                    "Couldn't read token file at %s! Error: %s" % (TOKEN_LOCATION, err)
                )

            # TODO: validate token given we found one but haven't checked its
            # auth status

        self.token = token

    def prepare_curl_cmd(self, method, accept, headers, data, temp_content):
        """Assemble curl command and return it."""
        curl_cmd = [
            super(GitHubSession, self).curl_binary(),
            "--location",
            "--silent",
            "--show-error",
            "--fail",
            "--dump-header",
            "-",
        ]

        curl_cmd.extend(["-X", method])
        curl_cmd.extend(["--header", "%s: %s" % ("User-Agent", "AutoPkg")])
        curl_cmd.extend(["--header", "%s: %s" % ("Accept", accept)])

        # Pass the GitHub token as a header
        if self.token:
            curl_cmd.extend(
                ["--header", "%s: %s" % ("Authorization", "token %s" % self.token)]
            )

        super(GitHubSession, self).add_curl_common_opts(curl_cmd)

        # Additional headers if defined
        if headers:
            for header, value in headers.items():
                curl_cmd.extend(["--header", "%s: %s" % (header, value)])

        # Set the data header if defined
        if data:
            data = json.dumps(data)
            curl_cmd.extend(["-d", data, "--header", "Content-Type: application/json"])

        # Final argument to curl is the URL
        curl_cmd.extend(["--url", self.env["url"]])
        curl_cmd.extend(["--output", temp_content])

        return curl_cmd

    def download(self, curl_cmd):
        """Downloads file using curl and returns raw headers."""

        p_stdout, p_stderr, retcode = super(GitHubSession, self).execute_curl(curl_cmd)

        if retcode:  # Non-zero exit code from curl => problem with download
            curl_err = super(GitHubSession, self).parse_curl_error(p_stderr)
            log_err(
                "Curl failure: Could not retrieve URL %s: %s"
                % (self.env["url"], curl_err)
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

    def call_api(
        self,
        endpoint,
        method="GET",
        query=None,
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
        self.env["url"] = BASE_URL + endpoint
        if query:
            self.env["url"] += "?" + query

        temp_content = tempfile.NamedTemporaryFile().name
        # Prepare curl command
        curl_cmd = self.prepare_curl_cmd(method, accept, headers, data, temp_content)

        # Execute curl command and parse headers
        raw_header = self.download(curl_cmd)
        header = {}
        super(GitHubSession, self).clear_header(header)
        super(GitHubSession, self).parse_headers(raw_header, header)
        if header["http_result_code"] != "000":
            self.http_result_code = int(header["http_result_code"])

        try:
            with open(temp_content) as f:
                resp_data = json.load(f)
        except:
            resp_data = None

        return (resp_data, self.http_result_code)
