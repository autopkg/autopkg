# Copyright 2014 Greg Neagle
# Borrowing liberally from Munki's munkilib/installer.py et al
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
"""Copies stuff from a diskimage to the current boot disk. Really useful for
drag-n-drop vendor disk images so we don't have to package it first to install
it"""

import os
import re
import stat
import subprocess

import xattr

PRIVATE_TMP = "/private/tmp"


class ItemCopierError(Exception):
    """Base error for ItemCopier errors"""

    pass


def is_path_under(path, root):
    """Return True if path is at or below root."""
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        return False


class ItemCopier:
    """Copies items from a mount_point to the current root volume"""

    def __init__(self, log, socket, request):
        """Arguments:

        log     A logger instance.
        socket  The socket for the requesting object
        request A request in plist format.
        """

        self.log = log
        self.socket = socket
        self.request = request
        self.mountpoint = None

    def reject_parent_reference(self, path, field):
        """Reject empty paths and paths with parent-directory references."""
        if not isinstance(path, str) or not path:
            raise ItemCopierError(f"{field} is required")
        parts = [part for part in path.replace("\\", "/").split("/") if part]
        if ".." in parts:
            raise ItemCopierError(
                f"{field} may not contain parent-directory references"
            )

    def verify_relative_path(self, path, field):
        """Verify a request path that must be relative."""
        self.reject_parent_reference(path, field)
        if os.path.isabs(path):
            raise ItemCopierError(f"{field} must be relative")

    def verify_mode(self, mode):
        """Reject mode changes that would set setuid or setgid bits."""
        mode = str(mode).strip()
        if not mode:
            raise ItemCopierError("mode is required")

        if re.fullmatch(r"[0-7]+", mode):
            if int(mode, 8) & (stat.S_ISUID | stat.S_ISGID):
                raise ItemCopierError("mode may not set setuid or setgid bits")
            return

        mode = mode.lower()
        if re.search(r"(^|,)[ugoa]*\+[^,]*s", mode) or re.search(
            r"(^|,)[ugoa]*=[^,]*s", mode
        ):
            raise ItemCopierError("mode may not set setuid or setgid bits")

    def verify_mountpoint(self):
        """Verify and return the real mount point path."""
        mountpoint = self.request["mount_point"]
        self.reject_parent_reference(mountpoint, "mount_point")
        mountpoint = os.path.realpath(mountpoint)
        if not is_path_under(mountpoint, os.path.realpath(PRIVATE_TMP)):
            raise ItemCopierError("mount_point is not in an allowed location")
        if not os.path.isdir(mountpoint):
            raise ItemCopierError(
                f"mount_point {self.request['mount_point']} is not a directory"
            )
        if not os.path.ismount(mountpoint):
            raise ItemCopierError("mount_point is not a mounted volume")
        return mountpoint

    def paths_for_item(self, item):
        """Verify item paths and return source, destination dir, and final path."""
        mountpoint = self.mountpoint or self.verify_mountpoint()

        source_itemname = item.get("source_item")
        self.verify_relative_path(source_itemname, "source_item")
        source_itempath = os.path.normpath(os.path.join(mountpoint, source_itemname))
        real_source_itempath = os.path.realpath(source_itempath)
        if not is_path_under(real_source_itempath, mountpoint):
            raise ItemCopierError(
                f"Source item {source_itemname} resolves outside the mount point"
            )
        if not os.path.exists(source_itempath):
            raise ItemCopierError(f"Source item {source_itemname} does not exist!")

        destpath = item.get("destination_path")
        self.reject_parent_reference(destpath, "destination_path")
        if not os.path.isabs(destpath):
            raise ItemCopierError("destination_path must be absolute")
        destpath = os.path.realpath(destpath)

        dest_itemname = item.get("destination_item")
        if dest_itemname:
            self.verify_relative_path(dest_itemname, "destination_item")
            target_name = os.path.basename(dest_itemname)
        else:
            target_name = os.path.basename(source_itemname)
        if not target_name:
            raise ItemCopierError("Destination item name is required")

        full_destpath = os.path.realpath(os.path.join(destpath, target_name))
        return source_itempath, destpath, full_destpath

    def verify_request(self) -> None:
        """Make sure copy request has everything we need"""
        self.log.debug("Verifying copy_from_dmg request")
        for key in ["mount_point", "items_to_copy"]:
            if key not in self.request:
                raise ItemCopierError(f"No {key} in request")
        self.mountpoint = self.verify_mountpoint()
        for item in self.request["items_to_copy"]:
            if "source_item" not in item:
                raise ItemCopierError("Missing source_item in items_to_copy item")
            if "destination_path" not in item:
                raise ItemCopierError("Missing destination_path in items_to_copy item")
            self.paths_for_item(item)
            self.verify_mode(item.get("mode", "o-w"))

    def copy_items(self) -> bool:
        """copies items from the mountpoint to the startup disk
        Returns True if no issues; raises ItemCopierError otherwise.

        self.request['items_to_copy'] is a list of dictionaries;
        each item should contain source_path and destination_path;
        may optionally include:
        destination_item to rename the item on copy
        user, group and mode to explicitly set those items
        """
        for item in self.request["items_to_copy"]:
            # get itemname
            source_itemname = item.get("source_item")
            if not source_itemname:
                raise ItemCopierError("Missing name of item to copy!")

            source_itempath, destpath, full_destpath = self.paths_for_item(item)
            self.verify_mode(item.get("mode", "o-w"))

            # check destination path
            if not os.path.exists(destpath):
                self.log.info(
                    "Destination path %s does not exist, will determine "
                    "owner/permissions from parent",
                    destpath,
                )
                parent_path = destpath
                new_paths = []

                # work our way back up to an existing path and build a list
                while not os.path.exists(parent_path):
                    new_paths.insert(0, parent_path)
                    parent_path = os.path.split(parent_path)[0]

                # stat the parent, get uid/gid/mode
                parent_stat = os.stat(parent_path)
                parent_uid, parent_gid = parent_stat.st_uid, parent_stat.st_gid
                parent_mode = stat.S_IMODE(parent_stat.st_mode)

                # make the new tree with the parent's mode
                try:
                    os.makedirs(destpath, mode=parent_mode)
                except OSError:
                    raise ItemCopierError(
                        f"There was an IO error in creating the path {destpath}!"
                    )
                except Exception:
                    raise ItemCopierError(
                        f"There was an unknown error in creating the path %{destpath}"
                    )

                # chown each new dir
                for new_path in new_paths:
                    os.chown(new_path, parent_uid, parent_gid)

            # remove item if it already exists
            if os.path.exists(full_destpath):
                self.log.info("Removing existing %s", full_destpath)
                retcode = subprocess.call(["/bin/rm", "-rf", full_destpath])
                if retcode:
                    raise ItemCopierError(
                        f"Error removing existing {full_destpath}: {retcode}"
                    )

            # all tests passed, OK to copy
            self.log.info("Copying %s to %s", source_itemname, full_destpath)
            self.socket.send(
                f"STATUS:Copying {source_itemname} to {full_destpath}\n".encode()
            )
            retcode = subprocess.call(
                ["/bin/cp", "-pR", source_itempath, full_destpath]
            )
            if retcode:
                raise ItemCopierError(
                    f"Error copying {source_itempath} to {full_destpath}: {retcode}"
                )

            # set owner
            user = item.get("user", "root")
            self.log.info("Setting owner for '%s' to '%s'", full_destpath, user)
            retcode = subprocess.call(["/usr/sbin/chown", "-R", user, full_destpath])
            if retcode:
                raise ItemCopierError(f"Error setting owner for {full_destpath}")

            # set group
            group = item.get("group", "admin")
            self.log.info("Setting group for '%s' to '%s'", full_destpath, group)
            retcode = subprocess.call(["/usr/bin/chgrp", "-R", group, full_destpath])
            if retcode:
                raise ItemCopierError(f"Error setting group for {full_destpath}")

            # set mode
            mode = item.get("mode", "o-w")
            self.log.info("Setting mode for '%s' to '%s'", full_destpath, mode)
            retcode = subprocess.call(["/bin/chmod", "-R", mode, full_destpath])
            if retcode:
                raise ItemCopierError(f"Error setting mode for {full_destpath}")

            # remove com.apple.quarantine attribute from copied item
            try:
                if "com.apple.quarantine" in xattr.xattr(full_destpath).list():
                    xattr.xattr(full_destpath).remove("com.apple.quarantine")
            except Exception as err:
                raise ItemCopierError(f"Error removing xattr: {err}")
        return True

    def copy(self) -> None:
        """Main method."""
        try:
            self.verify_request()
            self.copy_items()
        except Exception as err:
            raise ItemCopierError(err)
