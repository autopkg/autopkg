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

from Processor import Processor, ProcessorError


__all__ = ["OracleJava7URLProvider"]


BASE_URL = "http://java.com/en/download/manual.jsp?locale=en"

#<a title=" Download Java software for Mac OS X" href="http://javadl.sun.com/webapps/download/AutoDL?BundleId=75253">
jre_download_link = re.compile(
    r'<a title=" *Download Java software for Mac OS X" *href="(?P<url>http://javadl.sun.com/webapps/download/AutoDL\?BundleId=[0-9]+)">')


class OracleJava7URLProvider(Processor):
    """Provides a download URL for the latest Oracle Java 7 JRE release."""
    input_variables = {
        "base_url": {
            "required": False,
            "description": "Default is %s" % BASE_URL,
        },
    }
    output_variables = {
        "url": {
            "description": "URL to the latest Oracle Java 7 JRE release.",
        },
    }
    description = __doc__

    def get_java_dmg_url(self, base_url):
        """Finds a download URL for latest Oracle Java 7 release."""
        # Read HTML from base URL.
        try:
            f = urllib2.urlopen(base_url)
            html = f.read()
            f.close()
        except BaseException as err:
            raise ProcessorError("Can't download %s: %s" % (base_url, err))
        
        # Search for JRE downlaods link
        m = jre_download_link.search(html)
        if not m:
            raise ProcessorError(
                "Couldn't find JRE download link in %s" % base_url)
        return m.group("url")
        
    def main(self):
        """Find and return a download URL"""
        base_url = self.env.get("base_url", BASE_URL)
        self.env["url"] = self.get_java_dmg_url(base_url)


if __name__ == "__main__":
    processor = OracleJava7URLProvider()
    processor.execute_shell()
