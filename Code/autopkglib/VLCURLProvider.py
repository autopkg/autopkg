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


__all__ = ["VLCURLProvider"]


VLC_BASE_URL = "http://www.videolan.org/vlc/download-macosx.html"
# <a href="http://sourceforge.net/projects/vlc/files/1.1.5/macosx/vlc-1.1.5.dmg/download">Download VLC</a>
# <a href="http://sourceforge.net/projects/vlc/files/1.1.5/macosx/vlc-1.1.5-intel.dmg/download">Download VLC</a>
# <a href="http://sourceforge.net/projects/vlc/files/1.1.5/macosx/vlc-1.1.5-intel64.dmg/download">Download VLC</a>
# <a href="http://sourceforge.net/projects/vlc/files/1.1.5/macosx/vlc-1.1.5-powerpc.dmg/download">Download VLC</a>
re_vlc_dmg = re.compile(r'a[^>]* href=["\'](?P<url>http://sourceforge\.net/projects/vlc/files/[0-9.]+/macosx/vlc-[0-9.]+(?P<build>-(intel(64)?|powerpc))?\.dmg/download)["\']')


class VLCURLProvider(Processor):
    description = "Provides URL to the latest Firefox release."
    input_variables = {
        "build": {
            "required": False,
            "description": "Which build to download, 'universal' (default), 'intel', 'intel64' or 'powerpc'.",
        },
        "base_url": {
            "required": False,
            "description": "Default is '%s'." % VLC_BASE_URL,
        },
    }
    output_variables = {
        "url": {
            "description": "URL to the latest VLC release.",
        },
    }
    
    __doc__ = description
    
    def get_vlc_dmg_url(self, base_url, build):
        # Read HTML index.
        try:
            f = urllib2.urlopen(base_url)
            html = f.read()
            f.close()
        except BaseException as e:
            raise ProcessorError("Can't download %s: %s" % (base_url, e))
        
        if build == "universal":
            buildsuffix = None
        else:
            buildsuffix = "-" + build
        
        # Search for download links.
        matches = re_vlc_dmg.finditer(html)
        if not matches:
            raise ProcessorError(
                "Couldn't find VLC download URL in %s" % base_url)
        
        # Find match with the requested build.
        for m in matches:
            if m.group("build") == buildsuffix:
                return m.group("url")
        
        raise ProcessorError("%s build not found" % build)
    
    def main(self):
        # Determine build and base_url.
        if "build" in self.env:
            build = self.env["build"]
        else:
            build = "universal"
        if "base_url" in self.env:
            base_url = self.env["base_url"]
        else:
            base_url = VLC_BASE_URL
        
        self.env["url"] = self.get_vlc_dmg_url(base_url, build)
        self.output("Found URL %s" % self.env["url"])
    

if __name__ == '__main__':
    processor = VLCURLProvider()
    processor.execute_shell()
    
