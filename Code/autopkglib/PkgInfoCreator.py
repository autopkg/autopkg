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


import os.path
import subprocess
import plistlib
import math
from xml.etree import ElementTree

from Processor import Processor, ProcessorError


__all__ = ["PkgInfoCreator"]


class PkgInfoCreator(Processor):
    description = "Creates an Info.plist file for a package."
    input_variables = {
        "template_path": {
            "required": True,
            "description": "An Info.plist template.",
        },
        "version": {
            "required": True,
            "description": "Version of the package.",
        },
        "pkgroot": {
            "required": True,
            "description": "Virtual root of the package.",
        },
        "infofile": {
            "required": True,
            "description": "Path to the info file to create.",
        },
        "pkgtype": {
            "required": True,
            "description": "'flat' or 'bundle'."
        }
    }
    output_variables = {
    }
    
    __doc__ = description
    
    def main(self):
        if self.env.pkgtype not in ("bundle", "flat"):
            raise ProcessorError("Unknown pkgtype %s" % self.env.pkgtype)
        template = self.load_template(self.env.template_path, self.env.pkgtype)
        if self.env.pkgtype == "bundle":
            self.create_bundle_info(template)
        else:
            self.create_flat_info(template)
    
    restartaction_to_postinstallaction = {
        "None": "none",
        "RecommendRestart": "restart",
        "RequireLogout": "logout",
        "RequireRestart": "restart",
        "RequireShutdown": "shutdown",
    }
    def convert_bundle_info_to_flat(self, info):
        pkg_info = ElementTree.Element("pkg-info")
        pkg_info.set("format-version", "2")
        for bundle, flat in (("IFPkgFlagDefaultLocation", "install-location"),
                             ("CFBundleShortVersionString", "version"),
                             ("CFBundleIdentifier", "identifier")):
            if bundle in info:
                pkg_info.set(flat, info[bundle])
        if "IFPkgFlagAuthorizationAction" in info:
            if info["IFPkgFlagAuthorizationAction"] == "RootAuthorization":
                pkg_info.set("auth", "root")
            else:
                pkg_info.set("auth", "none")
        if "IFPkgFlagRestartAction" in info:
            pkg_info.set("postinstall-action",
                self.restartaction_to_postinstallaction[info["IFPkgFlagRestartAction"]])
        
        payload = ElementTree.SubElement(pkg_info, "payload")
        if "IFPkgFlagInstalledSize" in info:
            payload.set("installKBytes", str(info["IFPkgFlagInstalledSize"]))
        
        return ElementTree.ElementTree(pkg_info)
    
    postinstallaction_to_restartaction = {
        "none": "None",
        "logout": "RequireLogout",
        "restart": "RequireRestart",
        "shutdown": "RequireShutdown",
    }
    def convert_flat_info_to_bundle(self, info):
        info = {
            #"CFBundleIdentifier": "com.adobe.pkg.FlashPlayer",
            "IFPkgFlagAllowBackRev": False,
            #"IFPkgFlagAuthorizationAction": "RootAuthorization",
            #"IFPkgFlagDefaultLocation": "/",
            "IFPkgFlagFollowLinks": True,
            "IFPkgFlagInstallFat": False,
            "IFPkgFlagIsRequired": False,
            "IFPkgFlagOverwritePermissions": False,
            "IFPkgFlagRelocatable": False,
            #"IFPkgFlagRestartAction": "None",
            "IFPkgFlagRootVolumeOnly": False,
            "IFPkgFlagUpdateInstalledLanguages": False,
            "IFPkgFormatVersion": 0.1,
        }
        
        pkg_info = info.getroot()
        if pkg_info.tag != "pkg-info":
            raise ProcessorError("PackageInfo template root isn't pkg-info")
        
        info["CFBundleShortVersionString"] = pkg_info.get("version", "")
        info["CFBundleIdentifier"] = pkg_info.get("identifier", "")
        info["IFPkgFlagDefaultLocation"] = pkg_info.get("install-location", "")
        if pkg_info.get("auth") == "root":
            info["IFPkgFlagAuthorizationAction"] = "RootAuthorization"
        else:
            raise ProcessorError("Don't know how to convert auth=%s to Info.plist format" % pkg_info.get("auth"))
        info["IFPkgFlagRestartAction"] = \
            self.postinstallaction_to_restartaction[pkg_info.get("postinstall-action", "none")]
        
        payload = ElementTree.SubElement(pkg_info, "payload")
        info["IFPkgFlagInstalledSize"] = payload.get("installKBytes", 0)
        
        return info
    
    def load_template(self, template_path, template_type):
        """Load a package info template in Info.plist or PackageInfo format."""
        
        if template_path.endswith(".plist"):
            # Try to load Info.plist in bundle format.
            try:
                info = plistlib.readPlist(self.env.template_path)
            except BaseException as e:
                raise ProcessorError("Malformed Info.plist template %s" % self.env.template_path)
            if template_type == "bundle":
                return info
            else:
                return self.convert_bundle_info_to_flat(info)
        else:
            # Try to load PackageInfo in flat format.
            try:
                info = ElementTree.parse(template_path)
            except BaseException as e:
                raise ProcessorError("Malformed PackageInfo template %s" % self.env.template_path)
            if template_type == "flat":
                return info
            else:
                return self.convert_flat_info_to_bundle(info)
    
    def get_pkgroot_size(self, pkgroot):
        """Return the size of pkgroot (in kilobytes) and the number of files."""
        
        size = 0
        nfiles = 0
        for (dirpath, dirnames, filenames) in os.walk(pkgroot):
            # Count the current directory and the number of files in it.
            nfiles += 1 + len(filenames)
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                # Add up file size rounded up to the nearest 4 kB, which
                # appears to match what du -sk returns, and what PackageMaker
                # uses.
                size += int(math.ceil(float(os.lstat(path).st_size) / 4096.0))
        
        return (size, nfiles)
    
    def create_flat_info(self, template):
        info = template
        
        pkg_info = info.getroot()
        if pkg_info.tag != "pkg-info":
            raise ProcessorError("PackageInfo root should be pkg-info")
        
        pkg_info.set("version", self.env.version)
        
        payload = pkg_info.find("payload")
        if payload is None:
            payload = ElementTree.SubElement(pkg_info, "payload")
        size, nfiles = self.get_pkgroot_size(self.env.pkgroot)
        payload.set("installKBytes", str(size))
        payload.set("numberOfFiles", str(nfiles))
        
        info.write(self.env.infofile)

    
    def create_bundle_info(self, template):
        info = template
        
        info["CFBundleShortVersionString"] = self.env.version
        ver = self.env.version.split(".")
        info["IFMajorVersion"] = ver[0]
        info["IFMinorVersion"] = ver[1]
        
        size, nfiles = self.get_pkgroot_size(self.env.pkgroot)
        info["IFPkgFlagInstalledSize"] = size
        
        try:
            plistlib.writePlist(info, self.env.infofile)
        except BaseException as e:
            raise ProcessorError("Couldn't write %s: %s" % (self.env.infofile, e))
    

if __name__ == '__main__':
    processor = PkgInfoCreator()
    processor.execute_shell()
    
