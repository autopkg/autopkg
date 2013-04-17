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


import json
import urllib2

from Processor import Processor, ProcessorError


__all__ = ["AdobeReaderURLProvider"]


AR_BASE_URL = ("http://get.adobe.com/reader/webservices/json/standalone/"
    "?platform_type=Macintosh&platform_dist=OSX&platform_arch=x86-32"
    "&platform_misc=10.8.0&language=%s&eventname=readerotherversions")

LANGUAGE_DEFAULT = "English"
MAJOR_VERSION_DEFAULT = "11"

MAJOR_VERSION_MATCH_STR = "adobe/reader/mac/%s"

class AdobeReaderURLProvider(Processor):
    description = "Provides URL to the latest Adobe Reader release."
    input_variables = {
        "language": {
            "required": False,
            "description": ("Which language to download. Examples: 'English', "
                            "'German', 'Japanese', 'Swedish'. Default is %s."
                            % LANGUAGE_DEFAULT),
        },
        "major_version": {
            "required": False,
            "description": ("Major version. Examples: '10', '11'. Defaults to "
                            "%s" % MAJOR_VERSION_DEFAULT)
        },
        "base_url": {
            "required": False,
            "description": "Default is %s" % AR_BASE_URL,
        },
    }
    output_variables = {
        "url": {
            "description": "URL to the latest Adobe Reader release.",
        },
    }
    
    __doc__ = description
    
    def get_reader_dmg_url(self, base_url, language, major_version):
        request = urllib2.Request(base_url % language)
        request.add_header("x-requested-with", "XMLHttpRequest")
        try:
            url_handle = urllib2.urlopen(request)
            json_response = url_handle.read()
            url_handle.close()
        except BaseException as e:
            raise ProcessorError("Can't open %s: %s" % (base_url, e))
            
        reader_info = json.loads(json_response)
        major_version_string = MAJOR_VERSION_MATCH_STR % major_version
        matches = [item["download_url"] for item in reader_info 
                   if major_version_string in item["download_url"]]
        try:
            return matches[0]
        except IndexError:
            raise ProcessorError(
                "Can't find Adobe Reader download URL for %s, version %s" 
                % (language, major_version))
    
    def main(self):
        # Determine base_url, language and major_version.
        base_url = self.env.get("base_url", AR_BASE_URL)
        language = self.env.get("language", LANGUAGE_DEFAULT)
        major_version = self.env.get("major_version", MAJOR_VERSION_DEFAULT)
        
        self.env["url"] = self.get_reader_dmg_url(
            base_url, language, major_version)
        self.output("Found URL %s" % self.env["url"])
    

if __name__ == "__main__":
    processor = AdobeReaderURLProvider()
    processor.execute_shell()
    
