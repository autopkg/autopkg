#!/usr/local/autopkg/python
#
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
import stat
import subprocess

import xattr


class ItemCopierError(Exception):
    """Base error for ItemCopier errors"""

    pass


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

    def verify_request(self):
        """Make sure copy request has everything we need"""
        self.log.debug("Verifying copy_from_dmg request")
        for key in ["mount_point", "items_to_copy"]:
            if key not in self.request:
                raise ItemCopierError(f"No {key} in request")
        for item in self.request["items_to_copy"]:
            if "source_item" not in item:
                raise ItemCopierError("Missing source_item in items_to_copy item")
            if "destination_path" not in item:
                raise ItemCopierError("Missing destination_path in items_to_copy item")

    def copy_items(self):
        """copies items from the mountpoint to the startup disk
        Returns 0 if no issues; some error code otherwise.

        self.request['items_to_copy'] is a list of dictionaries;
        each item should contain source_path and destination_path;
        may optionally include:
        destination_item to rename the item on copy
        user, group and mode to explictly set those items
        """
        mountpoint = self.request["mount_point"]
        for item in self.request["items_to_copy"]:

            # get itemname
            source_itemname = item.get("source_item")
            dest_itemname = item.get("destination_item")
            if not source_itemname:
                raise ItemCopierError("Missing name of item to copy!")

            # check source path
            source_itempath = os.path.join(mountpoint, source_itemname)
            if not os.path.exists(source_itempath):
                raise ItemCopierError(f"Source item {source_itemname} does not exist!")

            # check destination path
            destpath = item.get("destination_path")
            if not os.path.exists(destpath):
                self.log.info(
                    f"Destination path {destpath} does not exist, will determine "
                    "owner/permissions from parent"
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

            # setup full destination path using 'destination_item', if supplied
            if dest_itemname:
                full_destpath = os.path.join(destpath, os.path.basename(dest_itemname))
            else:
                full_destpath = os.path.join(
                    destpath, os.path.basename(source_itemname)
                )

            # remove item if it already exists
            if os.path.exists(full_destpath):
                self.log.info(f"Removing existing {full_destpath}")
                retcode = subprocess.call(["/bin/rm", "-rf", full_destpath])
                if retcode:
                    raise ItemCopierError(
                        f"Error removing existing {full_destpath}: {retcode}"
                    )

            # all tests passed, OK to copy
            self.log.info(f"Copying {source_itemname} to {full_destpath}")
            self.socket.send(
                f"STATUS:Copying {source_itemname.encode('UTF-8')} to "
                f"{full_destpath.encode('UTF-8')}\n"
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
            self.log.info(f"Setting owner for '{full_destpath}' to '{user}'")
            retcode = subprocess.call(["/usr/sbin/chown", "-R", user, full_destpath])
            if retcode:
                raise ItemCopierError(f"Error setting owner for {full_destpath}")

            # set group
            group = item.get("group", "admin")
            self.log.info(f"Setting group for '{full_destpath}' to '{group}'")
            retcode = subprocess.call(["/usr/bin/chgrp", "-R", group, full_destpath])
            if retcode:
                raise ItemCopierError(f"Error setting group for {full_destpath}")

            # set mode
            mode = item.get("mode", "o-w")
            self.log.info(f"Setting mode for '{full_destpath}' to '{mode}'")
            retcode = subprocess.call(["/bin/chmod", "-R", mode, full_destpath])
            if retcode:
                raise ItemCopierError(f"Error setting mode for {full_destpath}")

            # remove com.apple.quarantine attribute from copied item
            try:
                if "com.apple.quarantine" in xattr.xattr(full_destpath).list():
                    xattr.xattr(full_destpath).remove("com.apple.quarantine")
            except BaseException as err:
                raise ItemCopierError(f"Error removing xattr: {err}")
            return True

    def copy(self):
        """Main method."""
        try:
            self.verify_request()
            self.copy_items()
        except BaseException as err:
            raise ItemCopierError(err)
