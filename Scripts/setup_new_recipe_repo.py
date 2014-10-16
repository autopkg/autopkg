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
#
# Utility script to handle duplicating existing repos to an organization,
# and creating a team with access to the new repo.
"""Utility to duplicate an AutoPkg recipe repo on GitHub to an organization and
create a new team specifically for the duplicate repo, and assign the source
repo author to this team."""

import json
import optparse
import os
import subprocess
import sys
import urllib2

from pprint import pprint
from tempfile import mkdtemp

BASE_URL = "https://api.github.com"
TOKEN = None


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


def call_api(endpoint, method="GET", query=None, data=None, headers=None,
             accept="application/vnd.github.v3+json"):
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

    url = BASE_URL + endpoint
    if query:
        url += "?" + query
    if data:
        data = json.dumps(data)

    # Setup custom request and its headers
    req = RequestWithMethod(method, url)
    req.add_header("User-Agent", "AutoPkg")
    req.add_header("Accept", accept)
    req.add_header("Authorization", "token %s" % TOKEN)
    if headers:
        for key, value in headers.items():
            req.add_header(key, value)

    try:
        urlfd = urllib2.urlopen(req, data=data)
        status = urlfd.getcode()
        response = urlfd.read()
        if response:
            resp_data = json.loads(response)
        else:
            resp_data = None
    except urllib2.HTTPError as err:
        status = err.code
        print >> sys.stderr, "API error: %s" % err
        try:
            error_json = json.loads(err.read())
            print >> sys.stderr, "Server response:"
            pprint(error_json, stream=sys.stderr)
        except BaseException:
            print >> sys.stderr, err.read()
    return (resp_data, status)


def clone_repo(url, bare=True):
    """Clones url to a temporary directory, and returns its path."""
    clonedir = mkdtemp()
    cmd = ["git", "clone"]
    if bare:
        cmd.append("--bare")
    cmd.extend([url, clonedir])
    subprocess.call(cmd)
    return clonedir


def main():
    '''Our main routine'''
    usage = ("Utility to duplicate an AutoPkg recipe repo on GitHub "
             "to an organization and create a new team specifically "
             "for the duplicate repo, and assign the source repo author "
             "to this team."
             "\n\n %prog [options] source-repo-user/recipe-repo-name")
    default_org = "autopkg"
    permisison_levels = ["pull", "push", "admin"]
    default_permission_level = "admin"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-t", "--token",
                      help="Auth token string to use. Required.")
    parser.add_option("-o", "--destination-org", default=default_org,
                      help=("GitHub org to fork the repo to. Defaults to '%s'."
                            % default_org))
    parser.add_option("-r", "--destination-repo-name",
                      help=("Destination repo-name. Defaults to "
                            "'username-recipes'"))
    parser.add_option("-p", "--permission-level",
                      default=default_permission_level,
                      help=("Permission level to use for new team. Must be one "
                            "of: %s. Defaults to %s."
                            % (", ".join(permisison_levels),
                               default_permission_level)))
    opts, args = parser.parse_args()
    if len(args) == 0:
        sys.exit("You must provide a repo in the form of 'user/repo' as the "
                 "only argument!")
    if opts.permission_level not in permisison_levels:
        sys.exit("Permission level option must be one of: %s."
                 % ", ".join(permisison_levels))
    if not opts.token:
        sys.exit("You must provide a token with '-t', and it must have admin "
                 "access for the org.")

    repo_components = args[0].split("/")
    source_repo_user = repo_components[-2]
    source_repo_name = repo_components[-1]
    print ("Using source repo: user %s, repo %s"
           % (source_repo_user, source_repo_name))
    destination_repo_name = (opts.destination_repo_name
                             or source_repo_user + "-recipes")
    dest_org = opts.destination_org
    print "Will clone to %s/%s.." % (dest_org, destination_repo_name)
    global TOKEN
    TOKEN = opts.token

    # Get the authenticated username for later use
    resp, code = call_api("/user")
    auth_user = resp["login"]

    # Grab the source repo metadata for later use
    # (currently we're only using description)
    src_repo, code = call_api(
        "/repos/%s/%s" % (source_repo_user, source_repo_name))

    # Get the existing repos of the destination user or org
    dest_repos = []
    print "Fetching %s's public repos.." % dest_org
    dest_repos_result, code = call_api("/users/%s/repos" % dest_org)
    if dest_repos_result:
        dest_repos = [r["name"] for r in dest_repos_result]
        if destination_repo_name in dest_repos:
            sys.exit("User %s already has a repo called '%s'!"
                     % (dest_org, destination_repo_name))

    # Repo is going to get its own team with the same name
    new_team_name = destination_repo_name
    teams, code = call_api("/orgs/%s/teams" % dest_org)
    if new_team_name in [t["name"] for t in teams]:
        sys.exit("Team %s already exists." % new_team_name)

    # Create the new bare repo
    new_repo_data = {"name": destination_repo_name,
                     "description": src_repo["description"],
                     "auto_init": False}
    _, code = call_api("/orgs/%s/repos" % dest_org,
                       method="POST",
                       data=new_repo_data)

    # Create new team in the org for use with this repo
    print "Creating new team: %s.." % new_team_name
    new_team_data = {
        "name": new_team_name,
        "permission": opts.permission_level,
        "repo_names": ["%s/%s" % (dest_org, destination_repo_name)]}
    new_team, code = call_api("/orgs/%s/teams" % dest_org,
                              method="POST",
                              data=new_team_data)
    if code != 201:
        sys.exit("Error creating team!")

    # For some reason, the authenticated user automatically gets added
    # to the new team, which is not what we want, so remove the user
    remove_member_endpoint = ("/teams/%s/members/%s"
                              % (new_team["id"], auth_user))
    _, code = call_api(remove_member_endpoint, method="DELETE")
    if code != 204:
        print >> sys.stderr, ("Warning: Unexpected HTTP result on removing "
                              "%s from new team." % auth_user)

    # Add the user to the new team
    # https://developer.github.com/v3/orgs/teams/#add-team-membership
    print "Adding %s to new team.." % source_repo_user
    user_add_team_endpoint = ("/teams/%s/memberships/%s"
                              % (new_team["id"], source_repo_user))
    # We need to explicitly set a Content-Length of 0, otherwise
    # the API server is expecting us to send data because of PUT
    response, code = call_api(user_add_team_endpoint,
                              headers={"Content-Length": 0},
                              method="PUT")
    if code == 200:
        print "User membership of team is now %s" % response["state"]
    else:
        sys.exit("Error adding team member %s to new team, "
                 "HTTP status code %s." % (source_repo_user, code))

    # Duplicate the repo using Git
    # https://help.github.com/articles/duplicating-a-repository
    repodir = clone_repo("https://github.com/%s/%s"
                         % (source_repo_user, source_repo_name))
    os.chdir(repodir)
    subprocess.call(["git", "push", "--mirror",
                     "https://github.com/%s/%s"
                     % (dest_org, destination_repo_name)])


if __name__ == "__main__":
    main()
