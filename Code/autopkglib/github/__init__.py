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

import os
from textwrap import dedent
from typing import Dict, List, Optional, Union

import github
from autopkglib.common import log, log_err
from autopkglib.prefs import get_pref
from urllib3.util import Retry

# Custom type to express the format of GitHub releases for AutoPkg
# This is a dictionary of release_tag: [ {asset_name: asset_url} ]
# Example from autopkg/autopkg:
# {
# {
# 'v2.8.1RC2':
#   [{'autopkg-2.8.1.pkg': 'https://github.com/autopkg/autopkg/releases/download/v2.8.1RC2/autopkg-2.8.1.pkg'}],
# 'v2.8.0RC1':
#   [{'autopkg-2.8.0.pkg': 'https://github.com/autopkg/autopkg/releases/download/v2.8.0RC1/autopkg-2.8.0.pkg'}],
# 'v2.7.2':
#   [{'autopkg-2.7.2.pkg': 'https://github.com/autopkg/autopkg/releases/download/v2.7.2/autopkg-2.7.2.pkg'}],
# }
GithubReleasesDict = Dict[str, List[Dict[str, str]]]

BASE_URL = "https://api.github.com"
DEFAULT_SEARCH_USER = "autopkg"


class GitHubSession:
    """Handles a session with the GitHub API using PyGithub"""

    def __init__(
        self,
        token_path: str = "",
        base_url: str = "https://api.github.com",
        timeout: int = 15,
        user_agent: str = "autopkg/autopkg",
        per_page: int = 30,
        verify: bool = True,
        retry: Optional[Union[int, Retry]] = None,
        pool_size: Optional[int] = None,
    ) -> None:
        self.auth_token: github.Auth.Token = None
        self.session: github.Github = None
        self.autopkg_org: github.Organization.Organization = None
        self.autopkg_repos: github.Repository.Repository = None
        self.autopkg_main: github.Repository.Repository = None
        # This is always the last repo fetched, for caching
        self.current_repo: github.Repository.Repository = None
        self._token_str = self._get_token(token_path)
        if self._token_str:
            # If we don't have an auth token, some GitHub API options will be unavailable or barely functional
            self.auth_token = github.Auth.Token(self._token_str)
            self.session = github.Github(
                base_url=base_url,
                timeout=timeout,
                user_agent=user_agent,
                per_page=per_page,
                verify=verify,
                retry=retry,
                pool_size=pool_size,
                auth=self.auth_token,
            )
        else:
            log(
                "WARNING: This is an unathenticated Github session, some API features may not work"
            )
            self.session = github.Github()
        self.autopkg_org = self.session.get_organization("autopkg")
        self.autopkg_repos = self.autopkg_org.get_repos(
            type="public", sort="full_name", direction="asc"
        )
        # Is there a more direct way of getting this, given that we know it's "autopkg/autopkg"?
        # But we already have to get the whole list anyway, why not just iterate?
        self.autopkg_main = [
            org for org in self.autopkg_repos if org.name == "autopkg"
        ][0]

    def _get_token(self, token_path: str) -> Optional[str]:
        """Reads token from GITHUB_TOKEN_PATH pref or provided token path."""
        if os.path.exists(token_path):
            expanded_token_path = os.path.expanduser(token_path)
        else:
            expanded_token_path = os.path.expanduser(get_pref("GITHUB_TOKEN_PATH"))
        token = None
        if os.path.exists(expanded_token_path):
            try:
                with open(expanded_token_path, "r") as tokenf:
                    token = tokenf.read().strip()
            except OSError as err:
                log_err(
                    dedent(
                        f"""Couldn't read token file at {expanded_token_path}! Error: {err}
                    Create a new token in your GitHub settings page:
                        https://github.com/settings/tokens
                    To save the token, paste it to the following prompt."""
                    )
                )
        return token

    def get_latest_release_url(self, name_or_id: str, prereleases: bool = False) -> str:
        """Get the download URL to the latest autopkg/autopkg release package.
        If prereleases is True, return latest prerelease."""
        if not prereleases:
            # There's an EZ button for this in the API
            return (
                self.get_repo(name_or_id)
                .get_latest_release()
                .assets[0]
                .browser_download_url
            )
        releases_paginated = self.get_repo(name_or_id).get_releases()
        releases = [rel for rel in releases_paginated if rel.prerelease is True]
        # This somewhat naively assumes the order of releases from the API remains consistent.
        # https://docs.github.com/en/rest/releases/releases?apiVersion=2022-11-28#list-releases
        # Docs do not seem to promise that this order is based on most recent, descending, but for now
        # we'll assume it will continue to be.
        return releases[0].assets[0].browser_download_url
        # TODO: Something to consider: what happens if this fails? If there's a rate limit/API exception,
        # what should we return?
        # For now, we'll generally assume this won't, but this may need to return an Optional string in the future
        # once we test what happens when it fails

    def get_repo(self, name_or_id: str) -> github.Repository.Repository:
        """Get a specific repository object"""
        self.current_repo = self.session.get_repo(name_or_id)
        return self.current_repo

    def get_repo_releases(self, name_or_id: str) -> List[github.GitRelease.GitRelease]:
        """Get a list of GitRelease objects for a repo"""
        repo: github.Repository.Repository = self.get_repo(name_or_id)
        paginated_releases: List[github.GitRelease.GitRelease] = repo.get_releases()
        return [rel for rel in paginated_releases]

    def get_repo_asset_dict(
        self, name_or_id: str, prereleases: bool = False
    ) -> GithubReleasesDict:
        """Get a dict of Release title: [ {asset name: asset id} ] only for all releases for a repo"""
        releases: List[github.GitRelease.GitRelease] = self.get_repo_releases(
            name_or_id
        )
        # Releases have a list of assets - release.asset, which is a list of GitReleaseAssets
        repo_asset_dict = {}
        for release in releases:
            if release.prerelease and not prereleases:
                # If we're not looking for pre-releases, skip it
                continue
            release_assets = []
            for asset in release.assets:
                release_assets.append({asset.name: asset.browser_download_url})
            repo_asset_dict[release.tag_name] = release_assets
        return repo_asset_dict

    def search_for_name(
        self,
        name: str,
        path_only: bool = False,
        user: str = DEFAULT_SEARCH_USER,
        use_token: bool = False,
        results_limit: int = 100,
    ):
        """Search GitHub for results for a given name."""
        log(
            "autopkg search is temporarily disabled; we are migrating to a new strategy in the next release."
            "\nIn the meantime, please see https://github.com/autopkg/autopkg/wiki/Finding-Recipes for tips "
            "on searching GitHub.com directly."
        )
        return []
        # # Include all supported recipe extensions in search.
        # # Compound extensions like ".recipe.yaml" aren't definable here,
        # # so further filtering of results is done below.
        # exts = "+".join(("extension:" + ext.split(".")[-1] for ext in RECIPE_EXTS))
        # # Example value: "extension:recipe+extension:plist+extension:yaml"

        # query = f"q={quote(name)}+{exts}+user:{user}"

        # if path_only:
        #     query += "+in:path,filepath"
        # else:
        #     query += "+in:path,file"
        # query += f"&per_page={results_limit}"

        # results = self.code_search(query, use_token=use_token)

        # if not results or not results.get("total_count"):
        #     log("Nothing found.")
        #     return []

        # # Filter out files from results that are not AutoPkg recipes.
        # results_items = [
        #     item
        #     for item in results["items"]
        #     if any((item["name"].endswith(ext) for ext in RECIPE_EXTS))
        # ]

        # if not results_items:
        #     log("Nothing found.")
        #     return []
        # return results_items

    def code_search(self, query: str, use_token: bool = False):
        """Search GitHub code repos"""
        log(
            "autopkg search is temporarily disabled; we are migrating to a new strategy in the next release."
            "\nIn the meantime, please see https://github.com/autopkg/autopkg/wiki/Finding-Recipes for tips "
            "on searching GitHub.com directly."
        )
        return
        # if use_token:
        #     _ = self.get_or_setup_token()
        # # Do the search, including text match metadata
        # (results, code) = self.call_api(
        #     "/search/code",
        #     query=query,
        #     accept="application/vnd.github.v3.text-match+json",
        # )

        # if code == 403:
        #     log_err(
        #         "You've probably hit the GitHub's search rate limit, officially 5 "
        #         "requests per minute.\n"
        #     )
        #     if results:
        #         log_err("Server response follows:\n")
        #         log_err(results.get("message", None))
        #         log_err(results.get("documentation_url", None))

        #     return None
        # if results is None or code is None:
        #     log_err("A GitHub API error occurred!")
        #     return None
        # return results


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


# Testing this out on the interpreter:
# import sys
# sys.path.append('autopkglib')
# import autopkglib.github
# new_session = autopkglib.github.GitHubSession()
