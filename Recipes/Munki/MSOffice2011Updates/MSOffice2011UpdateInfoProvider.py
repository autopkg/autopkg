#!/usr/bin/env python
#
# Copyright 2013 Greg Neagle
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


import plistlib
import re
import urllib2

from distutils.version import LooseVersion
from operator import itemgetter

from autopkglib.Processor import Processor, ProcessorError


__all__ = ["MSOffice2011UpdateInfoProvider"]


BASE_URL = "http://www.microsoft.com/mac/autoupdate/0409MSOf14.xml"
MUNKI_UPDATE_NAME = "Office2011_update"

class MSOffice2011UpdateInfoProvider(Processor):
    description = ("Provides a download URL for the latest Flip4Mac "
                   "release.")
    input_variables = {
        "base_url": {
            "required": False,
            "description": "Default is %s" % BASE_URL,
        },
        "version": {
            "required": False,
            "description": "Update version number. Defaults to latest.",
        },
        "munki_update_name": {
            "required": False,
            "description": 
                ("Name for the update in Munki repo. Defaults to "
                 "'%s'" % MUNKI_UPDATE_NAME),
        },
    }
    output_variables = {
        "url": {
            "description": "URL to the latest Office 2011 update.",
        },
        "additional_pkginfo": {
            "description": 
                "Some pkginfo fields extracted from the Microsoft metadata.",
        },
    }
    __doc__ = description
    
    def sanityCheckTriggerCondition(self, item):
        """Raises an exeception if the Trigger Condition
        for an update doesn't match the expected format"""
        if not item["Trigger Condition"] == ["and", "MCP"]:
            raise ProcessorError(
                "Unexpected Trigger Condition in item %s: %s" 
                % (item["Title"], item["Trigger Condition"]))
    
    def getRequiresFromUpdateItem(self, item):
        """Attempts to determine what earlier updates are
        required by this update"""
        
        def compare_versions(a, b):
            """Internal comparison function for use with sorting"""
            return cmp(LooseVersion(a), LooseVersion(b))
        
        self.sanityCheckTriggerCondition(item)
        munki_update_name = self.env.get("munki_update_name", MUNKI_UPDATE_NAME)
        mcp_versions = item.get(
            "Triggers", {}).get("MCP", {}).get("Versions", [])
        if not mcp_versions:
            return None
        # Versions array is already sorted in current 0409MSOf14.xml,
        # may be no need to sort; but we should just to be safe...
        mcp_versions.sort(compare_versions)
        if mcp_versions[0] == "14.0.0":
            # works with original Office release, so no requires array
            return None
        return ["%s-%s" % (munki_update_name, mcp_versions[0])]
    
    def getInstallsItemsFromUpdateItem(self, item):
        """Attempts to parse the Triggers to create an installs item"""
        self.sanityCheckTriggerCondition(item)
        triggers = item.get("Triggers", {})
        paths = [triggers[key].get("File") for key in triggers.keys()]
        if "Office/MicrosoftComponentPlugin.framework" in paths:
            # use MicrosoftComponentPlugin.framework as installs item
            installs_item = {
                "CFBundleShortVersionString": self.getVersion(item),
                "CFBundleVersion": self.getVersion(item),
                "path": ("/Applications/Microsoft Office 2011/"
                         "Office/MicrosoftComponentPlugin.framework"),
                "type": "bundle",
                "version_comparison_key": "CFBundleShortVersionString"
            }
            return [installs_item]
        return None
    
    def getVersion(self, item):
        """Extracts the version of the update item."""
        # currently relies on the item having a title in the format
        # "Office 2011 x.y.z Update"
        TITLE_START = "Office 2011 "
        TITLE_END = " Update"
        title = item.get("Title", "")
        version_str = title.replace(TITLE_START, "").replace(TITLE_END, "")
        return version_str
    
    def valueToOSVersionString(self, value):
        if isinstance(value, int):
            version_str = hex(value)[2:]
        elif isinstance(value, basestring):
            if value.startswith('0x'):
                version_str = value[2:]
        # OS versions are encoded as hex:
        # 4184 = 0x1058 = 10.5.8
        # not sure how 10.4.11 would be encoded;
        # guessing 0x104B ?
        major = 0
        minor = 0
        patch = 0
        try:
            if len(version_str) == 1:
                major = int(version_str[0])
            if len(version_str) > 1:
                major = int(version_str[0:2])
            if len(version_str) > 2:
                minor = int(version_str[2], 16)
            if len(version_str) > 3:
                patch = int(version_str[3], 16)
        except ValueError, err:
            raise ProcessorError("Unexpected value in version: %s" % value)
        return "%s.%s.%s" % (major, minor, patch)

    def get_mso2011update_info(self):
        base_url = self.env.get("base_url", BASE_URL)
        version_str = self.env.get("version")
        # Get metadata URL
        try:
            f = urllib2.urlopen(base_url)
            data = f.read()
            f.close()
        except BaseException as e:
            raise ProcessorError("Can't download %s: %s" % (base_url, e))
        
        metadata = plistlib.readPlistFromString(data)
        if not version_str:
            # Office 2011 update metadata is a list of dicts.
            # we need to sort by date.
            sorted_metadata = sorted(metadata, key=itemgetter('Date'))
            # choose the last item, which should be most recent.
            item = sorted_metadata[-1]
        else:
            # we've been told to find a specific version. Unfortunately, the
            # Office2011 update metadata items don't have a version attibute.
            # The version is only in text in the update's Title. So we look for 
            # that...
            # Titles are in the format "Office 2011 x.y.z Update"
            padded_version_str = " " + version_str + " "
            matched_items = [item for item in metadata 
                            if padded_version_str in item["Title"]]
            if len(matched_items) != 1:
                raise ProcessorError(
                    "Could not find version %s in update metadata" 
                    % version_str)
            item = matched_items[0]
        
        self.env["url"] = item["Location"]
        # now extract useful info from the rest of the metadata that could
        # be used in a pkginfo
        pkginfo = {}
        pkginfo["description"] = "<html>%s</html>" % item["Short Description"]
        pkginfo["display_name"] = item["Title"]
        max_os = self.valueToOSVersionString(item['Max OS'])
        min_os = self.valueToOSVersionString(item['Min OS'])
        if max_os != "0.0.0":
            pkginfo["maximum_os_version"] = max_os
        if min_os != "0.0.0":
            pkginfo["minimum_os_version"] = min_os
        installs_items = self.getInstallsItemsFromUpdateItem(item)
        if installs_items:
            pkginfo["installs"] = installs_items
        requires = self.getRequiresFromUpdateItem(item)
        if requires:
            pkginfo["requires"] = requires
        pkginfo['name'] = self.env.get("munki_update_name", MUNKI_UPDATE_NAME)
        self.env["additional_pkginfo"] = pkginfo

    def main(self):
        """Get information about an update"""
        self.get_mso2011update_info()


if __name__ == "__main__":
    processor = MSOffice2011UpdateInfoProvider()
    processor.execute_shell()
