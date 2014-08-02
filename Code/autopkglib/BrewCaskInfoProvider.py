#!/usr/bin/python
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


import re
import urllib2

from autopkglib import Processor, ProcessorError

__all__ = ["BrewCaskInfoProvider"]


class BrewCaskInfoProvider(Processor):
    description = ("Provides crowd-sourced URL and version info from thousands of "
                    "applications listed in brew-cask: "
                    "https://github.com/caskroom/homebrew-cask. See available apps: "
                    "https://github.com/caskroom/homebrew-cask/tree/master/Casks")
    input_variables = {
        "cask_name": {
            "required": True,
            "description": ("Name of cask to fetch, as would be given to the 'brew' command. "
                            "Example: 'audacity'")
        }
    }
    output_variables = {
        "url": {
            "description": "URL for the Cask's download.",
        },
        "version": {
            "description": ("Version info from formula. Depending on the nature of the formula "
                            "and stability of the URL, this might be simply 'latest'. It's "
                            "provided here for convenience in the recipe.")
        }
    }

    __doc__ = description


    def parse_formula(self, formula):
        """Return a dict containing attributes of the formula, ie. 'url', 'version', etc.
        parsed from the formula .rb file."""
        attrs = {}
        regex = r"  (?P<attr>.+) '(?P<value>.+)'"
        for line in formula.splitlines():
            match = re.match(regex, line)
            if match:
                attrs[match.group("attr")] = match.group("value")
        if not attrs:
            raise ProcessorError("Could not parse formula!")
        return attrs


    def main(self):
        github_raw_baseurl = "https://raw.githubusercontent.com/caskroom/homebrew-cask/master/Casks"
        cask_url = "%s/%s.rb" % (github_raw_baseurl, self.env["cask_name"])
        try:
            urlobj = urllib2.urlopen(cask_url)
        except urllib2.HTTPError as e:
            raise ProcessorError("Error opening URL %s: %s"
                % (cask_url, e))

        formula_data = urlobj.read()
        parsed = self.parse_formula(formula_data)

        if not "url" in parsed.keys():
            raise ProcessorError("No 'url' parsed from Formula!")
        self.env["url"] = parsed["url"]

        if "version" in parsed.keys():
            self.env["version"] = parsed["version"]
        else:
            self.env["version"] = ""

        self.output("Got URL %s from for cask '%s':"
            % (self.env["url"], self.env["cask_name"]))


if __name__ == "__main__":
    processor = BrewCaskInfoProvider()
    processor.execute_shell()
