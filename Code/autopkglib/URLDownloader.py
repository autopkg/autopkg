#!/usr/bin/python
#
# Refactoring 2018 Michal Moravec
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
import tempfile

from autopkglib import BUNDLE_ID, ProcessorError, is_mac
from autopkglib.URLGetter import URLGetter

if is_mac():
    import xattr


__all__ = ["URLDownloader"]


class URLDownloader(URLGetter):
    """Downloads a URL to the specified download_dir using curl."""

    description = __doc__
    input_variables = {
        "url": {"required": True, "description": "The URL to download."},
        "request_headers": {
            "required": False,
            "description": (
                "Optional dictionary of headers to include with the download "
                "request."
            ),
        },
        "curl_opts": {
            "required": False,
            "description": (
                "Optional array of options to include with the download " "request."
            ),
        },
        "download_dir": {
            "required": False,
            "description": (
                "The directory where the file will be downloaded to. Defaults "
                "to RECIPE_CACHE_DIR/downloads."
            ),
        },
        "filename": {
            "required": False,
            "description": "Filename to override the URL's tail.",
        },
        "CHECK_FILESIZE_ONLY": {
            "default": False,
            "required": False,
            "description": (
                "If True, a server's ETag and Last-Modified "
                "headers will not be checked to verify whether "
                "a download is newer than a cached item, and only "
                "Content-Length (filesize) will be used. This "
                "is useful for cases where a download always "
                "redirects to different mirrors, which could "
                "cause items to be needlessly re-downloaded. "
                "Defaults to False."
            ),
        },
        "PKG": {
            "required": False,
            "description": (
                "Local path to the pkg/dmg we'd otherwise download. "
                "If provided, the download is skipped and we just use "
                "this package or disk image."
            ),
        },
        "CURL_PATH": {
            "required": False,
            "default": "/usr/bin/curl",
            "description": "Path to curl binary. Defaults to /usr/bin/curl.",
        },
    }
    output_variables = {
        "pathname": {"description": "Path to the downloaded file."},
        "last_modified": {
            "description": "last-modified header for the downloaded item."
        },
        "etag": {"description": "etag header for the downloaded item."},
        "download_changed": {
            "description": (
                "Boolean indicating if the download has changed since the "
                "last time it was downloaded."
            )
        },
        "url_downloader_summary_result": {
            "description": "Description of interesting results."
        },
    }

    def getxattr(self, attr):
        """Get a named xattr from a file. Return None if not present"""
        if attr in xattr.listxattr(self.env["pathname"]):
            return xattr.getxattr(self.env["pathname"], attr)
        return None

    def prepare_curl_cmd(self, pathname_temporary):
        """Assemble curl command and return it."""
        curl_cmd = [
            super(URLDownloader, self).curl_binary(),
            "--silent",
            "--show-error",
            "--no-buffer",
            "--fail",
            "--dump-header",
            "-",
            "--speed-time",
            "30",
            "--location",
            "--url",
            self.env["url"],
            "--output",
            pathname_temporary,
        ]

        super(URLDownloader, self).add_curl_common_opts(curl_cmd)

        # if file already exists and the size is 0, discard it and download again
        if (
            os.path.exists(self.env["pathname"])
            and os.path.getsize(self.env["pathname"]) == 0
        ):
            os.remove(self.env["pathname"])

        # if file already exists, add some headers to the request
        # so we don't retrieve the content if it hasn't changed
        if os.path.exists(self.env["pathname"]):
            self.existing_file_size = os.path.getsize(self.env["pathname"])
            etag = self.getxattr(self.xattr_etag)
            last_modified = self.getxattr(self.xattr_last_modified)
            if etag:
                curl_cmd.extend(["--header", "If-None-Match: %s" % etag])
            if last_modified:
                curl_cmd.extend(["--header", "If-Modified-Since: %s" % last_modified])

        return curl_cmd

    def clear_vars(self):
        """Clear and initializace variables"""
        # Delete summary result if exists
        if "url_downloader_summary_result" in self.env:
            del self.env["url_downloader_summary_result"]

        # XATTR names for Etag and Last-Modified headers
        self.xattr_etag = "%s.etag" % BUNDLE_ID
        self.xattr_last_modified = "%s.last-modified" % BUNDLE_ID

        self.env["last_modified"] = ""
        self.env["etag"] = ""
        self.existing_file_size = None

    def get_filename(self):
        """Obtain filename from PKG variable or URL."""
        if "PKG" in self.env:
            self.env["pathname"] = os.path.expanduser(self.env["PKG"])
            self.env["download_changed"] = True
            self.output("Given %s, no download needed." % self.env["pathname"])
            return None

        if "filename" in self.env:
            filename = self.env["filename"]
        else:
            # Generate filename from URL.
            filename = self.env["url"].rpartition("/")[2]

        return filename

    def get_download_dir(self):
        """Create download dir and return its path."""
        download_dir = self.env.get("download_dir") or os.path.join(
            self.env["RECIPE_CACHE_DIR"], "downloads"
        )
        if not os.path.exists(download_dir):
            try:
                os.makedirs(download_dir)
            except OSError as err:
                raise ProcessorError(
                    "Can't create %s: %s" % (download_dir, err.strerror)
                )
        return download_dir

    def create_temp_file(self, download_dir):
        """Create temporary file and return its path."""
        temporary_file = tempfile.NamedTemporaryFile(dir=download_dir, delete=False)
        pathname_temporary = temporary_file.name
        # Set permissions on the temp file as curl would set for a newly-downloaded
        # file. NamedTemporaryFile uses mkstemp(), which sets a mode of 0600, and
        # this can cause issues if this item is eventually copied to a Munki repo
        # with the same permissions and the file is inaccessible by (for example)
        # the webserver.
        os.chmod(pathname_temporary, 0o644)
        return pathname_temporary

    def download_changed(self, header):
        """Check if downloaded file changed on server."""
        # If Content-Length header is present and we had a cached
        # file, see if it matches the size of the cached file.
        # Useful for webservers that don't provide Last-Modified
        # and ETag headers.
        if (not header.get("etag") and not header.get("last-modified")) or self.env[
            "CHECK_FILESIZE_ONLY"
        ]:
            size_header = header.get("content-length")
            if size_header and int(size_header) == self.existing_file_size:
                self.env["download_changed"] = False
                self.output(
                    "File size returned by webserver matches that "
                    "of the cached file: %s bytes" % size_header
                )
                self.output(
                    "WARNING: Matching a download by filesize is a "
                    "fallback mechanism that does not guarantee "
                    "that a build is unchanged."
                )
                self.output("Using existing %s" % self.env["pathname"])
                return False

        if header["http_result_code"] == "304":
            # resource not modified
            self.env["download_changed"] = False
            self.output("Item at URL is unchanged.")
            self.output("Using existing %s" % self.env["pathname"])
            return False

        return True

    def move_temp_file(self, pathname_temporary):
        """Move temporary download file to pathname."""
        if os.path.exists(self.env["pathname"]):
            os.remove(self.env["pathname"])
        try:
            os.rename(pathname_temporary, self.env["pathname"])
        except OSError:
            raise ProcessorError(
                "Can't move %s to %s" % (pathname_temporary, self.env["pathname"])
            )

    def store_headers(self, header):
        """Store last-modified and etag headers in pathname xattr."""
        if header.get("last-modified"):
            self.env["last_modified"] = header.get("last-modified")
            xattr.setxattr(
                self.env["pathname"],
                self.xattr_last_modified,
                header.get("last-modified"),
            )
            self.output(
                "Storing new Last-Modified header: %s" % header.get("last-modified")
            )

        self.env["etag"] = ""
        if header.get("etag"):
            self.env["etag"] = header.get("etag")
            xattr.setxattr(self.env["pathname"], self.xattr_etag, header.get("etag"))
            self.output("Storing new ETag header: %s" % header.get("etag"))

    def main(self):
        if not is_mac():
            raise ProcessorError("This processor is Mac-only!")

        # Clear and initiazize data structures
        self.clear_vars()

        # Ensure existence of necessary files, directories and paths
        filename = self.get_filename()
        if filename is None:
            return
        download_dir = self.get_download_dir()
        self.env["pathname"] = os.path.join(download_dir, filename)
        pathname_temporary = self.create_temp_file(download_dir)

        # Prepare curl command
        curl_cmd = self.prepare_curl_cmd(pathname_temporary)

        # Execute curl command and parse headers
        raw_header = super(URLDownloader, self).download(curl_cmd)
        header = {}
        super(URLDownloader, self).clear_header(header)
        super(URLDownloader, self).parse_headers(raw_header, header)

        if self.download_changed(header):
            self.env["download_changed"] = True
        else:
            # Discard the temp file
            os.remove(pathname_temporary)
            return

        # New resource was downloaded. Move the temporary download file to the pathname
        self.move_temp_file(pathname_temporary)

        # Save last-modified and etag headers to files xattr
        self.store_headers(header)

        # Generate output messages and variables
        self.output("Downloaded %s" % self.env["pathname"])
        self.env["url_downloader_summary_result"] = {
            "summary_text": "The following new items were downloaded:",
            "data": {"download_path": self.env["pathname"]},
        }


if __name__ == "__main__":
    PROCESSOR = URLDownloader()
    PROCESSOR.execute_shell()
