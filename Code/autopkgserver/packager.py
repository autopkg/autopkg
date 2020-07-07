#!/usr/local/autopkg/python
#
# Copyright 2010-2012 Per Olofsson
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


import os
import plistlib
import re
import shutil
import stat
import subprocess
import tempfile
from xml.parsers.expat import ExpatError

import grp
import pwd

__all__ = ["Packager", "PackagerError"]


class PackagerError(Exception):
    pass


class Packager:
    """Create an Apple installer package.

    Must be run as root."""

    re_pkgname = re.compile(r"^[a-z0-9][a-z0-9 ._\-]*$", re.I)
    re_id = re.compile(r"^[a-z0-9]([a-z0-9 \-]*[a-z0-9])?$", re.I)
    re_version = re.compile(r"^[a-z0-9_ ]*[0-9][a-z0-9_ ]*$", re.I)

    def __init__(self, log, request, name, uid, gid):
        """Arguments:

        log     A logger instance.
        request A request in plist format.
        name    Name of the component to package.
        uid     The UID of the user that made the request.
        gid     The GID of the user that made the request.
        """

        self.log = log
        self.request = request
        self.name = name
        self.uid = uid
        self.gid = gid
        self.tmproot = None

    def package(self):
        """Main method."""

        try:
            self.verify_request()
            self.copy_pkgroot()
            self.apply_chown()
            self.make_component_property_list()
            return self.create_pkg()
        finally:
            self.cleanup()

    def verify_request(self):
        """Verify that the request is valid."""

        def verify_dir_and_owner(path, uid):
            try:
                info = os.lstat(path)
            except OSError as e:
                raise PackagerError(f"Can't stat {path}: {e}")
            if info.st_uid != uid:
                raise PackagerError(f"{path} isn't owned by {uid}")
            if stat.S_ISLNK(info.st_mode):
                raise PackagerError(f"{path} is a soft link")
            if not stat.S_ISDIR(info.st_mode):
                raise PackagerError(f"{path} is not a directory")

        def cmd_output(cmd):
            """Outputs a stdout, stderr tuple from command output using a Popen"""
            p = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False
            )
            out, err = p.communicate()
            if err:
                self.log.debug(f"WARNING: errors from command '{', '.join(cmd)}':")
                self.log.debug(err.decode())
            return (out, err)

        def get_mounts():
            """Returns a list of mounted volume paths as reported by diskutil."""
            out, err = cmd_output(["/usr/sbin/diskutil", "list", "-plist"])
            try:
                du_list = plistlib.loads(out)
            except ExpatError:
                self.log.debug("WARNING: Error parsing diskutil output.")
                self.log.debug(err)
                return []

            vols = set()
            if "AllDisksAndPartitions" in du_list:
                for disk in du_list["AllDisksAndPartitions"]:
                    if "MountPoint" in disk:
                        vols.add(disk["MountPoint"])
                    if "Partitions" in disk:
                        for part in disk["Partitions"]:
                            if "MountPoint" in part:
                                vols.add(part["MountPoint"])
            else:
                self.log.debug("Missing AllDisksAndPartitions key in diskutil output")
            return list(vols)

        def check_ownerships_enabled(path):
            """Return True if 'ignore ownerships' is not set on the volume on which
            'path' resides, False if otherwise. We warn and return True on
            unexpected behavior."""

            # resolve the absolute path if a symlink
            path = os.path.realpath(path)

            # get mount points
            mounts = get_mounts()
            # move '/' to the end so we're sure to evaluate it before other
            # mount points (/ would match any mountpoint)
            if "/" in mounts:
                mounts.remove("/")
                mounts.append("/")
            if mounts:
                self.log.debug(f"Found mounted volumes: {', '.join(mounts)}")
            else:
                self.log.debug(
                    "WARNING: No mountpoints could be determined for "
                    "checking ownerships."
                )
                return True

            # find the mountpoint that has our path
            mount_for_path = None
            for mount in mounts:
                if path.startswith(mount):
                    mount_for_path = mount
                    break
            if not mount_for_path:
                self.log.debug(
                    f"WARNING: Checking disk ownerships for path '{path}' "
                    "failed. Attempting to continue.."
                )
                return True

            # look for 'ignore ownerships' setting on the disk
            # if 'GlobalPermissionsEnabled' is true, ownerships are _not_ ignored
            self.log.debug(f"Checking disk ownerships for mount '{mount_for_path}'..")
            out, err = cmd_output(
                ["/usr/sbin/diskutil", "info", "-plist", mount_for_path]
            )
            try:
                du_info = plistlib.loads(out)
            except ExpatError:
                self.log.debug("WARNING: Error parsing diskutil output.")
                self.log.debug(err)
                return True

            if "GlobalPermissionsEnabled" not in du_info:
                self.log.debug(
                    "WARNING: Couldn't read 'ignore ownerships' "
                    f"setting for mount point '{mount_for_path}'. Attempting to "
                    "continue."
                )
                return True

            if not du_info["GlobalPermissionsEnabled"]:
                return False
            else:
                return True

        self.log.debug("Verifying packaging request")
        # Check that a disk-based pkgroot isn't somewhere where 'ignore ownerships'
        # is set.
        if not check_ownerships_enabled(self.request["pkgroot"]):
            raise PackagerError(
                (
                    "'Ignore ownerships' is set on the disk where pkgroot "
                    f"'{self.request['pkgroot']}' "
                    "was set, and packaging cannot continue. Ownerships must "
                    "be enabled on the volume where a package is to be built."
                )
            )

        # Check owner and type of directories.
        verify_dir_and_owner(self.request["pkgroot"], self.uid)
        self.log.debug("pkgroot ok")
        verify_dir_and_owner(self.request["pkgdir"], self.uid)
        self.log.debug("pkgdir ok")

        # Check name.
        if len(self.request["pkgname"]) > 80:
            raise PackagerError("Package name too long")
        if not self.re_pkgname.search(self.request["pkgname"]):
            raise PackagerError("Invalid package name")
        if self.request["pkgname"].lower().endswith(".pkg"):
            raise PackagerError("Package name mustn't include '.pkg'")
        self.log.debug("pkgname ok")

        # Check ID.
        if len(self.request["id"]) > 80:
            raise PackagerError("Package id too long")
        components = self.request["id"].split(".")
        if len(components) < 2:
            raise PackagerError("Invalid package id")
        for comp in components:
            if not self.re_id.search(comp):
                raise PackagerError("Invalid package id")
        self.log.debug("id ok")

        # Check version.
        if len(self.request["version"]) > 40:
            raise PackagerError("Version too long")
        components = self.request["version"].split(".")
        if len(components) < 1:
            raise PackagerError(f"Invalid version \"{self.request['version']}\"")
        for comp in components:
            if not self.re_version.search(comp):
                raise PackagerError(f'Invalid version component "{comp}"')
        self.log.debug("version ok")

        # Make sure infofile and resources exist and can be read.
        if self.request["infofile"]:
            try:
                with open(self.request["infofile"], "rb"):
                    pass
            except OSError as e:
                raise PackagerError(f"Can't open infofile: {e}")
            self.log.debug("infofile ok")

        # Make sure scripts is a directory and its contents
        # are executable.
        if self.request["scripts"]:
            if self.request["pkgtype"] == "bundle":
                raise PackagerError(
                    "Installer scripts are not supported with bundle package types."
                )
            if not os.path.isdir(self.request["scripts"]):
                raise PackagerError(
                    f"Can't find scripts directory: {self.request['scripts']}"
                )
            for script in ["preinstall", "postinstall"]:
                script_path = os.path.join(self.request["scripts"], script)
                if os.path.exists(script_path) and not os.access(script_path, os.X_OK):
                    raise PackagerError(
                        f"{script} script found in {self.request['scripts']} but it is "
                        "not executable!"
                    )
            self.log.debug("scripts ok")
        self.log.info("Packaging request verified")

    def copy_pkgroot(self):
        """Copy pkgroot to temporary directory."""

        self.log.debug("Copying package root")

        self.tmproot = tempfile.mkdtemp()
        self.tmp_pkgroot = os.path.join(self.tmproot, self.name)
        os.mkdir(self.tmp_pkgroot)
        os.chmod(self.tmp_pkgroot, 0o1775)
        os.chown(self.tmp_pkgroot, 0, 80)
        try:
            p = subprocess.Popen(
                ("/usr/bin/ditto", self.request["pkgroot"], self.tmp_pkgroot),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            (_, err) = p.communicate()
        except OSError as e:
            raise PackagerError(
                f"ditto execution failed with error code {e.errno}: {e.strerror}"
            )
        if p.returncode != 0:
            raise PackagerError(
                f"Couldn't copy pkgroot from {self.request['pkgroot']} to "
                f"{self.tmp_pkgroot}: {' '.join(str(err).split())}"
            )

        self.log.info(f"Package root copied to {self.tmp_pkgroot}")

    def apply_chown(self):
        """Change owner and group, and permissions if the 'mode' key was set."""

        self.log.debug("Applying chown")

        def verify_relative_valid_path(root, path):
            if len(path) < 1:
                raise PackagerError("Empty chown path")

            checkpath = root
            parts = path.split(os.sep)
            for part in parts:
                if part in (".", ".."):
                    raise PackagerError(". and .. is not allowed in chown path")
                checkpath = os.path.join(checkpath, part)
                relpath = checkpath[len(root) + 1 :]
                if not os.path.exists(checkpath):
                    raise PackagerError(f"chown path {relpath} does not exist")
                if os.path.islink(checkpath):
                    raise PackagerError(f"chown path {relpath} is a soft link")

        for entry in self.request["chown"]:
            self.log.debug("Let's check the path!")
            self.log.debug(entry["path"])
            # Check path.
            verify_relative_valid_path(self.tmp_pkgroot, entry["path"])
            # Check user.
            if isinstance(entry["user"], str):
                try:
                    uid = pwd.getpwnam(entry["user"]).pw_uid
                except KeyError:
                    raise PackagerError(f"Unknown chown user {entry['user']}")
            else:
                uid = int(entry["user"])
            if uid < 0:
                raise PackagerError(f"Invalid uid {uid}")
            # Check group.
            if isinstance(entry["group"], str):
                try:
                    gid = grp.getgrnam(entry["group"]).gr_gid
                except KeyError:
                    raise PackagerError(f"Unknown chown group {entry['group']}")
            else:
                gid = int(entry["group"])
            if gid < 0:
                raise PackagerError(f"Invalid gid {gid}")

            self.log.info(
                f"Setting owner and group of {entry['path']} to {entry['user']}:"
                f"{entry['group']}"
            )

            # If an absolute path is passed in entry["path"], os.path.join
            # will not join it to the tmp_pkgroot. We need to strip out
            # the leading / to make sure we only touch the pkgroot.
            chownpath = os.path.join(self.tmp_pkgroot, entry["path"].lstrip("/"))
            if "mode" in list(entry.keys()):
                chmod_present = True
            else:
                chmod_present = False
            if os.path.isfile(chownpath):
                os.lchown(chownpath, uid, gid)
                if chmod_present:
                    self.log.info(f"Setting mode of {entry['path']} to {entry['mode']}")
                    os.chmod(chownpath, int(entry["mode"], 8))
            else:
                for (dirpath, dirnames, filenames) in os.walk(chownpath):
                    try:
                        os.lchown(dirpath, uid, gid)
                    except OSError as e:
                        raise PackagerError(f"Can't lchown {dirpath}: {e}")
                    for path_entry in dirnames + filenames:
                        path = os.path.join(dirpath, path_entry)
                        try:
                            os.lchown(path, uid, gid)
                            if chmod_present:
                                os.chmod(path, int(entry["mode"], 8))
                        except OSError as e:
                            raise PackagerError(f"Can't lchown {path}: {e}")

        self.log.info("Chown applied")

    def random_string(self, length):
        rand = os.urandom(int((length + 1) / 2))
        randstr = "".join(["%02x" % ord(c) for c in str(rand)])
        return randstr[:length]

    def make_component_property_list(self):
        """Use pkgutil --analyze to build a component property list; then
        turn off package relocation"""
        self.component_plist = os.path.join(self.tmproot, "component.plist")
        try:
            p = subprocess.Popen(
                (
                    "/usr/bin/pkgbuild",
                    "--analyze",
                    "--root",
                    self.tmp_pkgroot,
                    self.component_plist,
                ),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            (_, err) = p.communicate()
        except OSError as e:
            raise PackagerError(
                f"pkgbuild execution failed with error code {e.errno}: {e.strerror}"
            )
        if p.returncode != 0:
            raise PackagerError(
                f"pkgbuild failed with exit code {p.returncode}: "
                f"{' '.join(str(err).split())}"
            )
        try:
            with open(self.component_plist, "rb") as f:
                plist = plistlib.load(f)
        except BaseException:
            raise PackagerError(f"Couldn't read {self.component_plist}")
        # plist is an array of dicts, iterate through
        for bundle in plist:
            if bundle.get("BundleIsRelocatable"):
                bundle["BundleIsRelocatable"] = False
        try:
            with open(self.component_plist, "wb") as f:
                plist = plistlib.dump(plist, f)
        except BaseException:
            raise PackagerError(f"Couldn't write {self.component_plist}")

    def create_pkg(self):
        self.log.info("Creating package")
        if self.request["pkgtype"] != "flat":
            raise PackagerError(f"Unsupported pkgtype {self.request['pkgtype']}")

        pkgname = self.request["pkgname"] + ".pkg"
        pkgpath = os.path.join(self.request["pkgdir"], pkgname)

        # Remove existing pkg if it exists and is owned by uid.
        if os.path.exists(pkgpath):
            try:
                self.log.info("Checking if package is owned by uid")
                if os.lstat(pkgpath).st_uid != self.uid:
                    raise PackagerError(
                        f"Existing pkg {pkgpath} not owned by {self.uid}"
                    )
                if os.path.islink(pkgpath) or os.path.isfile(pkgpath):
                    os.remove(pkgpath)
                else:
                    shutil.rmtree(pkgpath)
            except OSError as e:
                raise PackagerError(
                    f"Can't remove existing pkg {pkgpath}: {e.strerror}"
                )
        self.log.info("Creating random name")
        # Use a temporary name while building.
        temppkgname = (
            f"autopkgtmp-{self.random_string(16)}-{self.request['pkgname']}.pkg"
        )
        temppkgpath = os.path.join(self.request["pkgdir"], temppkgname)
        self.log.info("Starting cmd try block")
        # Wrap package building in try/finally to remove temporary package if
        # it fails.
        try:
            # make a pkgbuild cmd
            cmd = [
                "/usr/bin/pkgbuild",
                "--root",
                self.tmp_pkgroot,
                "--identifier",
                self.request["id"],
                "--version",
                self.request["version"],
                "--ownership",
                "preserve",
                "--component-plist",
                self.component_plist,
            ]
            if self.request["infofile"]:
                cmd.extend(["--info", self.request["infofile"]])
            if self.request["scripts"]:
                cmd.extend(["--scripts", self.request["scripts"]])
            cmd.append(temppkgpath)

            # Execute pkgbuild.
            self.log.info("Sending package build command")
            try:
                p = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                (_, err) = p.communicate()
            except OSError as e:
                raise PackagerError(
                    f"pkgbuild execution failed with error code {e.errno}: {e.strerror}"
                )
            if p.returncode != 0:
                raise PackagerError(
                    f"pkgbuild failed with exit code {p.returncode}: "
                    f"{' '.join(str(err).split())}"
                )
            self.log.info("Changing name and owner")
            # Change to final name and owner.
            os.rename(temppkgpath, pkgpath)
            os.chown(pkgpath, self.uid, self.gid)

            self.log.info(f"Created package at {pkgpath}")
            return pkgpath

        finally:
            # Remove temporary package.
            try:
                os.remove(temppkgpath)
            except OSError as e:
                if e.errno != 2:
                    self.log.warn(
                        f"Can't remove temporary package at {temppkgpath}: {e.strerror}"
                    )

    def cleanup(self):
        """Clean up resources."""

        if self.tmproot:
            shutil.rmtree(self.tmproot)
