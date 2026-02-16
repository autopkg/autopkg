#!/usr/local/autopkg/python
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

import json
import os.path
import platform
import tempfile
from hashlib import md5, sha1, sha256
from typing import Any

from autopkglib import BUNDLE_ID, ProcessorError, xattr
from autopkglib.URLGetter import URLGetter

__all__ = ["URLDownloader"]


class URLDownloader(URLGetter):
    """Downloads a URL to the specified download_dir using curl."""

    description = __doc__
    lifecycle = {"introduced": "0.1.0"}
    input_variables = {
        "url": {"required": True, "description": "The URL to download."},
        "request_headers": {
            "required": False,
            "description": (
                "Optional dictionary of headers to include with the download request."
            ),
        },
        "curl_opts": {
            "required": False,
            "description": (
                "Optional array of options to include with the download request."
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
        "prefetch_filename": {
            "required": False,
            "description": (
                "If True, URLDownloader attempts to determine filename from HTTP "
                "headers downloaded before the file itself. 'prefetch_filename' "
                "overrides 'filename' option. Filename is determined from the first "
                "available source of information in this order:\n"
                "\t1. Content-Disposition header\n"
                "\t2. Location header\n"
                "\t3. 'filename' option (if set)\n"
                "\t4. last part of 'url'.  \n"
                "'prefetch_filename' is useful for URLs with redirects."
            ),
            "default": False,
        },
        "CHECK_FILESIZE_ONLY": {
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
            "default": False,
        },
        "PKG": {
            "required": False,
            "description": (
                "Local path to the pkg/dmg we'd otherwise download. "
                "If provided, the download is skipped and we just use "
                "this package or disk image."
            ),
        },
        "COMPUTE_HASHES": {
            "required": False,
            "default": False,
            "description": (
                "Determine whether to compute md5, sha1, and sha256 hashes of "
                "the downloaded file."
            ),
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

    def prepare_base_curl_cmd(self) -> list[str]:
        """Assemble base curl command and return it."""
        curl_cmd = [
            self.curl_binary(),
            "--silent",
            "--show-error",
            "--no-buffer",
            "--dump-header",
            "-",
            "--speed-time",
            "30",
            "--location",
            "--url",
            self.env["url"],
        ]

        return curl_cmd

    def clear_zero_file(self, pathname) -> None:
        """If file already exists and the size is 0, discard it to download again."""
        if os.path.exists(pathname) and os.path.getsize(pathname) == 0:
            os.remove(pathname)

    def prepare_download_curl_cmd(self, pathname_temporary) -> list[str]:
        """Assemble file download curl command and return it."""
        curl_cmd = self.prepare_base_curl_cmd()
        curl_cmd.extend(["--fail", "--output", pathname_temporary])
        # Add the common options
        self.add_curl_common_opts(curl_cmd)
        # Clear out a potentially zero-byte file
        self.clear_zero_file(self.env["pathname"])
        self.add_curl_headers(curl_cmd, self.produce_etag_headers(self.env["pathname"]))
        return curl_cmd

    def produce_etag_headers(self, filename) -> dict[str, str]:
        """Produce a dict of curl headers containing etag headers from the download."""
        headers = {}
        # If the download file already exists, add some headers to the request
        # so we don't retrieve the content if it hasn't changed
        if os.path.exists(filename):
            metadata = self.get_metadata()
            self.existing_file_size = metadata.get("file_size", 0)
            http_headers: dict[str, Any] = metadata.get("http_headers", {})
            if etag := http_headers.get("ETag"):
                headers["If-None-Match"] = etag
            if last_modified := http_headers.get("Last-Modified"):
                headers["If-Modified-Since"] = last_modified
        return headers

    def clear_vars(self) -> None:
        """Clear and initialize variables."""
        # Delete summary result if exists
        if "url_downloader_summary_result" in self.env:
            del self.env["url_downloader_summary_result"]

        # XATTR names for Etag and Last-Modified headers
        if platform.platform().startswith("Linux"):
            self.xattr_etag = f"user.{BUNDLE_ID}.etag"
            self.xattr_last_modified = f"user.{BUNDLE_ID}.last-modified"
        else:
            self.xattr_etag = f"{BUNDLE_ID}.etag"
            self.xattr_last_modified = f"{BUNDLE_ID}.last-modified"

        self.env["file_size"] = 0
        self.env["last_modified"] = ""
        self.env["etag"] = ""
        self.existing_file_size = None

    def prefetch_filename(self) -> str | None:
        """Attempt to find filename in HTTP headers."""
        curl_cmd = self.prepare_base_curl_cmd()
        curl_cmd.extend(["--head"])

        raw_headers = self.download_with_curl(curl_cmd)
        header = self.parse_headers(raw_headers)

        if "filename=" in header.get("content-disposition", ""):
            filename = (
                header["content-disposition"]
                .rpartition("filename=")[2]
                .replace('"', "")
            )
            self.output(
                f"Filename prefetched from the HTTP Content-Disposition header: {filename}",
                verbose_level=2,
            )
        elif header.get("http_redirected", None):
            filename = header["http_redirected"].rpartition("/")[2]
            self.output(
                f"Filename prefetched from the HTTP Location header: {filename}",
                verbose_level=2,
            )
        else:
            self.output(
                "Unable to find filename in the HTTP headers during prefetch",
                verbose_level=2,
            )
            return None

        return filename

    def get_filename(self) -> str | None:
        """Obtain filename from PKG variable or URL."""
        if "PKG" in self.env:
            self.env["pathname"] = os.path.expanduser(self.env["PKG"])
            self.env["download_changed"] = True
            self.output(f"Given {self.env['pathname']}, no download needed.")
            return None

        if self.env.get("prefetch_filename", False):
            filename = self.prefetch_filename()
            if filename:
                return filename

        if "filename" in self.env:
            filename = self.env["filename"]
        else:
            # Generate filename from URL.
            filename = self.env["url"].rpartition("/")[2]

        return filename

    def get_download_dir(self) -> str:
        """Create download dir and return its path."""
        download_dir = self.env.get("download_dir") or os.path.join(
            self.env["RECIPE_CACHE_DIR"], "downloads"
        )
        if not os.path.exists(download_dir):
            try:
                os.makedirs(download_dir)
            except OSError as err:
                raise ProcessorError(f"Can't create {download_dir}: {err.strerror}")
        return download_dir

    def get_metadata(self) -> dict[str, Any]:
        """
        Retrieves metadata information from a JSON file associated with the current environment's pathname.

        The method attempts to locate a `.info.json` file that corresponds to the `pathname` specified
        in `self.env`. If the file exists, its contents are parsed as JSON and returned as a dictionary.
        If the file does not exist, an empty dictionary is returned.
        """
        pathname_info_json = self.env["pathname"] + ".info.json"

        if os.path.exists(pathname_info_json):
            self.output("Reading metadata from Info JSON.", 2)
            with open(pathname_info_json, "r") as infile:
                metadata = json.load(infile)
                self.output(f"Info JSON contents: {metadata}", 2)
                return metadata

        return {}

    def compute_hashes(self) -> dict[str, str]:
        """
        Computes cryptographic hash values (SHA-1, SHA-256, and MD5) for the file located at
        the current environment's pathname.

        This method reads the file in chunks (4KB at a time) to efficiently handle large files
        without excessive memory usage. Hashes are computed concurrently for:
        - SHA-1
        - SHA-256
        - MD5
        """
        sha1_hasher = sha1()
        sha256_hasher = sha256()
        md5_hasher = md5()

        with open(self.env["pathname"], "rb") as infile:
            for chunk in iter(lambda: infile.read(4096), b""):
                sha1_hasher.update(chunk)
                sha256_hasher.update(chunk)
                md5_hasher.update(chunk)

        return {
            "sha1": sha1_hasher.hexdigest(),
            "sha256": sha256_hasher.hexdigest(),
            "md5": md5_hasher.hexdigest(),
        }

    def create_temp_file(self, download_dir) -> str:
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

    def download_changed(self, header) -> bool:
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
                    f"of the cached file: {size_header} bytes"
                )
                self.output(
                    "WARNING: Matching a download by filesize is a "
                    "fallback mechanism that does not guarantee "
                    "that a build is unchanged."
                )
                self.output(f"Using existing {self.env['pathname']}")
                return False

        if header["http_result_code"] == "304":
            # resource not modified
            self.env["download_changed"] = False
            self.output("Item at URL is unchanged.")
            self.output(f"Using existing {self.env['pathname']}")
            return False

        return True

    def move_temp_file(self, pathname_temporary) -> None:
        """Move temporary download file to pathname."""
        if os.path.exists(self.env["pathname"]):
            os.remove(self.env["pathname"])
        try:
            os.rename(pathname_temporary, self.env["pathname"])
        except OSError:
            raise ProcessorError(
                f"Can't move {pathname_temporary} to {self.env['pathname']}"
            )

    def store_headers(self, header) -> None:
        """Store last-modified and etag headers in pathname xattr."""
        if header.get("last-modified"):
            self.env["last_modified"] = header.get("last-modified")
            xattr.setxattr(
                self.env["pathname"],
                self.xattr_last_modified,
                header.get("last-modified").encode(),
            )
            self.output(
                f"Storing new Last-Modified header: {header.get('last-modified')}"
            )

        self.env["etag"] = ""
        if header.get("etag"):
            self.env["etag"] = header.get("etag")
            xattr.setxattr(
                self.env["pathname"], self.xattr_etag, header.get("etag").encode()
            )
            self.output(f"Storing new ETag header: {header.get('etag')}")

    def store_metadata(self, header: dict[str, Any]) -> None:
        """
        Generates and stores metadata information for the current file and its download source.

        This method constructs a metadata dictionary containing details such as:
        - Download URL
        - File name
        - File size
        - HTTP headers (Content-Length, ETag, Last-Modified)

        If the environment variable `"COMPUTE_HASHES"` is set to `True`, hash values for the file
        (SHA-1, SHA-256, MD5) are also computed and included.

        The metadata is serialized to JSON format and written to a `.info.json` file with a pathname
        matching the current file in `self.env`.

        Additionally, for backward compatibility, headers are stored as extended attributes (xattrs).
        """
        pathname_info_json = self.env["pathname"] + ".info.json"

        self.env["etag"] = header.get("etag", "")
        self.env["file_size"] = os.path.getsize(self.env["pathname"])
        self.env["last_modified"] = header.get("last-modified", "")

        metadata_dict: dict[str, Any] = {
            "download_url": self.env["url"],
            "file_name": self.get_filename() or "",
            "file_size": self.env["file_size"],
            "http_headers": {
                "Content-Length": self.env["file_size"],
                "ETag": self.env["etag"],
                "Last-Modified": self.env["last_modified"],
            },
        }
        if self.env.get("COMPUTE_HASHES", False):
            hashes = self.compute_hashes()
            metadata_dict["file_sha1"] = hashes["sha1"]
            metadata_dict["file_sha256"] = hashes["sha256"]
            metadata_dict["file_md5"] = hashes["md5"]

        metadata_str = json.dumps(metadata_dict, indent=4, sort_keys=True)

        # Write metadata to file
        self.output(f"Storing metadata:\n{metadata_str}")
        with open(pathname_info_json, "w") as outfile:
            outfile.write(metadata_str)

        # For backwards compatibility, set xattrs
        self.store_headers(header)

    def main(self) -> None:
        # Clear and initialize data structures
        self.clear_vars()

        # Ensure existence of necessary files, directories and paths
        filename = self.get_filename()
        if filename is None:
            return
        download_dir = self.get_download_dir()
        self.env["pathname"] = os.path.join(download_dir, filename)
        pathname_temporary = self.create_temp_file(download_dir)

        # Prepare curl command
        curl_cmd = self.prepare_download_curl_cmd(pathname_temporary)

        # Execute curl command and parse headers
        raw_headers = self.download_with_curl(curl_cmd)
        header = self.parse_headers(raw_headers)

        if self.download_changed(header):
            self.env["download_changed"] = True
        else:
            # Discard the temp file
            os.remove(pathname_temporary)
            return

        # New resource was downloaded. Move the temporary download file to the pathname
        self.move_temp_file(pathname_temporary)

        # Save last-modified and etag headers to files xattr
        self.store_metadata(header)

        # Generate output messages and variables
        self.output(f"Downloaded {self.env['pathname']}")
        self.env["url_downloader_summary_result"] = {
            "summary_text": "The following new items were downloaded:",
            "data": {"download_path": self.env["pathname"]},
        }


if __name__ == "__main__":
    PROCESSOR = URLDownloader()
    PROCESSOR.execute_shell()
