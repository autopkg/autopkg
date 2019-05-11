#!/usr/bin/python
#
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

from __future__ import print_function

import json
import os
import re
import subprocess
import sys

from autopkglib import curl_cmd, get_pref

BASE_URL = "https://api.github.com"
TOKEN_LOCATION = os.path.expanduser("~/.autopkg_gh_token")


class GitHubSession(object):
    """Handles a session with the GitHub API"""
    def __init__(self):
        token = get_pref('GITHUB_TOKEN')
        if token:
            self.token = token
        elif os.path.exists(TOKEN_LOCATION):
            try:
                with open(TOKEN_LOCATION, "r") as tokenf:
                    self.token = tokenf.read()
            except IOError as err:
                print(
                    "Couldn't read token file at %s! Error: %s"
                    % (TOKEN_LOCATION, err), file=sys.stderr)
                self.token = None
        else:
            self.token = None

    def setup_token(self):
        """Setup a GitHub OAuth token string. Will help to create one if necessary.
        The string will be stored in TOKEN_LOCATION and used again
        if it exists."""

        if not os.path.exists(TOKEN_LOCATION):
            print("""Create a new token in your GitHub settings page:

    https://github.com/settings/tokens

To save the token, paste it to the following prompt.""")

            token = raw_input("Token: ")
            if token:
                print("""Writing token file %s.""" % TOKEN_LOCATION)
                try:
                    with open(TOKEN_LOCATION, "w") as tokenf:
                        tokenf.write(token)
                    os.chmod(TOKEN_LOCATION, 0o600)
                except IOError as err:
                    print(
                        "Couldn't write token file at %s! Error: %s"
                        % (TOKEN_LOCATION, err), file=sys.stderr)
            else:
                print("Skipping token file creation.", file=sys.stderr)
        else:
            try:
                with open(TOKEN_LOCATION, "r") as tokenf:
                    token = tokenf.read()
            except IOError as err:
                print(
                    "Couldn't read token file at %s! Error: %s"
                    % (TOKEN_LOCATION, err), file=sys.stderr)

            # TODO: validate token given we found one but haven't checked its
            # auth status

        self.token = token

    def call_api(self, endpoint, method="GET", query=None, data=None,
                 headers=None, accept="application/vnd.github.v3+json"):
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
        url = BASE_URL + endpoint
        if query:
            url += "?" + query

        try:
            # Compose the curl command
            curl_path = curl_cmd()
            if not curl_path:
                return (None, None)
            cmd = [
                curl_path,
                '--location',
                '--silent',
                '--show-error',
                '--fail',
                '--dump-header', '-'
            ]
            cmd.extend(['-X', method])
            cmd.extend(['--header', '%s: %s' % ("User-Agent", "AutoPkg")])
            cmd.extend(['--header', '%s: %s' % ("Accept", accept)])

            # Pass the GitHub token as a header
            if self.token:
                cmd.extend(['--header', '%s: %s' % ("Authorization", "token %s" % self.token)])

            # Additional headers if defined
            if headers:
                for header, value in headers.items():
                    cmd.extend(['--header', '%s: %s' % (header, value)])

            # Set the data header if defined
            if data:
                data = json.dumps(data)
                cmd.extend(['-d', data, '--header', 'Content-Type: application/json'])

            # Final argument to curl is the URL
            cmd.append(url)

            # Start the curl process
            proc = subprocess.Popen(
                cmd,
                shell=False,
                bufsize=1,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            header = {}
            header['http_result_code'] = '000'
            header['http_result_description'] = ''
            donewithheaders = False
            maxheaders = 15

            page_content = ""

            # Parse the headers and the JSON from curl output
            while True:
                info = proc.stdout.readline()
                if not donewithheaders:
                    info = info.strip('\r\n')
                    if info:
                        if info.startswith('HTTP/'):
                            part = info.split(None, 2)
                            header['http_result_code'] = part[1]
                            try:
                                header['http_result_description'] = part[2]
                            except IndexError:
                                pass
                        elif ': ' in info:
                            part = info.split(None, 1)
                            fieldname = part[0].rstrip(':').lower()
                            try:
                                header[fieldname] = part[1]
                            except IndexError:
                                pass
                    else:
                        donewithheaders = True
                else:
                    page_content += info

                if (proc.poll() is not None):
                    # For small download files curl may exit before all headers
                    # have been parsed, don't immediately exit.
                    maxheaders -= 1
                    if donewithheaders or maxheaders <= 0:
                        break

            # All curl output should now be parsed
            retcode = proc.poll()
            if retcode:
                curlerr = ''
                try:
                    curlerr = proc.stderr.read().rstrip('\n')
                    curlerr = curlerr.split(None, 2)[2]
                except IndexError:
                    pass
                if retcode == 22:
                    # 22 means any 400 series return code. Note: header seems not to
                    # be dumped to STDOUT for immediate failures. Hence
                    # http_result_code is likely blank/000. Read it from stderr.
                    if re.search(r'URL returned error: [0-9]+', curlerr):
                        m = re.match(r".* (?P<status_code>\d+) .*", curlerr)
                        if m.group('status_code'):
                            header['http_result_code'] = m.group('status_code')
                print(
                    'Could not retrieve URL %s: %s' % (url, curlerr),
                    file=sys.stderr
                )

            if page_content:
                resp_data = json.loads(page_content)
            else:
                resp_data = None

        except OSError:
            print('Could not retrieve URL: %s' % url, file=sys.stderr)
            resp_data = None

        http_result_code = int(header.get('http_result_code'))
        return (resp_data, http_result_code)
