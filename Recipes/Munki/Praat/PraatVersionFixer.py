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
from Foundation import NSData, \
                       NSPropertyListSerialization, \
                       NSPropertyListXMLFormat_v1_0, \
                       NSPropertyListMutableContainers

from autopkglib import Processor, ProcessorError


__all__ = ["PraatVersionFixer"]


class PraatVersionFixer(Processor):
    description = "Fixes Praat version string."
    input_variables = {
        "app_path": {
            "required": True,
            "description": "Path to Praat.app.",
        },
    }
    output_variables = {
        "bundleid": {
            "description": "Bundle identifier of Praat.app.",
        },
        "version": {
            "description": "Version of Praat.app.",
        },
    }
    
    __doc__ = description
    
    def read_bundle_info(self, path):
        """Read Contents/Info.plist inside a bundle."""
        
        plistpath = os.path.join(path, "Contents", "Info.plist")
        info, format, error = \
            NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(
                NSData.dataWithContentsOfFile_(plistpath),
                NSPropertyListMutableContainers,
                None,
                None
            )
        if error:
            raise ProcessorError("Can't read %s: %s" % (plistpath, error))
        
        return info
    
    def write_bundle_info(self, info, path):
        """Write Contents/Info.plist inside a bundle."""
        
        plistpath = os.path.join(path, "Contents", "Info.plist")
        plist_data, error = \
            NSPropertyListSerialization.dataFromPropertyList_format_errorDescription_(
                info,
                NSPropertyListXMLFormat_v1_0,
                None
            )
        if error:
            raise ProcessorError("Can't serialize %s: %s" % (plistpath, error))
        
        if not plist_data.writeToFile_atomically_(plistpath, True):
            raise ProcessorError("Can't write %s" % (plistpath))
    
    def main(self):
        app_path = self.env["app_path"]
        info = self.read_bundle_info(app_path)
        self.env["bundleid"] = info["CFBundleIdentifier"]
        version = info["CFBundleShortVersionString"].replace("Praat ", "")
        info["CFBundleShortVersionString"] = version
        self.env["version"] = version
        self.write_bundle_info(info, app_path)
    

if __name__ == '__main__':
    processor = PraatVersionFixer()
    processor.execute_shell()
    
