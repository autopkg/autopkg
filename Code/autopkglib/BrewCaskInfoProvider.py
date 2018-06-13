#!/usr/bin/python
#
# Copyright 2013-2016 Timothy Sutton
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
"""See docstring for BrewCaskInfoProvider class"""

import re
import urllib2

from autopkglib import Processor, ProcessorError

__all__ = ["BrewCaskInfoProvider"]


class BrewCaskInfoProvider(Processor):
    # we dynamically set the docstring from the description (DRY), so:
    #pylint: disable=missing-docstring

    description = ("ATTENTION: This processor is deprecated, may not work "
                   "as expected with all known Casks, and may be removed "
                   "in a future release of AutoPkg. Description follows: "
                   "Provides crowd-sourced URL and version info from thousands "
                   "of applications listed in brew-cask: "
                   "https://github.com/caskroom/homebrew-cask. See available "
                   "apps: https://github.com/caskroom/homebrew-cask/tree/"
                   "master/Casks")
    input_variables = {
        "cask_name": {
            "required": True,
            "description": ("Name of cask to fetch, as would be given to the "
                            "'brew' command. Example: 'audacity'")
        }
    }
    output_variables = {
        "url": {
            "description": "URL for the Cask's download.",
        },
        "version": {
            "description": ("Version info from formula. Depending on the "
                            "nature of the formula and stability of the URL, "
                            "this might be simply 'latest'. It's provided "
                            "here for convenience in the recipe.")
        }
    }

    __doc__ = description


    def parse_formula(self, formula):
        """Return a dict containing attributes of the formula, ie. 'url',
        'version', etc. parsed from the formula .rb file."""
        #pylint: disable=no-self-use
        attrs = {}
        regex = r"^\s+(?P<attr>.+) [\'\"](?P<value>.+)[\'\"].*$"
        for line in formula.splitlines():
            match = re.match(regex, line)
            if match:
                attrs[match.group("attr")] = match.group("value")
        if not attrs:
            raise ProcessorError("Could not parse formula!")
        return attrs

    def interpolate_vars(self, attrs):
        """Return a copy of the dictionary of attributes parsed from the
        Cask, with variables substituted. Currently we only expect this
        to be used in 'url', which may contain Ruby-style substitutions
        of '#{version}' within."""
        newattrs = attrs.copy()
        for key, value in newattrs.items():
            match = re.search("#{(.+?)}", value)
            if match:
                subbed_key = match.groups()[0]
                self.output("Substituting value '%s' in %s: '%s'" % (
                    subbed_key, key, value))
                newattrs[key] = re.sub("#{%s}" % subbed_key,
                                       newattrs[subbed_key],
                                       newattrs[key])
        return newattrs

    def main(self):
        self.output("WARNING: BrewCaskInfoProvider is deprecated and may be "
                    "removed in a future AutoPkg release.")
        github_raw_baseurl = (
            "https://raw.githubusercontent.com/caskroom/homebrew-cask/master/"
            "Casks")
        cask_url = "%s/%s.rb" % (github_raw_baseurl, self.env["cask_name"])
        try:
            urlobj = urllib2.urlopen(cask_url)
        except urllib2.HTTPError as err:
            raise ProcessorError("Error opening URL %s: %s"% (cask_url, err))

        formula_data = urlobj.read()
        parsed = self.parse_formula(formula_data)
        parsed = self.interpolate_vars(parsed)

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
    PROCESSOR = BrewCaskInfoProvider()
    PROCESSOR.execute_shell()
