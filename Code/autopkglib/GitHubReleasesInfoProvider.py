#!/usr/local/autopkg/python
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

import re

import autopkglib.github
from autopkglib import APLooseVersion, Processor, ProcessorError

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
        "latest_only": {
            "required": False,
            "description": (
                "If True or a non-empty value, API call will fetch only the "
                "release marked as 'latest' in GitHub. May not play well with "
                "'include_prereleases'."
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
        "ignore_archived": {
            "required": False,
            "default": False,
            "description": (
                "If the Github repo is archived and ignore_archived is False (default): Autopkg will fail hard."
            ),
        },
        "CURL_PATH": {
            "required": False,
            "default": "/usr/bin/curl",
            "description": "Path to curl binary. Defaults to /usr/bin/curl.",
        },
        "GITHUB_URL": {
            "required": False,
            "default": "https://api.github.com",
            "description": (
                "If your organization has an internal GitHub instance "
                "set this value to your internal GitHub URL "
                "ie. 'https://git.internal.corp.com/api/v3'"
            ),
        },
        "GITHUB_TOKEN_PATH": {
            "required": False,
            "default": "~/.autopkg_gh_token",
            "description": (
                "Path to a file containing your GitHub token. "
                "Can be a relative path or absolute path. "
                "ie. '~/.custom_gh_token' or '/path/to/token' "
                "NOTE: the AutoPkg preference 'GITHUB_TOKEN' "
                "takes precedence over this value."
            ),
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
        "asset_url": {
            "description": (
                "The asset URL for the project's latest release. This is an "
                "API-only URL distinct from the browser_download_url, and is "
                "required for programmatically downloading assets from private "
                "repositories."
            )
        },
        "version": {
            "description": (
                "Version info parsed, naively derived from the release's tag."
            )
        },
        "asset_created_at": {"description": ("The release time of the asset.")},
    }

    __doc__ = description

    def get_releases(self, repo, latest_only=False):
        """Return a list of releases dicts for a given GitHub repo. repo must
        be of the form 'user/repo'"""
        releases = None
        curl_opts = self.env.get("curl_opts")
        github = autopkglib.github.GitHubSession(
            self.env["CURL_PATH"],
            curl_opts,
            self.env["GITHUB_URL"],
            self.env["GITHUB_TOKEN_PATH"],
        )
        releases_uri = f"/repos/{repo}/releases"
        if latest_only:
            releases_uri += "/latest"
        (releases, status) = github.call_api(releases_uri)
        if latest_only:
            # turn single item into a list of one item
            releases = [releases]
        if status != 200:
            raise ProcessorError(f"Unexpected GitHub API status code {status}.")

        if not releases:
            raise ProcessorError(f"No releases found for repo '{repo}'")

        return releases
    
    def get_repo(self, repo_name):
        """Return metadata for a given GitHub repo. repo_name must
        be of the form 'user/repo'"""
        curl_opts = self.env.get("curl_opts")
        github = autopkglib.github.GitHubSession(
            self.env["CURL_PATH"],
            curl_opts,
            self.env["GITHUB_URL"],
            self.env["GITHUB_TOKEN_PATH"],
        )
        (repo, status) = github.call_api(f"/repos/{repo_name}")
        if status != 200:
            raise ProcessorError(f"Unexpected GitHub API status code {status}.")
        if not repo:
            raise ProcessorError(f"No repo found for '{repo_name}'")
        self.output(f"found repo {repo_name}")
        self.output(f"repo metadata: {repo}", verbose_level=2)
        return repo
    
    def is_archived(self, repo_name) -> bool:
        """Return True if the repo is archived, False otherwise. repo_name must
        be of the form 'user/repo'"""
        repo = self.get_repo(repo_name)
        archived_status = repo.get("archived")
        self.output(f"{repo_name} is archived: {archived_status}")
        return bool(archived_status)

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

    def main(self):
        is_archived = self.is_archived(self.env["github_repo"])
        self.output(f"self.env['github_repo'] is archived: {is_archived}", verbose_level=2)
        self.output(f"type of is_archived: {type(is_archived)}", verbose_level=2)
        self.output(f"bool(self.env.get('ignore_archived'): {bool(self.env.get('ignore_archived'))}", verbose_level=2)
        if is_archived and not bool(self.env.get("ignore_archived")):
            raise ProcessorError(
                f"GitHub repo '{self.env['github_repo']}' is archived. If you are absolutely sure you still want to use this repo, set the 'ignore_archived' input variable to True."
            )

        # Get our list of releases
        releases = self.get_releases(
            self.env["github_repo"], latest_only=self.env.get("latest_only")
        )
        if self.env.get("sort_by_highest_tag_names"):
            releases = sorted(
                releases, key=lambda a: APLooseVersion(a["tag_name"]), reverse=True
            )

        # Store the first eligible asset
        self.select_asset(releases, self.env.get("asset_regex"))

        # Record the url
        self.env["url"] = self.selected_asset["browser_download_url"]

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
