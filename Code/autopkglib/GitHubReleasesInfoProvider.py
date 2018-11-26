#!/usr/bin/python
#
# Copyright 2014-2015 Timothy Sutton
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
"""See docstring for GitHubReleasesInfoProvider class"""

# Disabling warnings for env members and imports that only affect recipe-
# specific processors.
# pylint: disable=e1101,f0401

import re

import autopkglib.github
from autopkglib import Processor, ProcessorError

__all__ = ["GitHubReleasesInfoProvider"]


class GitHubReleasesInfoProvider(Processor):
    # pylint: disable=missing-docstring
    description = (
        "Get metadata from the latest release from a GitHub project"
        " using the GitHub Releases API."
        "\nRequires version 0.5.0."
    )
    input_variables = {
        "asset_regex": {
            "required": False,
            "description": (
                "If set, return only a release asset that " "matches this regex."
            ),
        },
        "github_repo": {
            "required": True,
            "description": (
                "Name of a GitHub user and repo, ie. " "'MagerValp/AutoDMG'"
            ),
        },
        "include_prereleases": {
            "required": False,
            "description": (
                "If set to True or a non-empty value, include " "prereleases."
            ),
        },
        "sort_by_highest_tag_names": {
            "required": False,
            "description": (
                "Set this to have releases sorted by highest "
                "to lowest tag version. By default, releases "
                "are sorted descending by date posted. This "
                "changes this behavior for cases where an 'older' "
                "release may be posted later."
            ),
        },
        "curl_opts": {
            "required": False,
            "description": (
                "Optional array of curl options to include with "
                "the download request."
            ),
        },
        "CURL_PATH": {
            "required": False,
            "default": "/usr/bin/curl",
            "description": "Path to curl binary. Defaults to /usr/bin/curl.",
        },
    }
    output_variables = {
        "release_notes": {
            "description": ("Full release notes body text from the chosen " "release.")
        },
        "url": {
            "description": (
                "URL for the first asset found for the project's " "latest release."
            )
        },
        "version": {
            "description": (
                "Version info parsed, naively derived from the " "release's tag."
            )
        },
    }

    __doc__ = description

    def get_releases(self, repo):
        """Return a list of releases dicts for a given GitHub repo. repo must
        be of the form 'user/repo'"""
        # pylint: disable=no-self-use
        releases = None
        if "curl_opts" in self.env:
            curl_opts = self.env["curl_opts"]
        else:
            curl_opts = None
        github = autopkglib.github.GitHubSession(self.env["CURL_PATH"], curl_opts)
        releases_uri = "/repos/%s/releases" % repo
        (releases, status) = github.call_api(releases_uri)
        if status != 200:
            raise ProcessorError("Unexpected GitHub API status code %s." % status)

        if not releases:
            raise ProcessorError("No releases found for repo '%s'" % repo)

        return releases

    def select_asset(self, releases, regex):
        """Iterates through the releases in order and determines the first
        eligible asset that matches the criteria. Sets the selected release
        and asset data in class variables.
        - Release 'type' depending on whether 'include_prereleases' is set
        - If 'asset_regex' is set, whether the asset's 'name' (the filename)
          matches the regex. If not, then the first asset will be
          returned."""
        selected = None
        for rel in releases:
            if selected:
                break
            if rel["prerelease"] and not self.env.get("include_prereleases"):
                continue

            assets = rel.get("assets")
            if not assets:
                continue

            for asset in assets:
                if not regex:
                    selected = (rel, asset)
                    break
                else:
                    if re.match(regex, asset["name"]):
                        self.output(
                            "Matched regex '%s' among asset(s): %s"
                            % (regex, ", ".join([x["name"] for x in assets]))
                        )
                        selected = (rel, asset)
                        break
        if not selected:
            raise ProcessorError(
                "No release assets were found that satisfy the criteria."
            )

        # pylint: disable=w0201
        # We set these in the class to avoid passing more objects around
        self.selected_release = selected[0]
        self.selected_asset = selected[1]
        self.output(
            "Selected asset '%s' from release '%s'"
            % (self.selected_asset["name"], self.selected_release["name"])
        )

    def process_release_asset(self):
        """Extract what we need from the release and chosen asset, set env
        variables"""
        tag = self.selected_release["tag_name"]
        # Versioned tags usually start with 'v'
        if tag.startswith("v"):
            tag = tag[1:]

        self.env["url"] = self.selected_asset["browser_download_url"]
        self.env["version"] = tag

    def main(self):
        # Get our list of releases
        releases = self.get_releases(self.env["github_repo"])
        if self.env.get("sort_by_highest_tag_names"):
            from operator import itemgetter

            def loose_compare(this, that):
                # cmp() doesn't exist in Python3, so this uses the suggested
                # solutions from What's New In Python 3.0:
                # https://docs.python.org/3.0/whatsnew/3.0.html#ordering-comparisons
                # This will be refactored in Python 3.
                from distutils.version import LooseVersion

                this_comparison = LooseVersion(this) > LooseVersion(that)
                that_comparison = LooseVersion(this) < LooseVersion(that)
                return this_comparison - that_comparison

            releases = sorted(
                releases, key=itemgetter("tag_name"), cmp=loose_compare, reverse=True
            )

        # Store the first eligible asset
        self.select_asset(releases, self.env.get("asset_regex"))

        # Record the url
        self.env["url"] = self.selected_asset["browser_download_url"]

        # Get a version string from the tag name
        tag = self.selected_release["tag_name"]
        # Versioned tags usually start with 'v'
        if tag.startswith("v"):
            tag = tag[1:]
        self.env["version"] = tag

        # Record release notes
        self.env["release_notes"] = self.selected_release["body"]
        # The API may return a JSON null if no body text was provided,
        # but we cannot ever store a None/NULL in an env.
        if not self.env["release_notes"]:
            self.env["release_notes"] = ""


if __name__ == "__main__":
    PROCESSOR = GitHubReleasesInfoProvider()
    PROCESSOR.execute_shell()
