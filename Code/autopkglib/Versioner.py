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


from Processor import Processor, ProcessorError

from Foundation import NSData, \
                       NSPropertyListSerialization, \
                       NSPropertyListMutableContainers, \
                       NSPropertyListXMLFormat_v1_0


__all__ = ["Versioner"]


class Versioner(Processor):
    description = ("Returns version information from a plist")
    input_variables = {
        "input_plist_path": {
            "required": True,
            "description": 
                ("File path to a plist."),
        },
        "plist_version_key": {
            "required": False,
            "description": 
                ("Which plist key to use; defaults to "
                "CFBundleShortVersionString"),
        },
    }
    output_variables = {
        "version": {
            "description": "Version of the item.",
        },
    }
    
    __doc__ = description
    
    def readPlist(self, filepath):
        """
        Read a .plist file from filepath.  Return the unpacked root object
        (which is usually a dictionary).
        """
        plistData = NSData.dataWithContentsOfFile_(filepath)
        dataObject, plistFormat, error = \
            NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(
                         plistData, NSPropertyListMutableContainers, None, None)
        if error:
            errmsg = "%s in file %s" % (error, filepath)
            raise ProcessorError(errmsg)
        else:
            return dataObject
            
    def main(self):
        plist = self.readPlist(self.env["input_plist_path"])
        version_key = self.env.get(
            "plist_version_key", "CFBundleShortVersionString")
        self.env['version'] = plist.get(version_key, "UNKNOWN_VERSION")
        
        
if __name__ == '__main__':
    processor = Versioner()
    processor.execute_shell()

    