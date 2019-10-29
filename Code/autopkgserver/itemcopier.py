#!/Library/AutoPkg/Python3/Python.framework/Versions/Current/bin/python3
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


class ItemCopier(object):
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
                raise ItemCopierError("No %s in request" % key)
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
                raise ItemCopierError(
                    "Source item %s does not exist!" % source_itemname
                )

            # check destination path
            destpath = item.get("destination_path")
            if not os.path.exists(destpath):
                self.log.info(
                    "Destination path %s does not exist, will determine "
                    "owner/permissions from parent" % destpath
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
                except IOError:
                    raise ItemCopierError(
                        "There was an IO error in creating the path %s!" % destpath
                    )
                except Exception:
                    raise ItemCopierError(
                        "There was an unknown error in creating the path %s!" % destpath
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
                self.log.info("Removing existing %s" % full_destpath)
                retcode = subprocess.call(["/bin/rm", "-rf", full_destpath])
                if retcode:
                    raise ItemCopierError(
                        "Error removing existing %s: %s" % (full_destpath, retcode)
                    )

            # all tests passed, OK to copy
            self.log.info("Copying %s to %s" % (source_itemname, full_destpath))
            self.socket.send(
                "STATUS:Copying %s to %s\n"
                % (source_itemname.encode("UTF-8"), full_destpath.encode("UTF-8"))
            )
            retcode = subprocess.call(
                ["/bin/cp", "-pR", source_itempath, full_destpath]
            )
            if retcode:
                raise ItemCopierError(
                    "Error copying %s to %s: %s"
                    % (source_itempath, full_destpath, retcode)
                )

            # set owner
            user = item.get("user", "root")
            self.log.info("Setting owner for '%s' to '%s'" % (full_destpath, user))
            retcode = subprocess.call(["/usr/sbin/chown", "-R", user, full_destpath])
            if retcode:
                raise ItemCopierError("Error setting owner for %s" % full_destpath)

            # set group
            group = item.get("group", "admin")
            self.log.info("Setting group for '%s' to '%s'" % (full_destpath, group))
            retcode = subprocess.call(["/usr/bin/chgrp", "-R", group, full_destpath])
            if retcode:
                raise ItemCopierError("Error setting group for %s" % full_destpath)

            # set mode
            mode = item.get("mode", "o-w")
            self.log.info("Setting mode for '%s' to '%s'" % (full_destpath, mode))
            retcode = subprocess.call(["/bin/chmod", "-R", mode, full_destpath])
            if retcode:
                raise ItemCopierError("Error setting mode for %s" % full_destpath)

            # remove com.apple.quarantine attribute from copied item
            try:
                if "com.apple.quarantine" in xattr.xattr(full_destpath).list():
                    xattr.xattr(full_destpath).remove("com.apple.quarantine")
            except BaseException as err:
                raise ItemCopierError("Error removing xattr: %s" % err)
            return True

    def copy(self):
        """Main method."""
        try:
            self.verify_request()
            self.copy_items()
        except BaseException as err:
            raise ItemCopierError(err)
