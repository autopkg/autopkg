#!/usr/local/autopkg/python

import json
import subprocess
import os
import sys
import certifi
import ssl


import urllib.error
import urllib.parse
import urllib.request


class GitHubAPIError(BaseException):
    """Base error for GitHub API interactions"""

    pass


def api_call(
    endpoint,
    token,
    baseurl="https://api.github.com",
    data=None,
    json_data=True,
    additional_headers=None,
):
    """endpoint: of the form '/repos/username/repo/etc'.
    token: the API token for Authorization.
    baseurl: the base URL for the API endpoint. for asset uploads this ends up
             needing to be overridden.
    data: takes a standard python object and serializes to json for a POST,
          unless json_data is False.
    additional_headers: a dict of additional headers for the API call"""
    if data and json_data:
        data = json.dumps(data, ensure_ascii=False)
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {token}",
    }
    if additional_headers:
        for header, value in list(additional_headers.items()):
            headers[header] = value

    req = urllib.request.Request(baseurl + endpoint, headers=headers)
    try:
        context = ssl.SSLContext()
        context.load_verify_locations(certifi.where())
        results = urllib.request.urlopen(req, data=data, context=context)
    except urllib.error.HTTPError as err:
        print("HTTP error making API call!", file=sys.stderr)
        print(err, file=sys.stderr)
        error_json = err.read()
        error = json.loads(error_json)
        print(f"API message: {error['message']}", file=sys.stderr)
        sys.exit(1)
    if results:
        try:
            parsed = json.loads(results.read())
            return parsed
        except BaseException as err:
            print(err, file=sys.stderr)
            raise GitHubAPIError
    return None


def main():
    token = None
    username = "nmcspadden"
    page = 1
    per_page = 100
    repos = []

    if os.path.exists(os.path.expanduser("~/.autopkg_gh_token")):
        with open(os.path.expanduser("~/.autopkg_gh_token"), "r") as f:
            token = f.read().strip()
            print(token)
    if not token:
        sys.exit("Invalid token")

    # ensure our OAuth token works before we go any further
    print("** Verifying OAuth token")
    api_call(f"/users/{username}", token)

    print("** Querying repos")
    while True:
        data = {"page": page, "per_page": per_page}
        encoded_data = urllib.parse.urlencode(data)
        response = api_call("/orgs/autopkg/repos" + "?" + encoded_data, token)
        if not response:
            break

        print(f"** Processing page {page} of repos...")
        repos.extend([x["full_name"] for x in response])
        page += 1

    # Ignore autopkg itself
    repos.remove("autopkg/autopkg")
    for repo in repos:
        dirname = repo.replace("autopkg/", "")
        if not os.path.isdir(dirname):
            print(dirname)


if __name__ == "__main__":
    main()
