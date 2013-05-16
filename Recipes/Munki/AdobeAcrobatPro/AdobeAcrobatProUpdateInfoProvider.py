#!/usr/bin/env python
#
# Copyright 2013 Timothy Sutton
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


import urllib2
import re

from autopkglib import Processor, ProcessorError
from plistlib import readPlistFromString

__all__ = ["AdobeAcrobatProUpdateInfoProvider"]


MUNKI_UPDATE_NAME_DEFAULT = "AdobeAcrobatPro{MAJREV}_Update"
VERSION_DEFAULT = "latest"

META_BASE_URL = "https://armmf.adobe.com/arm-manifests/mac"
MANIFEST_URL_TEMPLATE = META_BASE_URL + "/{MAJREV}/manifest_url_template.txt"
DL_BASE_URL = "http://armdl.adobe.com"

_url_vars = {
    "PROD": "com_adobe_Acrobat_Pro",
    "PROD_ARCH": "univ"
}
supported_vers = ['9', '10', '11']

class AdobeAcrobatProUpdateInfoProvider(Processor):
    description = "Provides URL to the latest Adobe Acrobat Pro release."
    input_variables = {
        "major_version": {
            "required": True,
            "description": ("Major version. Currently supports: %s"
                            % ", ".join(supported_vers))
        },
        "version": {
            "required": False,
            "description": "Update version number. Defaults to %s." % VERSION_DEFAULT,
        },
        "munki_update_name": {
            "required": False,
            "description": ("Name for the update in Munki. Defaults to "
                            "%s" % MUNKI_UPDATE_NAME_DEFAULT)
        }
    }
    output_variables = {
        "url": {
            "description": "URL to the latest Adobe Reader release.",
        },
        "version": {
            "description": "Version for this update.",
        },
        "additional_pkginfo": {
            "description": ("A pkginfo possibly containing additional 'requires' items.")
        }
    }

    __doc__ = description

    def process_url_vars(self, url):
        for var in _url_vars.keys():
            subbed_url = url.replace(r"{%s}" % var, _url_vars[var])
            url = subbed_url
        return subbed_url

    def get_url_response(self, url):
        try:
            url_handle = urllib2.urlopen(url)
            response = url_handle.read()
            url_handle.close()
        except BaseException as e:
            raise ProcessorError("Can't read response from URL %s: %s" % (url, e))
        return response

    def get_manifest_data(self, manifest_plist_url):
        manifest_plist_response = self.get_url_response(manifest_plist_url)
        try:
            manifest_data = readPlistFromString(manifest_plist_response)
        except BaseException as e:
            raise ProcessorError("Can't parse manifest plist at %s: %s" % (manifest_plist_url, e))

        if "PatchURL" not in manifest_data.keys():
            raise ProcessorError("Manifest plist key '%s' not found at %s: %s"
                                 % ("PatchURL", manifest_plist_url, e))

        return manifest_data

    def get_acrobat_metadata(self, major_version, get_version):
        '''Returns a tuple: (url, version, previous_required_version)'''

        template_url = self.process_url_vars(MANIFEST_URL_TEMPLATE)
        template_response = self.get_url_response(template_url)

        if get_version != "latest":
            # /{MAJREV}/latest/{PROD}_{PROD_ARCH}.plist -->
            # /{MAJREV}/get_version/{PROD}_{PROD_ARCH}.plist
            template_response = re.sub("\d+\.\d+\.\d+", get_version, template_response)
        
        manifest_url = self.process_url_vars(META_BASE_URL + template_response)
        manifest_data = self.get_manifest_data(manifest_url)


        composed_dl_url = DL_BASE_URL + manifest_data["PatchURL"]
        version = manifest_data["BuildNumber"]
        # If there's a previous required version, store that version for later use
        if manifest_data.get("PreviousURLTemplate","") != "noTemplate":
            prev_manifest_url = self.process_url_vars(
                                META_BASE_URL + manifest_data["PreviousURLTemplate"])
            prev_manifest_data = self.get_manifest_data(prev_manifest_url)
            prev_version = prev_manifest_data["BuildNumber"]
        return (composed_dl_url,version,prev_version)

    def main(self):
        major_version = self.env["major_version"]
        get_version = self.env.get("version", VERSION_DEFAULT)
        if major_version not in supported_vers:
            raise ProcessorError("major_version %s not one of those supported: %s"
                                % (major_version, ", ".join(supported_vers)))

        global _url_vars
        _url_vars["MAJREV"] = major_version

        munki_update_name = self.env.get("munki_update_name", "")
        if not munki_update_name:
            munki_update_name = self.process_url_vars(MUNKI_UPDATE_NAME_DEFAULT)
        (url, version, prev_version) = self.get_acrobat_metadata(major_version,
                                                                get_version=get_version)

        new_pkginfo = {}
        # if our required version is something other than a base version
        # should match a version ending in '.0.0', '.00.0', '.00.00', etc.
        if not re.search("\.[0]+\.[0]+", prev_version):
            new_pkginfo["requires"] = ["%s-%s" % (munki_update_name, prev_version)]
            self.output("Update requires previous version: %s" % prev_version)
        self.env["additional_pkginfo"] = new_pkginfo

        self.env["url"] = url
        self.output("Found URL %s" % self.env["url"])

if __name__ == "__main__":
    processor = AdobeAcrobatProUpdateInfoProvider()
    processor.execute_shell()
