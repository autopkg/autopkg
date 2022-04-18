#!/usr/local/autopkg/python
#
# Script to run the AutoPkg GitHub release workflow as outlined here:
# https://github.com/autopkg/autopkg/wiki/Packaging-AutoPkg-For-Release-on-GitHub
#
# This includes tagging and setting appropriate release notes for the release,
# uploading the actual built package, and incrementing the version number for
# the next version to be released.
#
# This skips the bootstrap installation script at 'Scripts/install.sh', because
# this step would require root.
#
# Requires an OAuth token with push access to the repo. Currently the GitHub
# Releases API is in a 'preview' status, and this script does very little error
# handling.
"""See docstring for main() function"""


import json
import optparse
import os
import pathlib
import plistlib
import re
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from distutils.version import LooseVersion
from pprint import pprint
from shutil import rmtree
from time import strftime

import certifi


class GitHubAPIError(BaseException):
    """Base error for GitHub API interactions"""

    pass


def api_call(
    endpoint,
    token=None,
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
        data = json.dumps(data, ensure_ascii=False).encode()
    headers = {
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"token {token}"
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
    """
    Builds and pushes a new AutoPkg release from an existing Git clone
    of AutoPkg.

    Requirements:

    API token:
    You'll need an API OAuth token with push access to the repo. You can create a
    Personal Access Token in your user's Account Settings:
    https://github.com/settings/tokens

    autopkgserver components:
    This script does not perform the bootstrap steps performed by the install.sh
    script, which are needed to have a working pkgserver component. This must
    be done as root, so it's best done as a separate process.
    """
    usage = __doc__
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-t", "--token", help="GitHub API OAuth token. Required.")
    parser.add_option(
        "-v",
        "--next-version",
        help=("Next version to which AutoPkg will be incremented. Required."),
    )
    parser.add_option(
        "-p",
        "--prerelease",
        help=(
            "Mark this release as a pre-release, applying "
            "a given suffix to the tag, i.e. 'RC1'"
        ),
    )
    parser.add_option(
        "--dry-run",
        action="store_true",
        help=(
            "Don't actually push any changes to "
            "Git remotes, and skip the actual release "
            "creation. Useful for testing changes "
            "to this script. Any GitHub API calls made "
            "are read-only."
        ),
    )
    parser.add_option(
        "--user-repo",
        default="autopkg/autopkg",
        help=(
            "Alternate org/user and repo to use for "
            "the release, useful for testing. Defaults to "
            "'autopkg/autopkg'."
        ),
    )
    parser.add_option(
        "-b",
        "--autopkg-branch",
        default="master",
        help=("A specific branch of AutoPkg repo clone. Otherwise, clone master."),
    )
    parser.add_option(
        "-r",
        "--recipe-branch",
        default="master",
        help=(
            "A specific branch of autopkg-recipes repo clone. "
            "Otherwise, clone master."
        ),
    )

    opts = parser.parse_args()[0]
    if not opts.next_version:
        sys.exit("Option --next-version is required!")
    if not opts.token and not opts.dry_run:
        sys.exit("Option --token is required!")
    next_version = opts.next_version
    if opts.dry_run:
        print("** Running in 'dry-run' mode..")
    publish_user, publish_repo = opts.user_repo.split("/")
    token = None
    if (not opts.dry_run):
        token = opts.token
        # ensure our OAuth token works before we go any further
        print("** Verifying OAuth token")
        api_call(f"/users/{publish_user}", token)

    # set up some paths and important variables
    autopkg_root = tempfile.mkdtemp()
    version_plist_path = os.path.join(autopkg_root, "Code/autopkglib/version.plist")
    changelog_path = os.path.join(autopkg_root, "CHANGELOG.md")

    git_cmd = ["git", "clone"]
    if opts.autopkg_branch:
        git_cmd.extend(["--branch", opts.autopkg_branch])
    git_cmd.extend([f"https://github.com/{publish_user}/{publish_repo}", autopkg_root])
    print((" ").join(git_cmd))
    # Clone the branch of AutoPkg
    print(f"** Clone git {opts.autopkg_branch}")
    subprocess.check_call(git_cmd)
    os.chdir(autopkg_root)

    # get the current autopkg version
    try:
        with open(version_plist_path, "rb") as f:
            plist = plistlib.load(f)
        current_version = plist["Version"]
    except BaseException:
        sys.exit("Couldn't determine current autopkg version!")
    print(f"** Current AutoPkg version: {current_version}")
    if LooseVersion(next_version) <= LooseVersion(current_version):
        sys.exit(
            f"Next version (gave {next_version}) must be greater than current version "
            f"{current_version}!"
        )

    print("** Checking published releases")
    tag_name = f"v{current_version}"
    if opts.prerelease:
        tag_name += opts.prerelease
    published_releases = api_call(
        f"/repos/{publish_user}/{publish_repo}/releases", token
    )
    for rel in published_releases:
        if rel["tag_name"] == tag_name:
            print(
                "There's already a published release on GitHub with the tag "
                "{}. It should first be manually removed. "
                "Release data printed below:".format(tag_name),
                file=sys.stderr,
            )
            pprint(rel, stream=sys.stderr)
            sys.exit()

    print("** Writing date into CHANGELOG.md")
    # write today's date in the changelog
    with open(changelog_path, "r") as fdesc:
        changelog = fdesc.read()
    release_date = strftime("(%B %d, %Y)")
    new_changelog = re.sub(r"\(Unreleased\)", release_date, changelog)
    new_changelog = re.sub("...HEAD", f"...v{current_version}", new_changelog)
    with open(changelog_path, "w") as fdesc:
        fdesc.write(new_changelog)

    print("** Creating git commit")
    # commit and push the new release
    subprocess.check_call(["git", "add", changelog_path])
    subprocess.check_call(
        ["git", "commit", "-m", f"Release version {current_version}."]
    )
    subprocess.check_call(["git", "tag", tag_name])
    if not opts.dry_run:
        print("** Pushing git release")
        subprocess.check_call(["git", "push", "origin", opts.autopkg_branch])
        subprocess.check_call(["git", "push", "--tags", "origin", opts.autopkg_branch])

    print("** Gathering release notes")
    # extract release notes for this new version
    notes_rex = r"(?P<current_ver_notes>\#\#\# \[%s\].+?)\#\#\#" % current_version
    match = re.search(notes_rex, new_changelog, re.DOTALL)
    if not match:
        sys.exit("Couldn't extract release notes for this version!")
    release_notes = match.group("current_ver_notes")

    recipes_dir = tempfile.mkdtemp()
    git_cmd = ["git", "clone"]
    if opts.recipe_branch != "master":
        git_cmd.extend(["--branch", opts.recipe_branch])
    git_cmd.extend(["https://github.com/autopkg/recipes", recipes_dir])
    print("** Cloning autopkg-recipes")
    subprocess.check_call(git_cmd)
    os.chdir(autopkg_root)

    print("** Running AutoPkgGitMaster.pkg recipe")
    # running using the system AutoPkg directory so that we ensure we're at the
    # minimum required version to run the AutoPkg recipe
    report_plist_path = tempfile.mkstemp()[1]
    parent_path = pathlib.Path(__file__).parent.parent
    cmd = [
        os.path.join(parent_path, "Code/autopkg"),
        "run",
        "-k",
        "force_pkg_build=true",
    ]
    if opts.autopkg_branch != "master":
        cmd.extend(["-k", f"BRANCH={opts.autopkg_branch}"])
    cmd.extend(
        [
            "--search-dir",
            recipes_dir,
            "--report-plist",
            report_plist_path,
            "AutoPkgGitMaster.pkg",
            "-vvvv",
            "-k",
            "PYTHON_VERSION=3.10.4",
            "-k",
            "REQUIREMENTS_FILENAME=new_requirements.txt",
            "-k",
            "OS_VERSION=11"
        ]
    )
    subprocess.run(args=cmd, text=True, check=True)
    try:
        with open(report_plist_path, "rb") as f:
            report = plistlib.load(f)
    except BaseException as err:
        print(
            "Couldn't parse a valid report plist from the autopkg run!", file=sys.stderr
        )
        sys.exit(err)
    os.remove(report_plist_path)

    if report["failures"]:
        sys.exit(f"Recipe run error: {report['failures'][0]['message']}")

    print("** Collecting package data")
    # collect pkg file data
    pkg_result = report["summary_results"]["pkg_creator_summary_result"]
    built_pkg_path = pkg_result["data_rows"][0]["pkg_path"]
    pkg_filename = os.path.basename(built_pkg_path)
    with open(built_pkg_path, "rb") as fdesc:
        pkg_data = fdesc.read()

    # prepare release metadata
    release_data = dict()
    release_data["tag_name"] = tag_name
    release_data["target_commitish"] = opts.autopkg_branch
    release_data["name"] = "AutoPkg " + current_version
    release_data["body"] = release_notes
    release_data["draft"] = False
    if opts.prerelease:
        release_data["prerelease"] = True
        release_data["name"] += " Beta"

    # create the release
    if not opts.dry_run:
        print("** Creating GitHub release")
        create_release = api_call(
            f"/repos/{publish_user}/{publish_repo}/releases", token, data=release_data
        )
        if create_release:
            print("Release successfully created. Server response:")
            pprint(create_release)
            print()

            print("** Uploading package as release asset")
            # upload the pkg as a release asset
            new_release_id = create_release["id"]
            endpoint = "/repos/{}/{}/releases/{}/assets?name={}".format(
                publish_user, publish_repo, new_release_id, pkg_filename
            )
            upload_asset = api_call(
                endpoint,
                token,
                baseurl="https://uploads.github.com",
                data=pkg_data,
                json_data=False,
                additional_headers={"Content-Type": "application/octet-stream"},
            )
            if upload_asset:
                print("Successfully attached .pkg release asset. Server response:")
                pprint(upload_asset)
                print()

    # increment version
    print(f"** Incrementing version to {next_version}..")
    plist["Version"] = next_version
    with open(version_plist_path, "wb") as f:
        plistlib.dump(plist, f)

    # increment changelog
    new_changelog = (
        "### [{}](https://github.com/{}/{}/compare/v{}...HEAD) (Unreleased)\n\n".format(
            next_version, publish_user, publish_repo, current_version
        )
        + new_changelog
    )
    with open(changelog_path, "w") as fdesc:
        fdesc.write(new_changelog)

    print("** Creating commit for change increment")
    # commit and push increment
    subprocess.check_call(["git", "add", version_plist_path, changelog_path])
    subprocess.check_call(
        ["git", "commit", "-m", f"Bumping to v{next_version} for development."]
    )
    if not opts.dry_run:
        print(f"** Pushing commit to {opts.autopkg_branch}")
        subprocess.check_call(["git", "push", "origin", opts.autopkg_branch])
    else:
        print(
            "Ended dry-run mode. Final state of the AutoPkg repo can be "
            f"found at: {autopkg_root}"
        )
    # clean up
    rmtree(recipes_dir)


if __name__ == "__main__":
    main()
