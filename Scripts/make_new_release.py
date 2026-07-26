#!/usr/local/autopkg/python
#
# Copyright 2013 Timothy Sutton
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
import site
import ssl
import subprocess
import sys
import sysconfig
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pprint import pprint
from shutil import rmtree, which
from time import strftime

import certifi

# Releases use a strict MAJOR.MINOR.PATCH version; beta/RC goes on the tag via
# --prerelease, not here.
SEMVER_RE = re.compile(r"\d+\.\d+\.\d+")
PYOBJC_SMOKE_IMPORTS = (
    "Foundation",
    "Quartz",
    "Security",
    "SystemConfiguration",
    "LaunchServices",
)
PYTHON_APP_EXECUTABLE = pathlib.Path(
    "Resources", "Python.app", "Contents", "MacOS", "Python"
)
REQUIRED_PYTHON_ARCHITECTURES = {"arm64", "x86_64"}


def version_tuple(version_string: str) -> tuple[int, ...]:
    """Return a (major, minor, patch) int tuple for a MAJOR.MINOR.PATCH version.

    Raises ValueError if version_string is not exactly MAJOR.MINOR.PATCH.
    """
    if not SEMVER_RE.fullmatch(version_string):
        raise ValueError(version_string)
    return tuple(int(part) for part in version_string.split("."))


def prerelease_display_name(prerelease: str) -> str:
    """Return a human-friendly label for a prerelease suffix."""
    rc_match = re.fullmatch(r"RC(\d+)", prerelease, re.IGNORECASE)
    if rc_match:
        return f"Release Candidate {rc_match.group(1)}"
    return prerelease


def find_bundled_python(expanded_pkg_dir: str) -> tuple[str, str] | None:
    """Return the packaged Python.framework and executable from an expanded pkg."""
    for framework_path in sorted(
        pathlib.Path(expanded_pkg_dir).glob(
            "**/Library/AutoPkg/Python3/Python.framework"
        )
    ):
        versions_path = framework_path / "Versions"
        version_paths = []
        current_path = versions_path / "Current"
        if current_path.exists():
            version_paths.append(current_path)
        if versions_path.exists():
            version_paths.extend(
                path
                for path in sorted(versions_path.iterdir())
                if path.name != "Current" and path.is_dir()
            )
        for version_path in version_paths:
            python_path = version_path / PYTHON_APP_EXECUTABLE
            if python_path.exists():
                return str(framework_path), str(python_path)
    return None


def bundled_python_binary_paths(framework_path: str) -> list[str]:
    """Return Python framework binary paths that must be universal."""
    framework_path = pathlib.Path(framework_path)
    binary_paths = set()
    for path in framework_path.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix in (".so", ".dylib"):
            binary_paths.add(path)
        elif (
            path.parts[-len(PYTHON_APP_EXECUTABLE.parts) :]
            == PYTHON_APP_EXECUTABLE.parts
        ):
            binary_paths.add(path)
        elif path.parent.name == "bin" and re.fullmatch(
            r"python\d*(?:\.\d+)?", path.name
        ):
            binary_paths.add(path)

    version_current_python = framework_path / "Versions" / "Current" / "Python"
    if version_current_python.exists():
        binary_paths.add(version_current_python)

    current_bin = framework_path / "Versions" / "Current" / "bin"
    if current_bin.exists():
        binary_paths.update(
            path
            for path in current_bin.glob("python*")
            if path.is_file() and re.fullmatch(r"python\d*(?:\.\d+)?", path.name)
        )

    return [str(path) for path in sorted(binary_paths)]


def smoke_test_bundled_python_architectures(framework_path: str) -> None:
    """Verify bundled Python binary files contain required universal slices."""
    lipo = "/usr/bin/lipo"
    if not os.path.exists(lipo):
        lipo = which("lipo")
    if not lipo:
        sys.exit("Cannot smoke-test bundled Python architectures: lipo was not found.")

    print("** Smoke-testing bundled Python universal binary slices")
    failures = []
    binary_paths = bundled_python_binary_paths(framework_path)
    if not binary_paths:
        sys.exit("Could not find bundled Python binary files to smoke-test.")

    for binary_path in binary_paths:
        result = subprocess.run(
            [lipo, "-archs", binary_path],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            failures.append(f"{binary_path}: {result.stderr.strip()}")
            continue
        architectures = set(result.stdout.split())
        missing_architectures = REQUIRED_PYTHON_ARCHITECTURES - architectures
        if missing_architectures:
            failures.append(
                "{}: missing {} (found {})".format(
                    binary_path,
                    ", ".join(sorted(missing_architectures)),
                    " ".join(sorted(architectures)) or "none",
                )
            )

    if failures:
        sys.exit(
            "Bundled Python universal binary smoke test failed:\n" + "\n".join(failures)
        )


def smoke_test_bundled_python(pkg_path: str) -> None:
    """Verify the built package's bundled Python can import required frameworks."""
    pkgutil = "/usr/sbin/pkgutil"
    if not os.path.exists(pkgutil):
        pkgutil = which("pkgutil")
    if not pkgutil:
        sys.exit("Cannot smoke-test bundled Python: pkgutil was not found.")

    print("** Smoke-testing bundled Python PyObjC framework imports")
    with tempfile.TemporaryDirectory() as temp_dir:
        expanded_pkg_dir = pathlib.Path(temp_dir) / "expanded_pkg"
        try:
            subprocess.run(
                [pkgutil, "--expand-full", pkg_path, str(expanded_pkg_dir)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except subprocess.CalledProcessError as err:
            sys.exit(
                "Could not expand built package for bundled Python smoke test: "
                f"{err.stderr.strip()}"
            )

        bundled_python = find_bundled_python(str(expanded_pkg_dir))
        if not bundled_python:
            sys.exit("Could not find bundled AutoPkg Python in built package.")
        framework_path, python_path = bundled_python

        import_statement = """
import importlib
import sys

failures = []
for module_name in {modules!r}:
    try:
        importlib.import_module(module_name)
    except Exception as err:
        failures.append(f"{{module_name}}: {{err}}")
if failures:
    sys.stderr.write("\\n".join(failures))
    sys.exit(1)
""".format(modules=PYOBJC_SMOKE_IMPORTS)
        result = subprocess.run(
            [python_path, "-c", import_statement],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            sys.exit(
                "Bundled Python PyObjC smoke test failed: "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
        smoke_test_bundled_python_architectures(framework_path)


class GitHubAPIError(Exception):
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
        context = ssl.create_default_context(cafile=certifi.where())
        results = urllib.request.urlopen(req, data=data, context=context)
    except urllib.error.HTTPError as err:
        print("HTTP error making API call!", file=sys.stderr)
        print(err, file=sys.stderr)
        error_body = err.read().decode("utf-8", errors="replace")
        message = error_body
        try:
            error = json.loads(error_body)
        except json.JSONDecodeError:
            pass
        else:
            if isinstance(error, dict):
                message = error.get("message", error_body)
        print(f"API message: {message}", file=sys.stderr)
        sys.exit(1)
    try:
        parsed = json.loads(results.read())
        return parsed
    except Exception as err:
        print(err, file=sys.stderr)
        raise GitHubAPIError(str(err)) from err


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
    parser.add_option(
        "-t", "--token", help="GitHub API OAuth token. Required except for --dry-run."
    )
    parser.add_option(
        "-v",
        "--next-version",
        help=(
            "Next version to which AutoPkg will be incremented. "
            "Required for final releases."
        ),
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
            "A specific branch of autopkg-recipes repo clone. Otherwise, clone master."
        ),
    )

    opts = parser.parse_args()[0]
    if not opts.next_version and not opts.prerelease:
        sys.exit("Option --next-version is required!")
    if not opts.token and not opts.dry_run:
        sys.exit("Option --token is required!")
    if opts.next_version:
        next_version = opts.next_version
        try:
            next_version_tuple = version_tuple(next_version)
        except ValueError:
            sys.exit(
                f"Option --next-version must be a MAJOR.MINOR.PATCH version "
                f"(e.g. 3.0.1); got '{next_version}'. A beta/RC designation belongs "
                f"on the tag via --prerelease, not on the version itself."
            )
    if opts.dry_run:
        print("** Running in 'dry-run' mode...")
    user_repo_parts = opts.user_repo.split("/")
    if len(user_repo_parts) != 2 or not all(user_repo_parts):
        sys.exit(
            "Option --user-repo must be of the form 'owner/repo'; "
            f"got '{opts.user_repo}'."
        )
    publish_user, publish_repo = user_repo_parts
    token = None
    if not opts.dry_run:
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
    except Exception:
        sys.exit("Couldn't determine current autopkg version!")
    print(f"** Current AutoPkg version: {current_version}")
    try:
        current_version_tuple = version_tuple(current_version)
    except ValueError:
        sys.exit(
            f"Current version '{current_version}' in version.plist is not a "
            f"MAJOR.MINOR.PATCH version; cannot compare."
        )
    if opts.next_version and next_version_tuple <= current_version_tuple:
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

    # compile requirements.txt from requirements.in
    requirements_in_path = os.path.join(autopkg_root, "requirements.in")
    requirements_txt_path = os.path.join(autopkg_root, "requirements.txt")
    uv_bin = which("uv") or os.path.join(sysconfig.get_path("scripts"), "uv")
    if not os.path.isfile(uv_bin):
        print("** Installing uv for requirements compilation")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "uv", "--quiet"])
        # pip may install to user base if the framework dir is root-owned
        for candidate in (
            which("uv"),
            os.path.join(sysconfig.get_path("scripts"), "uv"),
            os.path.join(site.getuserbase(), "bin", "uv"),
        ):
            if candidate and os.path.isfile(candidate):
                uv_bin = candidate
                break
        else:
            sys.exit("'uv' not found after install attempt. Try: pip install uv")
    print("** Compiling requirements.txt from requirements.in")
    subprocess.check_call(
        [
            uv_bin,
            "pip",
            "compile",
            requirements_in_path,
            "--universal",
            "--python-version",
            "3.11",
            "--output-file",
            requirements_txt_path,
            "--quiet",
        ]
    )
    with open(requirements_txt_path, "a") as f:
        f.write("--no-binary :all:\n")
    requirements_changed = (
        subprocess.run(
            ["git", "diff", "--quiet", "requirements.txt"],
            cwd=autopkg_root,
        ).returncode
        != 0
    )
    if requirements_changed:
        print(
            "NOTE: requirements.txt differs from the committed version. "
            "Commit and push that change before tagging a release so the "
            "package is built with the updated dependencies."
        )

    # write today's date in the changelog (in memory; written to disk only for final releases)
    with open(changelog_path) as fdesc:
        changelog = fdesc.read()
    release_date = strftime("(%B %-d, %Y)")
    new_changelog, replacements = re.subn(
        r"\(Unreleased\)", release_date, changelog, count=1
    )
    if replacements != 1:
        sys.exit("Couldn't find an '(Unreleased)' marker in CHANGELOG.md!")
    new_changelog, replacements = re.subn(
        r"\.\.\.HEAD", f"...{tag_name}", new_changelog, count=1
    )
    if replacements != 1:
        sys.exit("Couldn't find a '...HEAD' comparison link in CHANGELOG.md!")
    if not opts.prerelease:
        print("** Writing date into CHANGELOG.md")
        with open(changelog_path, "w") as fdesc:
            fdesc.write(new_changelog)
        print("** Creating git commit")
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
    notes_rex = r"(?P<current_ver_notes>^## \[%s\].+?)(?=^## |\Z)" % re.escape(
        current_version
    )
    match = re.search(notes_rex, new_changelog, re.DOTALL | re.MULTILINE)
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

    print("** Clearing AutoPkgGitMaster recipe cache")
    parent_path = pathlib.Path(__file__).parent.parent
    # check=False: exit code 1 is expected when no cache exists yet
    subprocess.run(
        [
            os.path.join(parent_path, "Code/autopkg"),
            "clear-cache",
            "--search-dir",
            recipes_dir,
            "AutoPkgGitMaster.pkg",
        ],
        check=False,
    )

    print("** Running AutoPkgGitMaster.pkg recipe")
    # running using the system AutoPkg directory so that we ensure we're at the
    # minimum required version to run the AutoPkg recipe
    report_plist_path = tempfile.mkstemp()[1]
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
            "PYTHON_VERSION=3.11.9",
            "-k",
            "REQUIREMENTS_FILENAME=requirements.txt",
            "-k",
            "OS_VERSION=11",
            "-k",
            "upgrade_pip=true",
        ]
    )

    # Use a temporary dir for pip/Python user isolation so relocatable-python
    # cannot see contributor-specific ~/Library/Python or pip cache contents.
    # HOME is intentionally left as the real home so the built pkg lands in the
    # real AutoPkg cache dir (readable after the build) rather than a temp dir.
    with tempfile.TemporaryDirectory() as isolation_dir:
        build_env = os.environ.copy()
        build_env.update(
            {
                "PYTHONUSERBASE": os.path.join(isolation_dir, "Library", "Python"),
                "PIP_CACHE_DIR": os.path.join(
                    isolation_dir, "Library", "Caches", "pip"
                ),
            }
        )
        subprocess.run(args=cmd, text=True, check=True, env=build_env)
        try:
            with open(report_plist_path, "rb") as f:
                report = plistlib.load(f)
        except Exception as err:
            print(
                "Couldn't parse a valid report plist from the autopkg run!",
                file=sys.stderr,
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
        smoke_test_bundled_python(built_pkg_path)
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
        release_data["name"] += f" {prerelease_display_name(opts.prerelease)}"

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

    if not opts.prerelease:
        # increment version
        print(f"** Incrementing version to {next_version}...")
        plist["Version"] = next_version
        with open(version_plist_path, "wb") as f:
            plistlib.dump(plist, f)

        # increment changelog
        new_version_header = (
            "## [{}](https://github.com/{}/{}/compare/v{}...HEAD) "
            "(Unreleased)\n\nNothing yet.\n\n"
        ).format(next_version, publish_user, publish_repo, current_version)

        # Insert the new version header before the first H2 heading
        # Find the position of the first "##" heading
        first_h2_match = re.search(r"^## ", new_changelog, re.MULTILINE)
        if first_h2_match:
            insert_pos = first_h2_match.start()
            new_changelog = (
                new_changelog[:insert_pos]
                + new_version_header
                + new_changelog[insert_pos:]
            )
        else:
            print(
                "WARNING: No H2 headings found in CHANGELOG.md. "
                "Prepending new version header."
            )
            new_changelog = new_version_header + new_changelog
        with open(changelog_path, "w", encoding="utf-8") as fdesc:
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

    if opts.dry_run:
        print(
            "Ended dry-run mode. Final state of the AutoPkg repo can be "
            f"found at: {autopkg_root}"
        )
    # clean up
    rmtree(recipes_dir)


if __name__ == "__main__":
    main()
