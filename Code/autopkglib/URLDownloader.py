#!/usr/bin/python
#
# Copyright 2015 Greg Neagle
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
"""See docstring for URLDownloader class"""

import os.path
import re
import subprocess
import time
import xattr
import tempfile

from urllib2 import unquote

from autopkglib import Processor, ProcessorError
try:
    from autopkglib import BUNDLE_ID
except ImportError:
    BUNDLE_ID = "com.github.autopkg"


__all__ = ["URLDownloader"]

# XATTR names for Etag and Last-Modified headers
XATTR_ETAG = "%s.etag" % BUNDLE_ID
XATTR_LAST_MODIFIED = "%s.last-modified" % BUNDLE_ID


def getxattr(pathname, attr):
    """Get a named xattr from a file. Return None if not present"""
    if attr in xattr.listxattr(pathname):
        return xattr.getxattr(pathname, attr)
    else:
        return None


class URLDownloader(Processor):
    """Downloads a URL to the specified download_dir using curl."""
    description = __doc__
    input_variables = {
        "url": {
            "required": True,
            "description": "The URL to download.",
        },
        "request_headers": {
            "required": False,
            "description":
                ("Optional dictionary of headers to include with the download "
                 "request.")
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
        "DISABLE_LAST_MODIFIED_ETAG_CHECKS": {
            "default": False,
            "required": False,
            "description": ("If True, a server's ETag and Last-Modified "
                            "headers will not be checked to verify whether "
                            "a download is newer than a cached item, and only "
                            "Content-Length (filesize) will be used. This "
                            "is useful for cases where a download always "
                            "redirects to different mirrors, which could "
                            "cause items to be needlessly re-downloaded. "
                            "Defaults to False."),
        },
        "PKG": {
            "required": False,
            "description":
                ("Local path to the pkg/dmg we'd otherwise download. "
                 "If provided, the download is skipped and we just use "
                 "this package or disk image."),
        },
        "CURL_PATH": {
            "required": False,
            "default": "/usr/bin/curl",
            "description": "Path to curl binary. Defaults to /usr/bin/curl.",
        },
    }
    output_variables = {
        "pathname": {
            "description": "Path to the downloaded file.",
        },
        "last_modified": {
            "description": "last-modified header for the downloaded item.",
        },
        "etag": {
            "description": "etag header for the downloaded item.",
        },
        "download_changed": {
            "description":
                ("Boolean indicating if the download has changed since the "
                 "last time it was downloaded."),
        },
        "url_downloader_summary_result": {
            "description": "Description of interesting results."
        },
    }

    def _curl_filename(self, curl_args, curl_path=None):
        if curl_path is None:
            curl_path = [self.env['CURL_PATH']]
        curl_cmd = curl_path + curl_args
        self.output(' '.join(curl_cmd), verbose_level=2)
        proc = subprocess.Popen(curl_cmd, shell=False, bufsize=1,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        file_url = proc.stdout.readline()
        filename = file_url.rpartition("/")[2]
        return file_url, filename

    def _remote_filename(self, url):
        curl_args = ['--silent',
                     '--location',
                     '--head',
                     '--write-out', '%{url_effective}',
                     '--url', url,
                     '--output', '/dev/null']

        (file_url, filename) = self._curl_filename(curl_args)

        # Decode any special characters in the filename, like %20 to a space.
        filename = unquote(filename)
        self.output("Found filename '%s' at '%s'" % (filename, file_url),
                    verbose_level=2)
        return filename

    def main(self):
        # clear any pre-exising summary result
        if 'url_downloader_summary_result' in self.env:
            del self.env['url_downloader_summary_result']

        self.env["last_modified"] = ""
        self.env["etag"] = ""
        existing_file_size = None

        if "PKG" in self.env:
            self.env["pathname"] = os.path.expanduser(self.env["PKG"])
            self.env["download_changed"] = True
            self.output("Given %s, no download needed." % self.env["pathname"])
            return

        if "filename" not in self.env:
            # Find the effective filename of the url after following redirects.
            filename = self._remote_filename(self.env["url"])
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
            except OSError, err:
                raise ProcessorError(
                    "Can't create %s: %s" % (download_dir, err.strerror))

        # Create a temp file
        temporary_file = tempfile.NamedTemporaryFile(dir=download_dir,
                                                     delete=False)
        pathname_temporary = temporary_file.name

        # construct curl command.
        curl_cmd = [self.env['CURL_PATH'],
                    '--silent', '--show-error', '--no-buffer',
                    '--dump-header', '-',
                    '--speed-time', '30',
                    '--location',
                    '--url', self.env["url"],
                    '--output', pathname_temporary]

        if "request_headers" in self.env:
            headers = self.env["request_headers"]
            for header, value in headers.items():
                curl_cmd.extend(['--header', '%s: %s' % (header, value)])

        # if file already exists and the size is 0, discard it and download
        # again
        if os.path.exists(pathname) and os.path.getsize(pathname) == 0:
            os.remove(pathname)

        # if file already exists, add some headers to the request
        # so we don't retrieve the content if it hasn't changed
        if os.path.exists(pathname):
            existing_file_size = os.path.getsize(pathname)
            etag = getxattr(pathname, XATTR_ETAG)
            last_modified = getxattr(pathname, XATTR_LAST_MODIFIED)
            if etag:
                curl_cmd.extend(['--header', 'If-None-Match: %s' % etag])
            if last_modified:
                curl_cmd.extend(
                    ['--header', 'If-Modified-Since: %s' % last_modified])

        # Open URL.
        proc = subprocess.Popen(curl_cmd, shell=False, bufsize=1,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        donewithheaders = False
        maxheaders = 15
        header = {}
        header['http_result_code'] = '000'
        header['http_result_description'] = ''
        while True:
            if not donewithheaders:
                info = proc.stdout.readline().strip('\r\n')
                if info.startswith('HTTP/'):
                    try:
                        header['http_result_code'] = info.split(None, 2)[1]
                        header['http_result_description'] = (
                            info.split(None, 2)[2])
                    except IndexError:
                        pass
                elif ': ' in info:
                    # got a header line
                    part = info.split(None, 1)
                    fieldname = part[0].rstrip(':').lower()
                    try:
                        header[fieldname] = part[1]
                    except IndexError:
                        header[fieldname] = ''
                elif info == '':
                    # we got an empty line; end of headers (or curl exited)
                    if header.get('http_result_code') in [
                            '301', '302', '303']:
                        # redirect, so more headers are coming.
                        # Throw away the headers we've received so far
                        header = {}
                        header['http_result_code'] = '000'
                        header['http_result_description'] = ''
                    else:
                        donewithheaders = True
            else:
                time.sleep(0.1)

            if proc.poll() != None:
                # For small download files curl may exit before all headers
                # have been parsed, don't immediately exit.
                maxheaders -= 1
                if donewithheaders or maxheaders <= 0:
                    break

        retcode = proc.poll()
        if retcode:
            curlerr = ''
            try:
                curlerr = proc.stderr.read().rstrip('\n')
                curlerr = curlerr.split(None, 2)[2]
            except IndexError:
                pass
            if retcode == 22:
                # 22 means any 400 series return code. Note: header seems not to
                # be dumped to STDOUT for immediate failures. Hence
                # http_result_code is likely blank/000. Read it from stderr.
                if re.search(r'URL returned error: [0-9]+$', curlerr):
                    header['http_result_code'] = curlerr[curlerr.rfind(' ')+1:]

        # If Content-Length header is present and we had a cached
        # file, see if it matches the size of the cached file.
        # Useful for webservers that don't provide Last-Modified
        # and ETag headers.
        if (not header.get("etag") and \
           not header.get("last-modified")) or \
            self.env["DISABLE_LAST_MODIFIED_ETAG_CHECKS"]:
            size_header = header.get("content-length")
            if size_header and int(size_header) == existing_file_size:
                self.env["download_changed"] = False
                self.output("File size returned by webserver matches that "
                            "of the cached file: %s bytes" % size_header)
                self.output("WARNING: Matching a download by filesize is a "
                            "fallback mechanism that does not guarantee "
                            "that a build is unchanged.")
                self.output("Using existing %s" % pathname)
                return

        if header['http_result_code'] == '304':
            # resource not modified
            self.env["download_changed"] = False
            self.output("Item at URL is unchanged.")
            self.output("Using existing %s" % pathname)

            # Discard the temp file
            os.remove(pathname_temporary)

            return

        self.env["download_changed"] = True

        # New resource was downloaded. Move the temporary download file
        # to the pathname
        if os.path.exists(pathname):
            os.remove(pathname)
        try:
            os.rename(pathname_temporary, pathname)
        except OSError:
            raise ProcessorError(
                "Can't move %s to %s" % (pathname_temporary, pathname))

        # save last-modified header if it exists
        if header.get("last-modified"):
            self.env["last_modified"] = (
                header.get("last-modified"))
            xattr.setxattr(
                pathname, XATTR_LAST_MODIFIED,
                header.get("last-modified"))
            self.output(
                "Storing new Last-Modified header: %s"
                % header.get("last-modified"))

        # save etag if it exists
        self.env["etag"] = ""
        if header.get("etag"):
            self.env["etag"] = header.get("etag")
            xattr.setxattr(
                pathname, XATTR_ETAG, header.get("etag"))
            self.output("Storing new ETag header: %s"
                        % header.get("etag"))

        self.output("Downloaded %s" % pathname)
        self.env['url_downloader_summary_result'] = {
            'summary_text': 'The following new items were downloaded:',
            'data': {
                'download_path': pathname,
            }
        }


if __name__ == "__main__":
    PROCESSOR = URLDownloader()
    PROCESSOR.execute_shell()
