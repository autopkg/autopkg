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
import xattr

from Processor import Processor, ProcessorError
try:
    from autopkglib import BUNDLE_ID
except ImportError:
    BUNDLE_ID = "com.googlecode.autopkg"


__all__ = ["URLDownloader"]

# XATTR names for Etag and Last-Modified headers
XATTR_ETAG = "%s.etag" % BUNDLE_ID
XATTR_LAST_MODIFIED = "%s.last-modified" % BUNDLE_ID

# Download URLs in chunks of 256 kB.
CHUNK_SIZE = 256 * 1024

def getxattr(pathname, attr):
    """Get a named xattr from a file. Return None if not present"""
    if attr in xattr.listxattr(pathname):
        return xattr.getxattr(pathname, attr)
    else:
        return None


class URLDownloader(Processor):
    description = "Downloads a URL to the specified download_dir."
    input_variables = {
        "url": {
            "required": True,
            "description": "The URL to download.",
        },
        "download_dir": {
            "required": False,
            "description": 
                ("The directory where the file will be downloaded to. Defaults "
                 "to RECIPE_CACHE_DIR/downloads."),
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
        "download_changed": {
            "description": 
                ("Boolean indicating if the download has changed since the "
                 "last time it was downloaded."),
        },
    }
    
    __doc__ = description
    
    
    def main(self):
        if not "filename" in self.env:
            # Generate filename.
            filename = self.env["url"].rpartition("/")[2]
        else:
            filename = self.env["filename"]
        download_dir = (self.env.get("download_dir") or
                        os.path.join(self.env["RECIPE_CACHE_DIR"], "downloads"))
        pathname = os.path.join(download_dir, filename)
        # Save pathname to environment
        self.env["pathname"] = pathname
        
        # create download_dir if needed
        if not os.path.exists(download_dir):
            try:
                os.makedirs(download_dir)
            except OSError, e:
                raise ProcessorError(
                    "Can't create %s: %s" 
                    % (download_dir, e.strerror))
        
        # Download URL.
        url_handle = None
        try:
            request = urllib2.Request(url=self.env["url"])
            
            # if file already exists, add some headers to the request
            # so we don't retrieve the content if it hasn't changed
            if os.path.exists(pathname):
                etag = getxattr(pathname, XATTR_ETAG)
                last_modified = getxattr(pathname, XATTR_LAST_MODIFIED)
                if etag:
                    request.add_header("If-None-Match", etag)
                if last_modified:
                    request.add_header("If-Modified-Since", last_modified)
                    
            # Open URL.
            try:
                url_handle = urllib2.urlopen(request)
            except urllib2.HTTPError, http_err:
                if http_err.code == 304:
                    # resource not modified
                    self.env["download_changed"] = False
                    return
                else:
                    raise
            
            # Download file.
            self.env["download_changed"] = True
            with open(pathname, "wb") as file_handle:
                while True:
                    data = url_handle.read(CHUNK_SIZE)
                    if len(data) == 0:
                        break
                    file_handle.write(data)
                    
            # save last-modified header if it exists
            if url_handle.info().get("last-modified"):
                xattr.setxattr(
                    pathname, XATTR_LAST_MODIFIED,
                    url_handle.info().get("last-modified"))
                            
            # save etag if it exists
            if url_handle.info().get("etag"):
                xattr.setxattr(
                    pathname, XATTR_ETAG, url_handle.info().get("etag"))
        
        except BaseException as e:
            raise ProcessorError(
                "Couldn't download %s: %s" % (self.env["url"], e))
        finally:
            if url_handle is not None:
                url_handle.close()


if __name__ == "__main__":
    processor = URLDownloader()
    processor.execute_shell()
    
