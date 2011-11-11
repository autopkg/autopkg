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


__all__ = ["AdobeReaderURLProvider"]


AR_BASE_URL = "http://get.adobe.com/se/reader/completion/?installer=Reader_10_%s_for_Mac_Intel"
# location.href = 'http://ardownload.adobe.com/pub/adobe/reader/mac/10.x/10.0.0/en_US/AdbeRdr1000_en_US.dmg';
re_reader_dmg = re.compile(r'location\.href *= *\'(?P<url>http://ardownload\.adobe\.com/pub/adobe/reader/mac/[0-9.x]+/[0-9.]+/[a-zA-Z_]+/AdbeRdr[0-9]+_[a-zA-Z_]+\.dmg)\'')


class AdobeReaderURLProvider(Processor):
    description = "Provides URL to the latest Adobe Reader release."
    input_variables = {
        "language": {
            "required": False,
            "description": "Which localization to download, default is 'English'.",
        },
        "base_url": {
            "required": False,
            "description": "Default is 'http://get.adobe.com/se/reader/completion/?installer=Reader_10_%s_for_Mac_Intel'.",
        },
    }
    output_variables = {
        "url": {
            "description": "URL to the latest Adobe Reader release.",
        },
    }
    
    __doc__ = description
    
    def get_reader_dmg_url(self, base_url, language):
        # Construct download directory URL.
        index_url = base_url % language
        
        # Read HTML index.
        try:
            f = urllib2.urlopen(index_url)
            html = f.read()
            f.close()
        except BaseException as e:
            raise ProcessorError("Can't download %s: %s" % (index_url, e))
        
        # Search for download link.
        m = re_reader_dmg.search(html)
        if not m:
            raise ProcessorError("Couldn't find Adobe Reader download URL in %s" % index_url)
        
        # Return URL.
        return m.group("url")
    
    def main(self):
        # Determine language and base_url.
        if "language" in self.env:
            language = self.env["language"]
        else:
            language = "English"
        if "base_url" in self.env:
            base_url = self.env["base_url"]
        else:
            base_url = AR_BASE_URL
        
        self.env["url"] = self.get_reader_dmg_url(base_url, language)
    

if __name__ == '__main__':
    processor = AdobeReaderURLProvider()
    processor.execute_shell()
    
