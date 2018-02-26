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

import json
import os
import sys
import urllib2
import subprocess
from autopkglib import curl_cmd

from base64 import b64encode
from getpass import getpass
from pprint import pprint

BASE_URL = "https://api.github.com"
TOKEN_LOCATION = os.path.expanduser("~/.autopkg_gh_token")


class RequestWithMethod(urllib2.Request):
    """Custom Request class that can accept arbitrary methods besides
    GET/POST"""
    # http://benjamin.smedbergs.us/blog/2008-10-21/
    #        putting-and-deleteing-in-python-urllib2/
    def __init__(self, method, *args, **kwargs):
        self._method = method
        urllib2.Request.__init__(self, *args, **kwargs)

    def get_method(self):
        return self._method


class GitHubSession(object):
    """Handles a session with the GitHub API"""
    def __init__(self):
        self.token = None

    def setup_token(self):
        """Return a GitHub OAuth token string. Will create one if necessary.
        The string will be stored in TOKEN_LOCATION and used again
        if it exists."""

        #TODO: - support defining alternate scopes
        #      - deal with case of an existing token with the same note
        if not os.path.exists(TOKEN_LOCATION):
            print """You will now be asked to enter credentials to a GitHub
account in order to create an API token. This token has only
a 'public' scope, meaning it cannot be used to retrieve
personal information from your account, or push to any repos
you may have access to. You can verify this token within your
profile page at https://github.com/settings/tokens and
revoke it at any time. This token will be stored in your user's
home folder at %s.""" % TOKEN_LOCATION
            username = raw_input("Username: ")
            password = getpass("Password: ")
            auth = b64encode(username + ":" + password)

            # https://developer.github.com/v3/oauth/#scopes
            req = urllib2.Request(BASE_URL + "/authorizations")
            req.add_header("Authorization", "Basic %s" % auth)
            json_resp = urllib2.urlopen(req)
            data = json.load(json_resp)

            req_post = {"note": "AutoPkg CLI"}
            req_json = json.dumps(req_post)
            create_resp = urllib2.urlopen(req, req_json)
            data = json.load(create_resp)

            token = data["token"]
            try:
                with open(TOKEN_LOCATION, "w") as tokenf:
                    tokenf.write(token)
                os.chmod(TOKEN_LOCATION, 0600)
            except IOError as err:
                print >> sys.stderr, (
                    "Couldn't write token file at %s! Error: %s"
                    % (TOKEN_LOCATION, err))
        else:
            try:
                with open(TOKEN_LOCATION, "r") as tokenf:
                    token = tokenf.read()
            except IOError as err:
                print >> sys.stderr, (
                    "Couldn't read token file at %s! Error: %s"
                    % (TOKEN_LOCATION, err))

            # TODO: validate token given we found one but haven't checked its
            # auth status

        self.token = token


    def call_api(self, endpoint, method="GET", query=None, data=None,
                 headers=None, accept="application/vnd.github.v3+json"):
        """Return a serialized JSON response from a call to a GitHub API endpoint.
        Certain APIs return no JSON result and so the response might be None.

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
                return None
            cmd = [curl_path, '--location']
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
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            (content, stderr) = proc.communicate()
            if content:
                resp_data = json.loads(content)
            else:
                resp_data = None
            if proc.returncode:
                print >> sys.stderr, 'Could not retrieve URL %s: %s' % (url, stderr)
                resp_data = None
        except OSError:
            print >> sys.stderr, 'Could not retrieve URL: %s' % url
            resp_data = None

        return resp_data

