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


__all__ = ["AdobeFlashURLProvider"]


ADOBEFLASH_BASE_URL = "http://get.adobe.com/flashplayer/completion/?installer=Flash_Player_11_for_Mac_OS_X_10.6_-_10.7"
#re_adobeflash_ver = re.compile(r'Adobe Flash Player \S+ version (?P<version>[\d.]+)', re.I)
re_adobeflash_dmg = re.compile(r'(?P<url>http://fpdownload.macromedia.com/get/flashplayer/pdc/[\d.]+/install_flash_player_osx.dmg)', re.I)

class AdobeFlashURLProvider(Processor):
    description = "Provides URL to the latest Adobe Flash Player release."
    input_variables = {
        "base_url": {
            "required": False,
            "description": "Default is '%s'." % ADOBEFLASH_BASE_URL,
        },
    }
    output_variables = {
        "url": {
            "description": "URL to the latest Adobe Flash Player release.",
        },
    }
    
    __doc__ = description
    
    def get_adobeflash_dmg_url(self, base_url):
        # Read HTML index.
        try:
            f = urllib2.urlopen(base_url)
            html = f.read()
            f.close()
        except BaseException as e:
            raise ProcessorError("Can't download %s: %s" % (base_url, e))
        
        # Search for download link.
        m = re_adobeflash_dmg.search(html)
        if not m:
            raise ProcessorError("Couldn't find Adobe Flash Player download URL in %s" % base_url)
        
        # Return URL.
        return m.group("url")
        #return "http://fpdownload.macromedia.com/get/flashplayer/pdc/%s/install_flash_player_osx.dmg" % m.group("ver")
    
    def main(self):
        # Determine base_url.
        if "base_url" in self.env:
            base_url = self.env.base_url
        else:
            base_url = ADOBEFLASH_BASE_URL
        
        self.env["url"] = self.get_adobeflash_dmg_url(base_url)
    

if __name__ == '__main__':
    processor = AdobeFlashURLProvider()
    processor.execute_shell()
    

