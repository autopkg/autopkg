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


__all__ = ["AdiumURLProvider"]


ADIUM_BASE_URL = "http://adium.im/?download=10.6"
re_adium_dmg = re.compile(r'CONTENT="\d+;URL=(?P<url>http://download.adium.im/Adium[^"]+\.dmg)"', re.I)


class AdiumURLProvider(Processor):
    description = "Provides URL to the latest Adium release."
    input_variables = {
        "base_url": {
            "required": False,
            "description": "Default is 'http://adium.im/?download=10.6'.",
        },
    }
    output_variables = {
        "url": {
            "description": "URL to the latest Adium release.",
        },
    }
    
    __doc__ = description
    
    def get_adium_dmg_url(self, base_url):
        # Read HTML index.
        try:
            f = urllib2.urlopen(base_url)
            html = f.read()
            f.close()
        except BaseException as e:
            raise ProcessorError("Can't download %s: %s" % (base_url, e))
        
        # Search for download link.
        m = re_adium_dmg.search(html)
        if not m:
            raise ProcessorError("Couldn't find Adium download URL in %s" % base_url)
        
        # Return URL.
        return m.group("url")
    
    def main(self):
        # Determine base_url.
        if "base_url" in self.env:
            base_url = self.env.base_url
        else:
            base_url = ADIUM_BASE_URL
        
        self.env["url"] = self.get_adium_dmg_url(base_url)
    

if __name__ == '__main__':
    processor = AdiumURLProvider()
    processor.execute_shell()
    

