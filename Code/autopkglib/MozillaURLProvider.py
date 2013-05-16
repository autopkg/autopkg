#!/usr/bin/env python
#
# Copyright 2010 Per Olofsson, 2013 Greg Neagle
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


__all__ = ["MozillaURLProvider"]


MOZ_BASE_URL = "http://download-origin.cdn.mozilla.net/pub/mozilla.org/"
               #"firefox/releases")
re_dmg = re.compile(r'a[^>]* href="(?P<filename>[^"]+\.dmg)"')
re_locale = re.compile(r'^(?P<lang>[a-z]{2,3})([\-_](?P<region>[A-Z]{2}))?$')


class MozillaURLProvider(Processor):
    description = "Provides URL to the latest Firefox release."
    input_variables = {
        "product_name": {
            "required": True,
            "description": 
                "Product to fetch URL for. One of 'firefox', 'thunderbird'.",
        },
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
            "description": "Default is '%s." % MOZ_BASE_URL,
        },
    }
    output_variables = {
        "url": {
            "description": "URL to the latest Mozilla product release.",
        },
    }
    
    __doc__ = description
    
    def get_mozilla_dmg_url(self, base_url, product_name, build, locale):
        # Allow locale as both en-US and en_US.
        m = re_locale.search(locale)
        if m:
            locale = "%s-%s" % (m.group("lang").lower(),
                                m.group("region").upper())
        
        # Construct download directory URL.
        build_dir = build.lower()
        
        index_url = "/".join(
            (base_url, product_name, "releases", build_dir, "mac", locale))
        #print >>sys.stderr, index_url
        
        # Read HTML index.
        try:
            f = urllib2.urlopen(index_url)
            html = f.read()
            f.close()
        except BaseException as e:
            raise ProcessorError("Can't download %s: %s" % (index_url, e))
        
        # Search for download link.
        m = re_dmg.search(html)
        if not m:
            raise ProcessorError(
                "Couldn't find %s download URL in %s" 
                % (product_name, index_url))
        
        # Return URL.
        return "/".join(
            (base_url, product_name, "releases", build_dir, "mac", locale,
             m.group("filename")))
    
    def main(self):
        # Determine product_name, build, locale, and base_url.
        product_name = self.env["product_name"]
        build = self.env.get("build", "latest")
        locale = self.env.get("locale", "en_US")
        base_url = self.env.get("base_url", MOZ_BASE_URL)
        
        self.env["url"] = self.get_mozilla_dmg_url(
                                        base_url, product_name, build, locale)
        self.output("Found URL %s" % self.env["url"])
    

if __name__ == "__main__":
    processor = MozillaURLProvider()
    processor.execute_shell()
    
