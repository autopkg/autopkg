#!/usr/bin/env python
#
# Copyright 2010 Per Olofsson
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
import stat
import shutil
import subprocess
import re
import tempfile
import pwd
import grp


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
    re_id      = re.compile(r'^[a-z0-9][a-z0-9 ]*$', re.I)
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
            return self.create_pkg()
        finally:
            self.cleanup()
    
    def verify_request(self):
        """Verify that the request is valid."""
        
        self.log.debug("Verifying packaging request")
        
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
        try:
            with open(self.request.infofile, "rb") as f:
                pass
        except (IOError, OSError) as e:
            raise PackagerError("Can't open infofile: %s" % e)
        self.log.debug("infofile ok")
        
        if self.request.resources:
            try:
                os.listdir(self.request.resources)
            except OSError as e:
                raise PackagerError("Can't list Resources: %s" % e)
            self.log.debug("resources ok")
        
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
        """Change owner and group."""
        
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
            if os.path.isfile(chownpath):
                os.lchown(chownpath, uid, gid)
            else:
                for (dirpath,
                     dirnames,
                     filenames) in os.walk(chownpath):
                    try:
                        os.lchown(dirpath, uid, gid)
                    except OSError as e:
                        raise PackagerError("Can't lchown %s: %s" % (dirpath, e))
                    for entry in dirnames + filenames:
                        path = os.path.join(dirpath, entry)
                        try:
                            os.lchown(path, uid, gid)
                        except OSError as e:
                            raise PackagerError("Can't lchown %s: %s" % (path, e))
        
        self.log.info("Chown applied")
    
    def random_string(self, len):
        rand = os.urandom((len + 1) / 2)
        randstr = "".join(["%02x" % ord(c) for c in rand])
        return randstr[:len]
    
    def create_pkg(self):
        self.log.info("Creating package")
        if self.request.pkgtype == "bundle":
            target = "10.4"
        else:
            target = "10.5"
        
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
            # Execute packagemaker.
            try:
                p = subprocess.Popen(("/Developer/usr/bin/packagemaker",
                                      "--root", self.tmp_pkgroot,
                                      "--info", self.request.infofile,
                                      "--resources", self.request.resources,
                                      "--id", self.request.id,
                                      "--version", self.request.version,
                                      "--no-recommend",
                                      "--no-relocate",
                                      "--target", target,
                                      "--out", temppkgpath),
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
                (out, err) = p.communicate()
            except OSError as e:
                raise PackagerError("packagemaker execution failed with error code %d: %s" % (
                                     e.errno, e.strerror))
            if p.returncode != 0:
                raise PackagerError("packagemaker failed with exit code %d: %s" % (
                                     p.returncode,
                                     " ".join(str(err).split())))
            
            # Change to final name and owner.
            os.rename(temppkgpath, pkgpath)
            if os.path.isdir(pkgpath):
                for (dirpath, dirnames, filenames) in os.walk(pkgpath):
                    os.lchown(dirpath, self.uid, self.gid)
                    for dirname in dirnames:
                        os.lchown(os.path.join(dirpath, dirname), self.uid, self.gid)
                    for filename in filenames:
                        os.lchown(os.path.join(dirpath, filename), self.uid, self.gid)
            else:
                os.chown(pkgpath, self.uid, self.gid)
            
            self.log.info("Created package at %s" % pkgpath)
            return pkgpath
        
        finally:
            # Remove temporary package.
            try:
                if os.path.exists(temppkgpath):
                    if os.path.islink(temppkgpath) or os.path.isfile(temppkgpath):
                        os.remove(temppkgpath)
                    else:
                        shutil.rmtree(temppkgpath)
            except OSError:
                self.log.warn("Can't remove temporary package at %s" % temppkgpath)
    
    def cleanup(self):
        """Clean up resources."""
        
        if self.tmproot:
            shutil.rmtree(self.tmproot)
    
