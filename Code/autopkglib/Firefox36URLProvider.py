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


import re
import urllib2

from Processor import Processor, ProcessorError


__all__ = ["Firefox36URLProvider"]


FF_BASE_URL = "http://releases.mozilla.org/pub/mozilla.org/firefox/releases/latest-3.6"
re_firefox_dmg = re.compile(r'a[^>]* href="(?P<filename>Firefox[^"]+\.dmg)"')
re_locale = re.compile(r'^(?P<lang>[a-z]{2,3})([\-_](?P<region>[A-Z]{2}))?$')


class Firefox36URLProvider(Processor):
    description = "Provides URL to the latest Firefox release."
    input_variables = {
        "build": {
            "required": False,
            "description": "Which build to download, 'mac' or 'mac64'.",
        },
        "locale": {
            "required": False,
            "description": "Which localization to download, default is 'en_US'.",
        },
        "base_url": {
            "required": False,
            "description": "Default is 'http://releases.mozilla.org/pub/mozilla.org/firefox/releases/latest'.",
        },
    }
    output_variables = {
        "url": {
            "description": "URL to the latest Firefox release.",
        },
    }
    
    __doc__ = description
    
    def get_firefox_dmg_url(self, base_url, build, locale):
        # Allow locale as both en-US and en_US.
        m = re_locale.search(locale)
        if m:
            locale = "%s-%s" % (m.group("lang").lower(), m.group("region").upper())
        
        # Construct download directory URL.
        index_url = "/".join((base_url, build, locale))
        #print >>sys.stderr, index_url
        
        # Read HTML index.
        try:
            f = urllib2.urlopen(index_url)
            html = f.read()
            f.close()
        except BaseException as e:
            raise ProcessorError("Can't download %s: %s" % (index_url, e))
        
        # Search for download link.
        m = re_firefox_dmg.search(html)
        if not m:
            raise ProcessorError("Couldn't find Firefox download URL in %s" % index_url)
        
        # Return URL.
        return "/".join((base_url, build, locale, m.group("filename")))
    
    def main(self):
        # Determine build, locale, and base_url.
        if "build" in self.env:
            build = self.env["build"]
        else:
            build = "mac"
        if "locale" in self.env:
            locale = self.env["locale"]
        else:
            locale = "en_US"
        if "base_url" in self.env:
            base_url = self.env["base_url"]
        else:
            base_url = FF_BASE_URL
        
        self.env["url"] = self.get_firefox_dmg_url(base_url, build, locale)
    

if __name__ == '__main__':
    processor = Firefox36URLProvider()
    processor.execute_shell()
    
