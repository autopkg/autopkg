#!/usr/local/autopkg/python
#
# Copyright 2014-2015 Timothy Sutton
# Updated 2023 Nick McSpadden
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
from typing import Optional

import autopkglib.github
from autopkglib import Processor, ProcessorError

__all__ = ["GitHubReleasesInfoProvider"]


class GitHubReleasesInfoProvider(Processor):
    description = (
        "Get metadata from the latest release from a GitHub project"
        " using the GitHub Releases API. You should populate GITHUB_TOKEN_PATH in preferences."
        "\nRequires version 2.8.1."
    )
    input_variables = {
        "asset_regex": {
            "required": False,
            "description": (
                "If set, return only a release asset whose name matches this regex. "
                "If this is not set, it will behave identically to 'latest_only' being set."
            ),
        },
        "github_repo": {
            "required": True,
            "description": ("Name of a GitHub user and repo, ie. 'autopkg/autopkg'"),
        },
        "include_prereleases": {
            "required": False,
            "description": (
                "If a non-empty value, include prereleases when applying regex."
            ),
        },
        "latest_only": {
            "required": False,
            "description": (
                "If a non-empty value, apply regex only against latest release's assets."
            ),
        },
    }
    output_variables = {
        "release_notes": {
            "description": ("Full release notes body text from the chosen release.")
        },
        "url": {
            "description": (
                "URL for the first matching asset found for the project's latest release."
            )
        },
        "asset_url": {
            "description": (
                "The asset URL for the project's latest release. This is an "
                "API-only URL distinct from the browser_download_url, and is "
                "required for programmatically downloading assets from private "
                "repositories."
            )
        },
        "version": {"description": ("Version info derived from the release's tag.")},
        "asset_created_at": {"description": ("The release time of the asset.")},
    }

    __doc__ = description

    def select_asset(self, releases: autopkglib.github.GithubReleasesDict, regex: str) -> None:
        """Iterates through the a list of asset filenames in order and determines the first
        eligible asset that matches the regex. Sets the selected release
        and asset data in class variables."""
        # selected is going to be a tuple of the release title, asset filename, and asset url
        selected: Optional[tuple[str, str, str]] = None
        for rel, assets in releases.items():
            # rel is a release name, such as:
            # 'AutoPkg 2.7.2'
            # assets is a list of dictionaries of filenames: URLs
            if selected:
                break

            if not regex:
                # If there's no regex to match against, attempt to return the first asset we find
                try:

                    selected = (rel, next(iter(assets[0])), list(assets[0].values())[0])
                    break
                except KeyError:
                    # If there are no assets, we just throw the processor error below
                    pass
            for asset in assets:
                # asset is a Dictionary with filename: URL
                # Example:
                # {'autopkg-2.7.2.pkg':
                #   'https://github.com/autopkg/autopkg/releases/download/v2.7.2/autopkg-2.7.2.pkg'}
                for asset_filename in asset:
                    try:
                        if re.match(regex, asset_filename):
                            self.output(
                                f"Matched regex '{regex}' among asset(s): {asset_filename}"
                            )
                            selected = (rel, asset_filename, asset[asset_filename])
                            break
                    except re.error as e:
                        raise ProcessorError(f"Invalid regex: {e}") from e
                        raise ProcessorError(f"Invalid regex: {e}") from e
        if not selected:
            raise ProcessorError(
                "No release assets were found that satisfy the criteria."
            )

        # We set these in the class to avoid passing more objects around
        self.selected_release = selected[0]
        self.selected_asset = selected[1]
        self.selected_asset_url = selected[2]
        self.output(
            f"Selected asset '{self.selected_asset}' from release "
            f"'{self.selected_release}' with url {self.selected_asset_url}"
        )

    def main(self):
        """Execute Github-related searches for releases."""
        # Start a new session
        new_session = autopkglib.github.GitHubSession()
        # We're just going to use the built-in function from autopkglib.github to get a dictionary
        # of releases to asset names and URLs, and regex against that.
        # The idea is that other processors don't need to learn PyGithub and can just get straight
        # into business logic
        # This is a dictionary of release titles : [{ asset_name: asset_url }]
        # Example from autopkg/autopkg:
        # {
        # 'AutoPkg 2.8.1 Beta': [{'autopkg-2.8.1.pkg':
        #   'https://github.com/autopkg/autopkg/releases/download/v2.8.1RC2/autopkg-2.8.1.pkg'}],
        # 'AutoPkg 2.8.0 Beta': [{'autopkg-2.8.0.pkg':
        #   'https://github.com/autopkg/autopkg/releases/download/v2.8.0RC1/autopkg-2.8.0.pkg'}],
        # 'AutoPkg 2.7.2': [{'autopkg-2.7.2.pkg': 'https://github.com/autopkg/autopkg/releases/download/v2.7.2/autopkg-2.7.2.pkg'}],
        #  }
        releases_dict: autopkglib.github.GithubReleasesDict = new_session.get_repo_asset_dict(
            self.env["github_repo"], self.env.get("include_preleases", False)
        )
        # If we're looking for the latest one, we look at the first dictionary entry
        releases: autopkglib.github.GithubReleasesDict = {}
        if self.env.get("latest_only") or not self.env.get("regex"):
            releases = releases[next(iter(releases_dict))]
            # Releases will only contain the dictionary of assets from the latest release
        else:
            # If not the latest, just send in the whole thing
            releases = releases_dict
        # Find the first eligible asset based on the regex
        self.select_asset(releases, self.env.get("asset_regex"))

        # TODO: Here's how this needs to work
        # We need to get a list of all asset filenames for a repo, and regex against them
        # We need the release ID from that matching asset filename
        # Once we have the release ID, we can fetch the release directly and all associated information about it

        # Record the download url
        self.env["url"] = self.selected_asset_url

        # Record the asset url
        self.env["asset_url"] = self.selected_asset["url"]

        # Record the asset created_at time
        self.env["asset_created_at"] = self.selected_asset["created_at"]

        # Get a version string from the tag name
        tag = self.selected_release["tag_name"]
        # Versioned tags usually start with 'v'
        if tag.startswith("v"):
            tag = tag.lstrip("v.")
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
