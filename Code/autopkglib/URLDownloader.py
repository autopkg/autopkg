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


import os.path
import urllib2

from Processor import Processor, ProcessorError


__all__ = ["URLDownloader"]


# Download URLs in chunks of 256 kB.
CHUNK_SIZE = 256 * 1024


class URLDownloader(Processor):
    description = "Downloads a URL to the specified download_dir."
    input_variables = {
        "url": {
            "required": True,
            "description": "The URL to download.",
        },
        "download_dir": {
            "required": True,
            "description": "The directory where the file will be downloaded to.",
        },
        "filename": {
            "required": False,
            "description": "Filename to override the URL's tail.",
        },
    }
    output_variables = {
        "pathname": {
            "description": "Path to the downloaded file.",
        },
    }
    
    __doc__ = description
    
    def has_changed(self, url_info, pathname):
        """Check if data at URL is different from the already downloaded copy."""
        
        # Get file info.
        try:
            file_info = os.stat(pathname)
        except BaseException as e:
            raise ProcessorError("Couldn't get info for %s: %s" % (pathname, e))
        
        # Compare size.
        content_length = url_info.get("Content-Length", None)
        if content_length:
            content_length = int(content_length)
            if content_length == file_info.st_size:
                return False
        
        # Time comparison and If-Modified-Since not implemented due to lack of
        # decent timezone handling in Python.
        return True
    
    def main(self):
        if not "filename" in self.env:
            # Generate filename.
            filename = self.env["url"].rpartition("/")[2]
        else:
            filename = self.env.filename
        pathname = os.path.join(self.env["download_dir"], filename)
        
        # Download URL.
        url_handle = None
        try:
            # Open URL.
            url_handle = urllib2.urlopen(self.env["url"])
            
            # If file already exists, check if it has changed.
            if os.path.exists(pathname):
                download = self.has_changed(url_handle.info(), pathname)
            else:
                download = True
            
            # Download if file has changed, or doesn't exist.
            if download:
                with open(pathname, "wb") as file_handle:
                    while True:
                        data = url_handle.read(CHUNK_SIZE)
                        if len(data) == 0:
                            break
                        file_handle.write(data)
        
        except BaseException as e:
            raise ProcessorError("Couldn't download %s: %s" % (self.env["url"], e))
        finally:
            if url_handle is not None:
                url_handle.close()
        
        # Save path to downloaded file.
        self.env["pathname"] = pathname
    

if __name__ == '__main__':
    processor = URLDownloader()
    processor.execute_shell()
    
