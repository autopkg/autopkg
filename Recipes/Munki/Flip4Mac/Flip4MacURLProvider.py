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

from autopkglib.Processor import Processor, ProcessorError


__all__ = ["Flip4MacURLProvider"]


BASE_URL = "http://www.microsoft.com/mac/downloads"

re_download_link = re.compile(
    r'Flip4Mac Windows Media View</h3>\s+<p><a href="(?P<url>http://[^"]+)"')
    
re_ver2_dmg_link = re.compile(r'href="(?P<url>http://.*? 2[.0-9]*.dmg)"')
re_ver3_dmg_link = re.compile(r'href="(?P<url>http://.*? 3[.0-9]*.dmg)"')


class Flip4MacURLProvider(Processor):
    description = ("Provides a download URL for the latest Flip4Mac "
                   "release.")
    input_variables = {
        "base_url": {
            "required": False,
            "description": "Default is %s" % BASE_URL,
        },
        "major_version": {
            "required": False,
            "description": "Major version of Flip4Mac. Defaults to 3."
        }
    }
    output_variables = {
        "url": {
            "description": "URL to the latest Flip4Mac release.",
        },
    }
    
    __doc__ = description

    def get_flip4mac_dmg_url(self, base_url, major_version):
        # Read HTML index.
        try:
            f = urllib2.urlopen(base_url)
            html = f.read()
            f.close()
        except BaseException as e:
            raise ProcessorError("Can't download %s: %s" % (base_url, e))
        
        # Search for download page link.
        m = re_download_link.search(html)
        if not m:
            raise ProcessorError(
                "Couldn't find Flip4Mac download URL in %s" % base_url)
        
        # Get URL for download page.
        download_page_url = m.group("url")
        try:
            f = urllib2.urlopen(download_page_url)
            html = f.read()
            f.close()
        except BaseException as e:
            raise ProcessorError("Can't download %s: %s" % (base_url, e))
            
        if major_version == 3:
            m = re_ver3_dmg_link.search(html)
        elif major_version == 2:
            m = re_ver2_dmg_link.search(html)
        else:
            raise ProcessorError(
                "Unsupported major_version number: %s" % major_version)
            
        if not m:
            raise ProcessorError(
                "Couldn't find Flip4Mac download URL in %s" % download_page_url)
        
        return urllib2.quote(m.group("url"), safe=":/")
        

    def main(self):
        """Find and return a download URL"""
        major_version = int(self.env.get("major_version", 3))
        base_url = self.env.get("base_url", BASE_URL)
        self.env["url"] = self.get_flip4mac_dmg_url(base_url, major_version)


if __name__ == "__main__":
    processor = Flip4MacURLProvider()
    processor.execute_shell()
