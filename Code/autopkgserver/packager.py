#!/usr/bin/python
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
import stat
import shutil
import subprocess
import re
import tempfile
import pwd
import grp

from xml.parsers.expat import ExpatError

__all__ = [
    'Packager',
    'PackagerError'
]


class PackagerError(Exception):
    pass

class Packager(object):
    """Create an Apple installer package.

    Must be run as root."""

    re_pkgname = re.compile(r'^[a-z0-9][a-z0-9 ._\-]*$', re.I)
    re_id      = re.compile(r'^[a-z0-9]([a-z0-9 \-]*[a-z0-9])?$', re.I)
    re_version = re.compile(r'^[a-z0-9_ ]*[0-9][a-z0-9_ ]*$', re.I)

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
                raise PackagerError("Can't stat %s: %s" % (path, e))
            if info.st_uid != uid:
                raise PackagerError("%s isn't owned by %d" % (path, uid))
            if stat.S_ISLNK(info.st_mode):
                raise PackagerError("%s is a soft link" % path)
            if not stat.S_ISDIR(info.st_mode):
                raise PackagerError("%s is not a directory" % path)


        def cmd_output(cmd):
            '''Outputs a stdout, stderr tuple from command output using a Popen'''
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate()
            if err:
                self.log.debug("WARNING: errors from command '%s':" % ", ".join(cmd))
                self.log.debug(err)
            return (out, err)


        def get_mounts():
            '''Returns a list of mounted volume paths as reported by diskutil.'''
            out, err = cmd_output([
                "/usr/sbin/diskutil",
                "list",
                "-plist"])
            try:
                du_list = plistlib.readPlistFromString(out)
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
                self.log.debug(
                    "Missing AllDisksAndPartitions key in diskutil output")
            return list(vols)


        def check_ownerships_enabled(path):
            '''Return True if 'ignore ownerships' is not set on the volume on which
            'path' resides, False if otherwise. We warn and return True on
            unexpected behavior.'''

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
                self.log.debug("Found mounted volumes: %s" % ", ".join(mounts))
            else:
                self.log.debug(("WARNING: No mountpoints could be determined for "
                             "checking ownerships."))
                return True

            # find the mountpoint that has our path
            mount_for_path = None
            for mount in mounts:
                if path.startswith(mount):
                    mount_for_path = mount
                    break
            if not mount_for_path:
                self.log.debug(("WARNING: Checking disk ownerships for path '%s' "
                             "failed. Attempting to continue.."
                             % path))
                return True

            # look for 'ignore ownerships' setting on the disk
            # if 'GlobalPermissionsEnabled' is true, ownerships are _not_ ignored
            self.log.debug("Checking disk ownerships for mount '%s'.." % mount_for_path)
            out, err = cmd_output([
                "/usr/sbin/diskutil",
                "info",
                "-plist",
                mount_for_path])
            try:
                du_info = plistlib.readPlistFromString(out)
            except ExpatError:
                self.log.debug("WARNING: Error parsing diskutil output.")
                self.log.debug(err)
                return True

            if not "GlobalPermissionsEnabled" in du_info:
                self.log.debug("WARNING: Couldn't read 'ignore ownerships' "
                    "setting for mount point '%s'. Attempting to "
                    "continue." % mount_for_path)
                return True

            if not du_info["GlobalPermissionsEnabled"]:
                return False
            else:
                return True


        self.log.debug("Verifying packaging request")
        # Check that a disk-based pkgroot isn't somewhere where 'ignore ownerships'
        # is set.
        if not check_ownerships_enabled(self.request.pkgroot):
            raise PackagerError(
                ("'Ignore ownerships' is set on the disk where pkgroot '%s' "
                "was set, and packaging cannot continue. Ownerships must "
                "be enabled on the volume where a package is to be built.")
                % self.request.pkgroot)


        # Check owner and type of directories.
        verify_dir_and_owner(self.request.pkgroot, self.uid)
        self.log.debug("pkgroot ok")
        verify_dir_and_owner(self.request.pkgdir, self.uid)
        self.log.debug("pkgdir ok")

        # Check name.
        if len(self.request.pkgname) > 80:
            raise PackagerError("Package name too long")
        if not self.re_pkgname.search(self.request.pkgname):
            raise PackagerError("Invalid package name")
        if self.request.pkgname.lower().endswith(".pkg"):
            raise PackagerError("Package name mustn't include '.pkg'")
        self.log.debug("pkgname ok")

        # Check ID.
        if len(self.request.id) > 80:
            raise PackagerError("Package id too long")
        components = self.request.id.split(".")
        if len(components) < 2:
            raise PackagerError("Invalid package id")
        for comp in components:
            if not self.re_id.search(comp):
                raise PackagerError("Invalid package id")
        self.log.debug("id ok")

        # Check version.
        if len(self.request.version) > 40:
            raise PackagerError("Version too long")
        components = self.request.version.split(".")
        if len(components) < 1:
            raise PackagerError("Invalid version")
        for comp in components:
            if not self.re_version.search(comp):
                raise PackagerError("Invalid version")
        self.log.debug("version ok")

        # Make sure infofile and resources exist and can be read.
        if self.request.infofile:
            try:
                with open(self.request.infofile, "rb") as f:
                    pass
            except (IOError, OSError) as e:
                raise PackagerError("Can't open infofile: %s" % e)
            self.log.debug("infofile ok")

        # Make sure scripts is a directory and its contents
        # are executable.
        if self.request.scripts:
            if self.request.pkgtype == "bundle":
                raise PackagerError(
                    "Installer scripts are not supported with "
                    "bundle package types.")
            if not os.path.isdir(self.request.scripts):
                raise PackagerError(
                    "Can't find scripts directory: %s"
                    % self.request.scripts)
            for script in ["preinstall", "postinstall"]:
                script_path = os.path.join(self.request.scripts, script)
                if os.path.exists(script_path) \
                    and not os.access(script_path, os.X_OK):
                    raise PackagerError(
                        "%s script found in %s but it is not executable!"
                        % (script, self.request.scripts))
            self.log.debug("scripts ok")

        # FIXME: resources temporarily unsupported.
        #if self.request.resources:
        #    try:
        #        os.listdir(self.request.resources)
        #    except OSError as e:
        #        raise PackagerError("Can't list Resources: %s" % e)
        #    self.log.debug("resources ok")

        # Leave chown verification until after the pkgroot has been copied.

        self.log.info("Packaging request verified")

    def copy_pkgroot(self):
        """Copy pkgroot to temporary directory."""

        name = self.request.pkgname

        self.log.debug("Copying package root")

        self.tmproot = tempfile.mkdtemp()
        self.tmp_pkgroot = os.path.join(self.tmproot, self.name)
        os.mkdir(self.tmp_pkgroot)
        os.chmod(self.tmp_pkgroot, 01775)
        os.chown(self.tmp_pkgroot, 0, 80)
        try:
            p = subprocess.Popen(("/usr/bin/ditto",
                                  self.request.pkgroot,
                                  self.tmp_pkgroot),
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            out, err = p.communicate()
        except OSError as e:
            raise PackagerError("ditto execution failed with error code %d: %s" % (
                                 e.errno, e.strerror))
        if p.returncode != 0:
            raise PackagerError("Couldn't copy pkgroot from %s to %s: %s" % (
                                 self.request.pkgroot,
                                 self.tmp_pkgroot,
                                 " ".join(str(err).split())))

        self.log.info("Package root copied to %s" % self.tmp_pkgroot)

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
                relpath = checkpath[len(root) + 1:]
                if not os.path.exists(checkpath):
                    raise PackagerError("chown path %s does not exist" % relpath)
                if os.path.islink(checkpath):
                    raise PackagerError("chown path %s is a soft link" % relpath)

        for entry in self.request.chown:
            # Check path.
            verify_relative_valid_path(self.tmp_pkgroot, entry.path)
            # Check user.
            if isinstance(entry.user, str):
                try:
                    uid = pwd.getpwnam(entry.user).pw_uid
                except KeyError:
                    raise PackagerError("Unknown chown user %s" % entry.user)
            else:
                uid = int(entry.user)
            if uid < 0:
                raise PackagerError("Invalid uid %d" % uid)
            # Check group.
            if isinstance(entry.group, str):
                try:
                    gid = grp.getgrnam(entry.group).gr_gid
                except KeyError:
                    raise PackagerError("Unknown chown group %s" % entry.group)
            else:
                gid = int(entry.group)
            if gid < 0:
                raise PackagerError("Invalid gid %d" % gid)

            self.log.info("Setting owner and group of %s to %s:%s" % (
                     entry.path,
                     str(entry.user),
                     str(entry.group)))

            chownpath = os.path.join(self.tmp_pkgroot, entry.path)
            if "mode" in entry.keys():
                chmod_present = True
            else:
                chmod_present = False
            if os.path.isfile(chownpath):
                os.lchown(chownpath, uid, gid)
                if chmod_present:
                    self.log.info("Setting mode of %s to %s" % (
                        entry.path,
                        str(entry.mode)))
                    os.chmod(chownpath, int(entry.mode, 8))
            else:
                for (dirpath,
                     dirnames,
                     filenames) in os.walk(chownpath):
                    try:
                        os.lchown(dirpath, uid, gid)
                    except OSError as e:
                        raise PackagerError("Can't lchown %s: %s" % (dirpath, e))
                    for path_entry in dirnames + filenames:
                        path = os.path.join(dirpath, path_entry)
                        try:
                            os.lchown(path, uid, gid)
                            if chmod_present:
                                os.chmod(path, int(entry.mode, 8))
                        except OSError as e:
                            raise PackagerError("Can't lchown %s: %s" % (path, e))

        self.log.info("Chown applied")

    def random_string(self, len):
        rand = os.urandom((len + 1) / 2)
        randstr = "".join(["%02x" % ord(c) for c in rand])
        return randstr[:len]

    def make_component_property_list(self):
        """Use pkgutil --analyze to build a component property list; then
        turn off package relocation"""
        self.component_plist = os.path.join(self.tmproot, "component.plist")
        try:
            p = subprocess.Popen(("/usr/bin/pkgbuild",
                                  "--analyze",
                                  "--root", self.tmp_pkgroot,
                                  self.component_plist),
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
            (out, err) = p.communicate()
        except OSError as e:
            raise PackagerError(
                "pkgbuild execution failed with error code %d: %s"
                % (e.errno, e.strerror))
        if p.returncode != 0:
            raise PackagerError(
                "pkgbuild failed with exit code %d: %s"
                % (p.returncode, " ".join(str(err).split())))
        try:
            plist = plistlib.readPlist(self.component_plist)
        except BaseException as err:
            raise PackagerError("Couldn't read %s" % self.component_plist)
        # plist is an array of dicts, iterate through
        for bundle in plist:
            if bundle.get("BundleIsRelocatable"):
                bundle["BundleIsRelocatable"] = False
        try:
            plistlib.writePlist(plist, self.component_plist)
        except BaseException as err:
            raise PackagerError("Couldn't write %s" % self.component_plist)

    def create_pkg(self):
        self.log.info("Creating package")
        if self.request.pkgtype != "flat":
            raise PackagerError("Unsupported pkgtype %s" % (
                                repr(self.request.pkgtype)))

        pkgname = self.request.pkgname + ".pkg"
        pkgpath = os.path.join(self.request.pkgdir, pkgname)

        # Remove existing pkg if it exists and is owned by uid.
        if os.path.exists(pkgpath):
            try:
                if os.lstat(pkgpath).st_uid != self.uid:
                    raise PackagerError("Existing pkg %s not owned by %d" % (
                                         pkgpath, self.uid))
                if os.path.islink(pkgpath) or os.path.isfile(pkgpath):
                    os.remove(pkgpath)
                else:
                    shutil.rmtree(pkgpath)
            except OSError as e:
                raise PackagerError("Can't remove existing pkg %s: %s" % (
                                     pkgpath, e.strerror))

        # Use a temporary name while building.
        temppkgname = "autopkgtmp-%s-%s.pkg" % (self.random_string(16),
                                     self.request.pkgname)
        temppkgpath = os.path.join(self.request.pkgdir, temppkgname)

        # Wrap package building in try/finally to remove temporary package if
        # it fails.
        try:
            # make a pkgbuild cmd
            cmd = ["/usr/bin/pkgbuild",
                    "--root", self.tmp_pkgroot,
                    "--identifier", self.request.id,
                    "--version", self.request.version,
                    "--ownership", "preserve",
                    "--component-plist", self.component_plist]
            if self.request.infofile:
                cmd.extend(["--info", self.request.infofile])
            if self.request.scripts:
                cmd.extend(["--scripts", self.request.scripts])
            cmd.append(temppkgpath)

            # Execute pkgbuild.
            try:
                p = subprocess.Popen(cmd,
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
                (out, err) = p.communicate()
            except OSError as e:
                raise PackagerError(
                    "pkgbuild execution failed with error code %d: %s"
                    % (e.errno, e.strerror))
            if p.returncode != 0:
                raise PackagerError("pkgbuild failed with exit code %d: %s" % (
                                     p.returncode,
                                     " ".join(str(err).split())))

            # Change to final name and owner.
            os.rename(temppkgpath, pkgpath)
            os.chown(pkgpath, self.uid, self.gid)

            self.log.info("Created package at %s" % pkgpath)
            return pkgpath

        finally:
            # Remove temporary package.
            try:
                os.remove(temppkgpath)
            except OSError as e:
                if e.errno != 2:
                    self.log.warn("Can't remove temporary package at %s: %s" % (
                                  temppkgpath, e.strerror))

    def cleanup(self):
        """Clean up resources."""

        if self.tmproot:
            shutil.rmtree(self.tmproot)

