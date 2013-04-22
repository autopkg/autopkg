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

from autopkglib import Processor, ProcessorError


__all__ = ["TheUnarchiverURLProvider"]


THEUNARCHIVER_BASE_URL = "http://wakaba.c3.cx/s/apps/unarchiver.html"
re_theunarchiver_zip = re.compile(r'class="download" href="(?P<url>http://theunarchiver.googlecode.com/files/TheUnarchiver[^"]+\.zip)"', re.I)


class TheUnarchiverURLProvider(Processor):
    description = "Provides URL to the latest release of The Unarchiver."
    input_variables = {
        "base_url": {
            "required": False,
            "description": "Default is 'http://wakaba.c3.cx/s/apps/unarchiver.html'.",
        },
    }
    output_variables = {
        "url": {
            "description": "URL to the latest release of The Unarchiver.",
        },
    }
    
    __doc__ = description
    
    def get_theunarchiver_zip_url(self, base_url):
        # Read HTML index.
        try:
            f = urllib2.urlopen(base_url)
            html = f.read()
            f.close()
        except BaseException as e:
            raise ProcessorError("Can't download %s: %s" % (base_url, e))
        
        # Search for download link.
        m = re_theunarchiver_zip.search(html)
        if not m:
            raise ProcessorError("Couldn't find The Unarchiver download URL in %s" % base_url)
        
        # Return URL.
        return m.group("url")
    
    def main(self):
        # Determine base_url.
        base_url = self.env.get('base_url', THEUNARCHIVER_BASE_URL)
        
        self.env["url"] = self.get_theunarchiver_zip_url(base_url)
        self.output("Found URL %s" % self.env["url"])
    

if __name__ == '__main__':
    processor = TheUnarchiverURLProvider()
    processor.execute_shell()
    

