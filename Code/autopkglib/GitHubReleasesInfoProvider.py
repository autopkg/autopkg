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

import autopkglib.apgithub
from autopkglib import Processor, ProcessorError

__all__ = ["GitHubReleasesInfoProvider"]


class GitHubReleasesInfoProvider(Processor):
    description = (
        "Get metadata from the latest release from a GitHub project"
        " using the GitHub Releases API. You should populate GITHUB_TOKEN_PATH in preferences."
        "\nRequires version 2.8.1."
    )
    input_variables = {
        "github_repo": {
            "required": True,
            "description": ("Name of a GitHub user and repo, ie. 'autopkg/autopkg'"),
        },
        "asset_regex": {
            "required": False,
            "description": (
                "If set, return only a release asset whose name matches this regex. "
                "If this is not set, it will behave identically to 'latest_only' being set."
            ),
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

    def select_asset(
        self, releases: autopkglib.apgithub.GithubReleasesDict, regex: str
    ) -> None:
        """Iterates through the a list of asset filenames in order and determines the first
        eligible asset that matches the regex. Sets the selected release
        and asset data in class variables."""
        # selected is going to be a tuple of the release tag, asset filename, and asset url
        selected: Optional[tuple[str, str, str]] = None
        for rel, assets in releases.items():
            # rel is a release tag, such as:
            # 'v2.7.2'
            # assets is a list of dictionaries of filenames: URLs
            if selected:
                break

            if not regex:
                # If there are no assets, do nothing
                if not assets:
                    continue
                # If there's no regex to match against, attempt to return the first asset we find
                try:
                    selected = (rel, next(iter(assets[0])), list(assets[0].values())[0])
                    break
                except KeyError:
                    # If there are no assets, we just throw the processor error below
                    pass
            for asset in assets:
                # asset is a Dict with filename: url
                # Example:
                # {'autopkg-2.7.2.pkg': 'https://github.com/autopkg/autopkg/releases/download/v2.7.2/autopkg-2.7.2.pkg'}
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
                if selected:
                    break
        if not selected:
            return

        # We set these in the class to avoid passing more objects around
        self.selected_release_tag = selected[0]
        self.selected_asset = selected[1]
        self.selected_asset_url = selected[2]
        self.output(
            f"Selected asset '{self.selected_asset}' from tag "
            f"'{self.selected_release_tag}' at url {self.selected_asset_url}"
        )

    def main(self):
        """Execute Github-related searches for releases."""
        self.selected_release_tag = None
        self.selected_asset = None
        self.selected_asset_url = None

        # Start a new session
        new_session = autopkglib.apgithub.GitHubSession()
        # We're just going to use the built-in function from autopkglib.apgithub to get a dictionary
        # of releases to asset names and URLs, and regex against that.
        # The idea is that other processors don't need to learn PyGithub and can just get straight
        # into business logic
        # This is a dictionary of release tags : [{ asset_name: asset_url }]
        # Example from autopkg/autopkg:
        # {
        # 'v2.8.1RC2':
        #   [{'autopkg-2.8.1.pkg': 'https://github.com/autopkg/autopkg/releases/download/v2.8.1RC2/autopkg-2.8.1.pkg'}],
        # 'v2.8.0RC1':
        #   [{'autopkg-2.8.0.pkg': 'https://github.com/autopkg/autopkg/releases/download/v2.8.0RC1/autopkg-2.8.0.pkg'}],
        # 'v2.7.2':
        #   [{'autopkg-2.7.2.pkg': 'https://github.com/autopkg/autopkg/releases/download/v2.7.2/autopkg-2.7.2.pkg'}],
        # }
        self.output(f"Creating GitHub session for {self.env['github_repo']}", 3)
        releases_dict: autopkglib.apgithub.GithubReleasesDict = (
            new_session.get_repo_asset_dict(
                self.env["github_repo"], self.env.get("include_prereleases", False)
            )
        )
        # self.output(releases_dict, 4)
        # If we're looking for the latest one, we look at the first dictionary entry
        releases: autopkglib.apgithub.GithubReleasesDict = {}
        if self.env.get("latest_only"):
            self.output("Considering latest release only")
            # Use a dictionary comprehension to create a new dictionary that contains only the latest key
            releases = {
                k: releases_dict[k]
                for k in releases_dict.keys()
                if k == next(iter(releases_dict))
            }
        else:
            # If not the latest, just send in the whole thing
            releases = releases_dict
        self.output(f"All releases available: {releases}", 4)
        # Find the first eligible asset based on the regex
        self.select_asset(releases, self.env.get("asset_regex"))
        if not (
            self.selected_release_tag
            and self.selected_asset
            and self.selected_asset_url
        ):
            raise ProcessorError(
                "No release assets were found that satisfy the criteria."
            )

        # The asset id is now in self.selected_asset_id
        self.output("Fetching release data from GitHub...", 3)
        this_release = new_session.current_repo.get_release(self.selected_release_tag)
        # Get all the asset data about this particular release's asset
        this_asset = [x for x in this_release.assets if x.name == self.selected_asset][
            0
        ]

        # Record the browser download url
        self.env["url"] = self.selected_asset_url

        # Record the asset url
        self.env["asset_url"] = this_asset.url

        # Record the asset created_at time in ISO 8601 format
        self.env["asset_created_at"] = this_asset.created_at.strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        # Get a version string from the tag name
        tag = self.selected_release_tag
        # Versioned tags usually start with 'v'
        if tag.startswith("v"):
            tag = tag.lstrip("v.")
        self.env["version"] = tag

        # Record release notes
        self.env["release_notes"] = this_release.body
        # The API may return a JSON null if no body text was provided,
        # but we cannot ever store a None/NULL in an env.
        if not self.env["release_notes"]:
            self.env["release_notes"] = ""


if __name__ == "__main__":
    PROCESSOR = GitHubReleasesInfoProvider()
    PROCESSOR.execute_shell()
