#!/usr/bin/python
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
"""See docstring for PlistEditor class"""

from autopkglib import Processor, ProcessorError
import FoundationPlist


__all__ = ["PlistEditor"]


class PlistEditor(Processor):
    """Merges data with an input plist (which can be empty) and writes a new
    plist."""
    description = __doc__
    input_variables = {
        "input_plist_path": {
            "required": False,
            "description":
                ("File path to a plist; empty or undefined to start with "
                 "an empty plist."),
        },
        "output_plist_path": {
            "required": True,
            "description":
                "File path to a plist. Can be the same path as input_plist.",
        },
        "plist_data": {
            "required": True,
            "description":
                ("A dictionary of data to be merged with the data from the "
                 "input plist."),
        },
    }
    output_variables = {
    }

    __doc__ = description

    def read_plist(self, pathname):
        """reads a plist from pathname"""
        #pylint: disable=no-self-use
        if not pathname:
            return {}
        try:
            return FoundationPlist.readPlist(pathname)
        except Exception, err:
            raise ProcessorError(
                'Could not read %s: %s' % (pathname, err))

    def write_plist(self, data, pathname):
        """writes a plist to pathname"""
        #pylint: disable=no-self-use
        try:
            FoundationPlist.writePlist(data, pathname)
        except Exception, err:
            raise ProcessorError(
                'Could not write %s: %s' % (pathname, err))

    def main(self):
        # read original plist (or empty plist)
        working_plist = self.read_plist(self.env.get("input_plist_path"))

        # insert new data
        plist_data = self.env["plist_data"]
        for key in plist_data.keys():
            working_plist[key] = plist_data[key]

        # write changed plist
        self.write_plist(working_plist, self.env["output_plist_path"])
        self.output("Updated plist at %s" % self.env["output_plist_path"])

if __name__ == '__main__':
    PROCESSOR = PlistEditor()
    PROCESSOR.execute_shell()
