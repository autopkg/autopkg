#!/usr/local/autopkg/python
#
# Copyright 2014-2015 Timothy Sutton
# 2020 Refactor for private repositories Arjen van Bochoven
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

import re

import autopkglib.github
from autopkglib import APLooseVersion, Processor, ProcessorError

BASE_URL = "https://api.github.com"

__all__ = ["GitHubReleasesInfoProvider"]


class GitHubReleasesInfoProvider(Processor):
    description = (
        "Get metadata from the latest release from a GitHub project"
        " using the GitHub Releases API."
        "\nRequires version 0.5.0."
    )
    input_variables = {
        "asset_regex": {
            "required": False,
            "description": (
                "If set, return only a release asset that matches this regex."
            ),
        },
        "github_repo": {
            "required": True,
            "description": ("Name of a GitHub user and repo, ie. 'MagerValp/AutoDMG'"),
        },
        "include_prereleases": {
            "required": False,
            "description": (
                "If set to True or a non-empty value, include prereleases."
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
            "description": ("Full release notes body text from the chosen release.")
        },
        "url": {
            "description": (
                "URL for the first asset found for the project's latest release."
            )
        },
        "curl_opts": {
            "description": (
                "Curl options, including the Github Token for authorization."
            )
        },
        "filename": {"description": ("The filename of the asset.")},
        "version": {
            "description": (
                "Version info parsed, naively derived from the release's tag."
            )
        },
    }

    __doc__ = description

    def get_releases(self, repo):
        """Return a list of releases dicts for a given GitHub repo. repo must
        be of the form 'user/repo'"""
        releases = None
        releases_uri = f"/repos/{repo}/releases"
        (releases, status) = self.github.call_api(releases_uri)
        if status != 200:
            raise ProcessorError(f"Unexpected GitHub API status code {status}.")

        if not releases:
            raise ProcessorError(f"No releases found for repo '{repo}'")

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
                    try:
                        if re.match(regex, asset["name"]):
                            self.output(
                                f"Matched regex '{regex}' among asset(s): "
                                f"{', '.join([x['name'] for x in assets])}"
                            )
                            selected = (rel, asset)
                            break
                    except re.error as e:
                        raise ProcessorError(f"Invalid regex: {e}")
        if not selected:
            raise ProcessorError(
                "No release assets were found that satisfy the criteria."
            )

        # We set these in the class to avoid passing more objects around
        self.selected_release = selected[0]
        self.selected_asset = selected[1]
        self.output(
            f"Selected asset '{self.selected_asset['name']}' from release "
            f"'{self.selected_release['name']}'"
        )

    def get_tag(self):
        tag = self.selected_release["tag_name"]
        # Versioned tags usually start with 'v'
        if tag.startswith("v"):
            tag = tag[1:]
        return tag
    
    def load_github_session(self):
        curl_opts = self.env.get("curl_opts")
        return autopkglib.github.GitHubSession(self.env["CURL_PATH"], curl_opts)

    def get_curl_opts(self):
        curl_opts = self.env.get("curl_opts", [])
        curl_opts.extend(["--header", f"Accept: application/octet-stream"])
        if self.github.token:
            curl_opts.extend(["--header", f"Authorization: token {self.github.token}"])
        return curl_opts

    def get_release_notes(self):
        release_notes = self.selected_release["body"]
        # The API may return a JSON null if no body text was provided,
        # but we cannot ever store a None/NULL in an env.
        if not release_notes:
            release_notes = ""
        return release_notes

    def remove_field(self, line):
        """Check if we have an Accept or Authorization header."""
        part = line.split(None, 1)
        return part[0].rstrip(":").lower() in ["accept", "authorization"]

    def filter_curl_opts(self):
        """Filter Accept and Authorization headers"""
        curl_opts = self.env.get("curl_opts", [])
        curl_opts_filtered = []
        length = len(curl_opts) 
        i = 0
        while i < length: 
            val = curl_opts[i]
            if val == "--header" and self.remove_field(curl_opts[i + 1]):
                i += 1
            else:
                curl_opts_filtered.extend([val])
            i += 1
        self.env["curl_opts"] = curl_opts_filtered

    def main(self):
        # Remove Accept and Authorization form curl options
        self.filter_curl_opts()

        # load github session
        self.github = self.load_github_session()

        # Get our list of releases
        releases = self.get_releases(self.env["github_repo"])
        if self.env.get("sort_by_highest_tag_names"):
            releases = sorted(
                releases, key=lambda a: APLooseVersion(a["tag_name"]), reverse=True
            )

        # Store the first eligible asset
        self.select_asset(releases, self.env.get("asset_regex"))

        # Set env variables
        self.env["filename"] = self.selected_asset["name"]
        self.env["url"] = self.selected_asset["url"]
        self.env["version"] = self.get_tag()
        self.env["curl_opts"] = self.get_curl_opts()
        self.env["release_notes"] = self.get_release_notes()


if __name__ == "__main__":
    PROCESSOR = GitHubReleasesInfoProvider()
    PROCESSOR.execute_shell()
