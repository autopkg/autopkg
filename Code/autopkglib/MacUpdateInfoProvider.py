#!/usr/bin/env python
#
# Copyright 2014 ps Enable, Inc.
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


import urllib
import urllib2
import urlparse
import os
import re

from autopkglib import Processor, ProcessorError

__all__ = ["MacUpdateInfoProvider"]


class MacUpdateInfoProvider(Processor):
    description = ( "Provides URL to the latest update from Macupdate.com. "
    				"The Macupdate download URL is of the form: "
    				"https://macupdate.com/downloads/12345/SomeApp.dmg, which then"
    				"302 redirects to the actual download URL. Macupdate will"
    				"return a 200 response code to known URL downloading tools"
    				"such as curl, wget, and urllib2. To avoid this, we add a "
    				"User-Agent header that matches Safari. " )
    input_variables = {
        "macupdate_url": {
            "required": True,
            "description": "URL for a MacUpdate app page.",
        },
    }
    output_variables = {
        "request_headers": {
            "description": ("Add a User-Agent header for URLDownloader.py because Macupdate.com"
                            "will return a plain HTTP 200 with empty content for known URL"
                            "downloading tools like curl, wget, and (in our case) urllib2,"
                            "rather than providing the HTTP 302 redirect code that we want."
                            "So we put in a User-Agent header that matches Safari instead." )
        },
        "url": {
            "description": "URL for a download.",
        },
        "version": {
            "description": ("Version info from web page.")
        }
    }

    __doc__ = description
    
    user_agent_string = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9) AppleWebKit/537.71 (KHTML, like Gecko) Version/7.0 Safari/537.71"
            

    def main(self):
        # load the page into a string        
        macupdate_page = urllib2.urlopen( self.env[ "macupdate_url" ] )
        macupdate_page_contents = macupdate_page.read()
        
        # parse it using a regex to find the download URL
        downloadHref = re.search( "href=\"(/download/.*)\" id", macupdate_page_contents )
        self.env[ "url" ] = "https://macupdate.com" + downloadHref.group( 1 )
        
        # parse page to get version info
        version_match = re.search( "<span id=\"appversinfo\">(.*)</span>", macupdate_page_contents )
        self.env[ "version" ] = version_match.group( 1 )
        
        if "request_headers" in self.env:
            
            # request_headers already exists, add User-Agent to existing dict
            request_headers_dict = self.env[ "request_headers" ]
            request_headers_dict[ "User-Agent" ] = self.user_agent_string
            
        else:
        
        	# create new request_headers dict
            self.env[ "request_headers" ] = { "User-Agent": self.user_agent_string }
            
            
        
if __name__ == "__main__":
    processor = MacUpdateInfoProvider()
    processor.execute_shell()
