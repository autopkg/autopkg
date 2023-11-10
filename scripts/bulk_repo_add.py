#!/usr/local/autopkg/python

import argparse
import getpass
import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

import certifi


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


def output(quiet, msg):
    """Print a message unless in quiet mode."""
    if not quiet:
        print(msg)


def repo_add(repo):
    """Add a repo using 'repo-add'."""
    cmd = ["/usr/local/bin/autopkg", "repo-add", repo]
    subprocess.run(cmd, check=False, capture_output=True)


def get_repo_list(prefs):
    """Get list of all repos in <name-recipes> form."""
    cmd = ["/usr/local/bin/autopkg", "repo-list"]
    if prefs:
        cmd.extend(["--prefs", prefs])
    result = subprocess.run(cmd, check=False, capture_output=True)
    full_repo_list = result.stdout.strip().splitlines()
    repo_list = [x.split(b" ")[0].split(b".")[-1].decode() for x in full_repo_list]
    return repo_list


def main():
    """
    Lists (and repo-adds) all recipe repo in the autopkg org.

    Requirements:

    API token:
    You'll need an API OAuth token with push access to the repo. You can create a
    Personal Access Token in your user's Account Settings:
    https://github.com/settings/tokens
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t",
        "--token",
        help="GitHub API OAuth token. Defaults to reading from ~/.autopkg_gh_token.",
    )
    parser.add_argument(
        "-u",
        "--username",
        help="Username to validate token. Defaults to current logged in user.",
    )
    parser.add_argument(
        "-a", "--add", help=("Use 'repo-add' to add all found recipe repos.")
    )
    parser.add_argument(
        "-i",
        "--ignore-existing",
        help=("Show/add repos that already exist on disk."),
        action="store_true",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        help=("Only output directory repo names, no flavor text."),
        action="store_true",
    )
    parser.add_argument("-p", "--prefs", help=("Pass in a preferences file."))
    args = parser.parse_args()

    token = args.token
    if not args.token:
        if os.path.exists(os.path.expanduser("~/.autopkg_gh_token")):
            with open(os.path.expanduser("~/.autopkg_gh_token"), "r") as f:
                token = f.read().strip()
        if not token:
            sys.exit("Invalid token")
    username = getpass.getuser()
    if args.username:
        username = args.username
    page = 1
    per_page = 100
    repos = []

    # ensure our OAuth token works before we go any further
    output(args.quiet, "** Verifying OAuth token")
    api_call(f"/users/{username}", token)

    output(args.quiet, "** Gathering current repo list")
    repo_list = get_repo_list(args.prefs)
    output(args.quiet, "** Querying repos")
    while True:
        data = {"page": page, "per_page": per_page}
        encoded_data = urllib.parse.urlencode(data)
        response = api_call("/orgs/autopkg/repos" + "?" + encoded_data, token)
        if not response:
            break

        output(args.quiet, f"** Processing page {page} of repos...")
        repos.extend([x["full_name"] for x in response])
        page += 1

    # Ignore autopkg itself
    repos.remove("autopkg/autopkg")
    for repo in repos:
        dirname = repo.replace("autopkg/", "")
        if dirname in repo_list and not args.ignore_existing:
            # Ignore ones we've already got
            continue
        print(dirname)
        if args.add:
            repo_add(dirname)


if __name__ == "__main__":
    main()
