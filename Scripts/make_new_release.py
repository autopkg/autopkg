#!/usr/bin/python
#
# Script to run the AutoPkg GitHub release workflow as outlined here:
# https://github.com/autopkg/autopkg/wiki/Packaging-AutoPkg-For-Release-on-GitHub
#
# This includes tagging and setting appropriate release notes for the release,
# uploading the actual built package, and incrementing the version number for the
# next version to be released.
#
# This skips the bootstrap installation script at 'Scripts/install.sh', because this
# step would require root.
#
# Requires an OAuth token with push access to the repo. Currently the GitHub Releases
# API is in a 'preview' status, and this script does very little error handling.

import json
import optparse
import os
import plistlib
import re
import subprocess
import sys
import tempfile
import urllib2

from distutils.version import LooseVersion
from pprint import pprint
from shutil import rmtree
from time import strftime

GITHUB_REPO = 'autopkg/autopkg'

class GitHubAPIError(BaseException):
    pass


def api_call(endpoint, token, baseurl='https://api.github.com', data=None, json_data=True, additional_headers={}):
    '''endpoint: of the form '/repos/username/repo/etc'.
    token: the API token for Authorization.
    baseurl: the base URL for the API endpoint. for asset uploads this ends up needing to be overridden.
    data: takes a standard python object and serializes to json for a POST, unless json_data is False.
    additional_headers: a dict of additional headers for the API call'''
    if data and json_data:
        data = json.dumps(data, ensure_ascii=False)
    headers = {'Accept': 'application/vnd.github.v3+json',
               'Authorization': 'token %s' % token}
    for header, value in additional_headers.items():
        headers[header] = value

    req = urllib2.Request(baseurl + endpoint, headers=headers)
    try:
        results = urllib2.urlopen(req, data=data)
    except urllib2.HTTPError as e:
        print >> sys.stderr, "HTTP error making API call!"
        print >> sys.stderr, e
        error_json = e.read()
        error = json.loads(error_json)
        print >> sys.stderr, "API message: %s" % error['message']
        sys.exit(1)
    if results:
        try:
            parsed = json.loads(results.read())
            return parsed
        except BaseException as e:
            print >> sys.stderr, e
            raise GitHubAPIError
    return None


def main():
    usage="""Builds and pushes a new AutoPkg release from an existing Git clone
of AutoPkg.

Requirements:

API token:
You'll need an API OAuth token with push access to the repo. You can create a
Personal Access Token in your user's Account Settings:
https://github.com/settings/applications

autopkgserver components:
This script does not perform the bootstrap steps performed by the install.sh
script, which are needed to have a working pkgserver component. This must
be done as root, so it's best done as a separate process.
"""
    o = optparse.OptionParser(usage=usage)
    o.add_option('-t', '--token',
        help="""GitHub API OAuth token. Required.""")
    o.add_option('-v', '--next-version',
        help="""Next version to which AutoPkg will be incremented. Required.""")

    opts, args = o.parse_args()
    if not opts.next_version:
        sys.exit("Option --next-version is required!")
    if not opts.token:
        sys.exit("Option --token is required!")
    next_version = opts.next_version
    token = opts.token
    # ensure our OAuth token works before we go any further
    api_call('/users/autopkg', token)

    # set up some paths and important variables
    autopkg_root = tempfile.mkdtemp()
    version_plist_path = os.path.join(autopkg_root, 'Code/autopkglib/version.plist')
    changelog_path = os.path.join(autopkg_root, 'CHANGELOG.md')

    # clone Git master
    subprocess.check_call(['git', 'clone', 'https://github.com/autopkg/autopkg', autopkg_root])
    os.chdir(autopkg_root)

    # get the current autopkg version
    try:
        plist = plistlib.readPlist(version_plist_path)
        current_version = plist['Version']
    except:
        sys.exit("Couldn't determine current autopkg version!")
    print "Current AutoPkg version: %s" % current_version
    if LooseVersion(next_version) <= LooseVersion(current_version):
        sys.exit("Next version (gave %s) must be greater than current version %s!"
            % (next_version, current_version))

    tag_name = 'v%s' % current_version
    published_releases = api_call('/repos/%s/releases' % GITHUB_REPO, token)
    for r in published_releases:
        if r['tag_name'] == tag_name:
            print >> sys.stderr, ("There's already a published release on GitHub with the tag {0}. "
                "It should first be manually removed. Release data printed below:".format(tag_name))
            pprint(r, stream=sys.stderr)
            sys.exit()

    # write today's date in the changelog
    with open(changelog_path, 'r') as fd:
        changelog = fd.read()
    release_date = strftime("%B %d, %Y")
    new_changelog = re.sub('Unreleased', release_date, changelog)
    with open(changelog_path, 'w') as fd:
        fd.write(new_changelog)

    # commit and push the new release
    subprocess.check_call(['git', 'add', changelog_path])
    subprocess.check_call(['git', 'commit', '-m', 'Release version %s.' % current_version])
    subprocess.check_call(['git', 'tag', tag_name])
    subprocess.check_call(['git', 'push', 'origin', 'master'])
    subprocess.check_call(['git', 'push', '--tags', 'origin', 'master'])
    # extract release notes for this new version
    match = re.search("(?P<current_ver_notes>\#\#\# %s.+?)\#\#\#" % current_version, new_changelog, re.DOTALL)
    if not match:
        sys.exit("Couldn't extract release notes for this version!")
    release_notes = match.group('current_ver_notes')

    # run the actual AutoPkg.pkg recipe
    recipes_dir = tempfile.mkdtemp()
    subprocess.check_call(['git', 'clone', 'https://github.com/autopkg/recipes', recipes_dir])
    # running using the system AutoPkg directory so that we ensure we're at the minimum
    # required version to run the AutoPkg recipe
    p = subprocess.Popen(['/Library/AutoPkg/autopkg',
        'run',
        '-k', 'force_pkg_build=true',
        '--search-dir', recipes_dir,
        '--report-plist',
        'AutoPkgGitMaster.pkg'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    out, err = p.communicate()
    print >> sys.stderr, err
    try:
        report = plistlib.readPlistFromString(out)
    except BaseException as e:
        print >> sys.stderr, "Couldn't parse a valid report plist from the autopkg run!"
        sys.exit(e)

    if report['failures']:
        sys.exit("Recipe run error: %s" % report['failures'][0]['message'])

    # collect pkg file data
    built_pkg_path = report['new_packages'][0]['pkg_path']
    pkg_filename = os.path.basename(built_pkg_path)
    with open(built_pkg_path, 'rb') as fd:
        pkg_data = fd.read()

    # prepare release metadata
    release_data = dict()
    release_data['tag_name'] = tag_name
    release_data['target_commitish'] = 'master'
    release_data['name'] = "AutoPkg " + current_version
    release_data['body'] = release_notes
    release_data['draft'] = False

    # create the release
    create_release = api_call(
        '/repos/%s/releases' % GITHUB_REPO,
        token,
        data=release_data)
    if create_release:
        print "Release successfully created. Server response:"
        pprint(create_release)
        print

        # upload the pkg as a release asset
        new_release_id = create_release['id']
        endpoint = '/repos/%s/releases/%s/assets?name=%s' % (GITHUB_REPO, new_release_id, pkg_filename)
        upload_asset = api_call(
            endpoint,
            token,
            baseurl='https://uploads.github.com',
            data=pkg_data,
            json_data=False,
            additional_headers={'Content-Type': 'application/octet-stream'})
        if upload_asset:
            print "Successfully attached .pkg release asset. Server response:"
            pprint(upload_asset)
            print

    # increment version
    print "Incrementing version to %s.." % next_version
    plist['Version'] = next_version
    plistlib.writePlist(plist, version_plist_path)

    # increment changelog
    new_changelog = "### %s (Unreleased)\n\n" % next_version + new_changelog
    with open(changelog_path, 'w') as fd:
        fd.write(new_changelog)

    # commit and push increment
    subprocess.check_call(['git', 'add', version_plist_path, changelog_path])
    subprocess.check_call(['git', 'commit', '-m', 'Bumping to v%s for development.' % next_version])
    subprocess.check_call(['git', 'push', 'origin', 'master'])

    # clean up
    rmtree(recipes_dir)


if __name__ == '__main__':
    main()
