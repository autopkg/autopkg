import os
import plistlib
import shutil

from autopkglib import ProcessorError


class AutoPkgLib:
    def __init__(self, munki_repo, repo_subdirectory):
        self.munki_repo = munki_repo
        self.repo_subdirectory = repo_subdirectory

    def make_catalog_db(self):
        """Reads the 'all' catalog and returns a dict we can use like a
        database"""

        all_items_path = os.path.join(self.munki_repo, "catalogs", "all")
        if not os.path.exists(all_items_path):
            # might be an error, or might be a brand-new empty repo
            catalogitems = []
        else:
            try:
                with open(all_items_path, "rb") as f:
                    catalogitems = plistlib.load(f)
            except OSError as err:
                raise ProcessorError(
                    f"Error reading 'all' catalog from Munki repo: {err}"
                )

        pkgid_table = {}
        app_table = {}
        installer_item_table = {}
        hash_table = {}
        checksum_table = {}
        files_table = {}

        itemindex = -1
        for item in catalogitems:
            itemindex = itemindex + 1
            name = item.get("name", "NO NAME")
            vers = item.get("version", "NO VERSION")

            if name == "NO NAME" or vers == "NO VERSION":
                # skip this item
                continue

            # add to hash table
            if "installer_item_hash" in item:
                if not item["installer_item_hash"] in hash_table:
                    hash_table[item["installer_item_hash"]] = []
                hash_table[item["installer_item_hash"]].append(itemindex)

            # add to installer item table
            if "installer_item_location" in item:
                installer_item_name = os.path.basename(item["installer_item_location"])
                if installer_item_name not in installer_item_table:
                    installer_item_table[installer_item_name] = {}
                if vers not in installer_item_table[installer_item_name]:
                    installer_item_table[installer_item_name][vers] = []
                installer_item_table[installer_item_name][vers].append(itemindex)

            # add to table of receipts
            for receipt in item.get("receipts", []):
                try:
                    if "packageid" in receipt and "version" in receipt:
                        pkgid = receipt["packageid"]
                        pkgvers = receipt["version"]
                        if pkgid not in pkgid_table:
                            pkgid_table[pkgid] = {}
                        if pkgvers not in pkgid_table[pkgid]:
                            pkgid_table[pkgid][pkgvers] = []
                        pkgid_table[pkgid][pkgvers].append(itemindex)
                except TypeError:
                    # skip this receipt
                    continue

            # add to table of installed applications
            for install in item.get("installs", []):
                try:
                    if install.get("type") in ("application", "bundle"):
                        if "path" in install:
                            if "version_comparison_key" in install:
                                app_version = install[install["version_comparison_key"]]
                            else:
                                app_version = install["CFBundleShortVersionString"]
                            if install["path"] not in app_table:
                                app_table[install["path"]] = {}
                            if vers not in app_table[install["path"]]:
                                app_table[install["path"]][app_version] = []
                            app_table[install["path"]][app_version].append(itemindex)
                    if install.get("type") == "file":
                        if "path" in install:
                            if "md5checksum" in install:
                                cksum = install["md5checksum"]

                                if cksum not in list(checksum_table.keys()):
                                    checksum_table[cksum] = []

                                checksum_table[cksum].append(
                                    {"path": install["path"], "index": itemindex}
                                )
                            else:
                                path = install["path"]

                                if path not in list(files_table.keys()):
                                    files_table[path] = []

                                files_table[path].append(
                                    {"path": install["path"], "index": itemindex}
                                )

                except (TypeError, KeyError):
                    # skip this item
                    continue

        pkgdb = {}
        pkgdb["hashes"] = hash_table
        pkgdb["receipts"] = pkgid_table
        pkgdb["applications"] = app_table
        pkgdb["installer_items"] = installer_item_table
        pkgdb["checksums"] = checksum_table
        pkgdb["files"] = files_table
        pkgdb["items"] = catalogitems

        return pkgdb

    def copy_pkg_to_repo(self, pkginfo, pkg_path):
        """Copies an item to the appropriate place in the repo.
        If pkg_path is a path within the repo/pkgs directory, copies nothing.
        Renames the item if an item already exists with that name.
        Returns the relative path to the item.
        uninstaller_pkg should be True if the item is an uninstaller (Adobe).
        """

        item_version = pkginfo.get("version")

        if not os.path.exists(self.munki_repo):
            raise ProcessorError(f"Munki repo not available at {self.munki_repo}.")

        destination_path = os.path.join(self.munki_repo, "pkgs", self.repo_subdirectory)
        if not os.path.exists(destination_path):
            try:
                os.makedirs(destination_path)
            except OSError as err:
                raise ProcessorError(
                    f"Could not create {destination_path}: {err.strerror}"
                )

        item_name = os.path.basename(pkg_path)
        destination_pathname = os.path.join(destination_path, item_name)

        if pkg_path == destination_pathname:
            # we've been asked to 'import' an item already in the repo.
            # just return the relative path
            return os.path.join(self.repo_subdirectory, item_name)

        if item_version:
            name, ext = os.path.splitext(item_name)
            if not name.endswith(item_version):
                # add the version number to the end of
                # the item name
                item_name = f"{name}-{item_version}{ext}"
                destination_pathname = os.path.join(destination_path, item_name)

        index = 0
        name, ext = os.path.splitext(item_name)
        while os.path.exists(destination_pathname):
            # try appending numbers until we have a unique name
            index += 1
            item_name = f"{name}__{index}{ext}"
            destination_pathname = os.path.join(destination_path, item_name)

        try:
            shutil.copy(pkg_path, destination_pathname)
        except OSError as err:
            raise ProcessorError(
                f"Can't copy {pkg_path} to {destination_pathname}: " f"{err.strerror}"
            )

        return os.path.join(self.munki_repo, "pkgs", self.repo_subdirectory, item_name)

    def copy_pkginfo_to_repo(self, pkginfo, file_extension="plist"):
        """Saves pkginfo to munki_repo_path/pkgsinfo/subdirectory.
        Returns full path to the pkginfo in the repo."""
        # less error checking because we copy the installer_item
        # first and bail if it fails...
        destination_path = os.path.join(
            self.munki_repo, "pkgsinfo", self.repo_subdirectory
        )
        if not os.path.exists(destination_path):
            try:
                os.makedirs(destination_path)
            except OSError as err:
                raise ProcessorError(
                    f"Could not create {destination_path}: {err.strerror}"
                )

        if len(file_extension) > 0:
            file_extension = "." + file_extension.strip(".")
        pkginfo_name = f"{pkginfo['name']}-{pkginfo['version'].strip()}{file_extension}"
        pkginfo_path = os.path.join(destination_path, pkginfo_name)
        index = 0
        while os.path.exists(pkginfo_path):
            index += 1
            pkginfo_name = (
                f"{pkginfo['name']}-{pkginfo['version']}__{index}{file_extension}"
            )
            pkginfo_path = os.path.join(destination_path, pkginfo_name)

        try:
            with open(pkginfo_path, "wb") as f:
                plistlib.dump(pkginfo, f)
        except OSError as err:
            raise ProcessorError(
                f"Could not write pkginfo {pkginfo_path}: {err.strerror}"
            )
        return pkginfo_path
