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


import re
import urllib2

from autopkglib import Processor, ProcessorError


__all__ = ["ThunderbirdURLProvider"]


TB_BASE_URL = ("http://download-origin.cdn.mozilla.net/pub/mozilla.org/"
               "thunderbird/releases")
re_thunderbird_dmg = re.compile(
                        r'a[^>]* href="(?P<filename>Thunderbird[^"]+\.dmg)"')
re_locale = re.compile(r'^(?P<lang>[a-z]{2,3})([\-_](?P<region>[A-Z]{2}))?$')


class ThunderbirdURLProvider(Processor):
    description = "Provides URL to the latest Thunderbird release."
    input_variables = {
        "build": {
            "required": False,
            "description": ("Which build to download. Examples: 'latest', "
                "'latest-10.0esr', 'latest-esr', 'latest-beta'."),
        },
        "locale": {
            "required": False,
            "description": 
                    "Which localization to download, default is 'en_US'.",
        },
        "base_url": {
            "required": False,
            "description": ("Default is '%s'.") % TB_BASE_URL,
        },
    }
    output_variables = {
        "url": {
            "description": "URL to the latest Thunderbird release.",
        },
    }
    
    __doc__ = description
    
    def get_thunderbird_dmg_url(self, base_url, build, locale):
        # Allow locale as both en-US and en_US.
        m = re_locale.search(locale)
        if m:
            locale = "%s-%s" % (m.group("lang").lower(),
                                m.group("region").upper())
        
        # Construct download directory URL.
        build_dir = build.lower()
        
        index_url = "/".join((base_url, build_dir, "mac", locale))
        #print >>sys.stderr, index_url
        
        # Read HTML index.
        try:
            f = urllib2.urlopen(index_url)
            html = f.read()
            f.close()
        except BaseException as e:
            raise ProcessorError("Can't download %s: %s" % (index_url, e))
        
        # Search for download link.
        m = re_thunderbird_dmg.search(html)
        if not m:
            raise ProcessorError(
                "Couldn't find Thunderbird download URL in %s" % index_url)
        
        # Return URL.
        return "/".join(
            (base_url, build_dir, "mac", locale, m.group("filename")))
    
    def main(self):
        # Determine build, locale, and base_url.
        if "build" in self.env:
            build = self.env["build"]
        else:
            build = "latest"
        if "locale" in self.env:
            locale = self.env["locale"]
        else:
            locale = "en_US"
        if "base_url" in self.env:
            base_url = self.env["base_url"]
        else:
            base_url = TB_BASE_URL
        
        self.env["url"] = self.get_thunderbird_dmg_url(base_url, build, locale)
        self.output("Found URL %s" % self.env["url"])
    

if __name__ == "__main__":
    processor = ThunderbirdURLProvider()
    processor.execute_shell()
    
