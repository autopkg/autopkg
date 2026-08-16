#!/usr/local/autopkg/python
#
# Copyright 2021 James Stewart @JGStew
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

"""See docstring for URLDownloaderPython class"""

import os
import ssl
from hashlib import md5, sha1, sha256
from typing import Any
from urllib.request import Request, urlopen

import certifi
from autopkglib import ProcessorError
from autopkglib.URLDownloader import URLDownloader

__all__ = ["URLDownloaderPython"]


class URLDownloaderPython(URLDownloader):
    """This is meant to be a pure python replacement for URLDownloader
    See: https://github.com/autopkg/autopkg/blob/master/Code/autopkglib/URLDownloader.py
    """

    description = __doc__
    lifecycle = {"introduced": "2.4.1"}
    input_variables = URLDownloader.input_variables.copy()
    input_variables.pop("curl_opts")
    input_variables["request_headers"] = {
        "required": False,
        "description": (
            "Optional dictionary of headers to include with the download request. "
            "Keys are header names and values are header values."
        ),
    }
    output_variables = URLDownloader.output_variables.copy()

    def ssl_context_certifi(self) -> ssl.SSLContext:
        """SSL context using certifi CAs or custom CAs if the env SSL_CERT_FILE is set"""
        # this doesn't need to be a class method
        # https://stackoverflow.com/questions/24374400/verifying-https-certificates-with-urllib-request
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.load_verify_locations(cafile=certifi.where())
        if (cafile := os.environ.get("SSL_CERT_FILE")) is not None:
            self.output(f"SSL_CERT_FILE={cafile}", 1)
            if not os.path.isfile(cafile):
                raise ProcessorError(f"Certificate file '{cafile}' does not exist.")
            if not os.access(cafile, os.R_OK):
                raise ProcessorError(f"Certificate file '{cafile}' is not readable.")
            ctx.load_verify_locations(cafile=cafile)
        return ctx

    def download_and_hash(self, file_save_path) -> dict | None:
        """stream down file from url and calculate size & hashes"""
        # it is much more efficient to calculate hashes WHILE downloading
        # this allows the file to be read only once and never from disk
        # https://github.com/jgstew/bigfix_prefetch/blob/master/src/bigfix_prefetch/prefetch_from_url.py
        url = self.env.get("url")
        download_dictionary: dict[str, Any] = {}

        hashes = None
        if self.env_bool("COMPUTE_HASHES"):
            hashes = (
                sha1(usedforsecurity=False),
                sha256(usedforsecurity=False),
                md5(usedforsecurity=False),
            )

        # chunksize seems like it could be anything
        #   it is probably best if it is a multiple of a typical hash block_size
        #   a larger chunksize is probably best for faster downloads
        #   chunksize should be evenly divisible by 4096 due to 4k blocks of storage
        chunksize = 4096 * 100
        if hashes:
            chunksize = max(chunksize, max(a_hash.block_size for a_hash in hashes))

        size = 0

        file_save = None

        # Build request, adding any provided request headers
        request_headers = self.env.get("request_headers") or {}
        if request_headers and not isinstance(request_headers, dict):
            raise ProcessorError(
                "request_headers must be a dictionary of header-name: value pairs"
            )
        # Normalise header keys to str (in case of non-str) and skip None values
        normalised_headers = {
            str(k): str(v) for k, v in request_headers.items() if v is not None
        }
        request_obj = Request(url, headers=normalised_headers)

        # get http headers
        response = urlopen(
            request_obj, context=self.ssl_context_certifi()
        )  # nosec B310 - file:// is a supported url scheme
        response_headers = response.info()

        version_changed = self.download_changed(response_headers)
        self.env["download_changed"] = version_changed

        # DOWNLOAD_MISSING_FILE only decides whether to re-fetch a file that
        # has gone missing while the remote resource is unchanged; it never changes
        # download_changed.
        previous_download_path = self.env.get("pathname")
        previous_download_exists = bool(
            previous_download_path and os.path.isfile(previous_download_path)
        )
        materialize_missing = not previous_download_exists and self.env_bool(
            "DOWNLOAD_MISSING_FILE", default=True
        )

        # Unchanged and either the cached file is present or we've been told
        # not to re-fetch it: don't read the body, just reuse existing hashes.
        if not version_changed and not materialize_missing:
            os.remove(file_save_path)
            self.publish_existing_hashes()
            return None

        # download file
        if file_save_path:
            file_save = open(file_save_path, "wb")

        try:
            while True:
                chunk = response.read(chunksize)
                if not chunk:
                    break
                # get size of chunk and add to existing size
                size += len(chunk)
                # add chunk to hash computations
                if hashes:
                    for a_hash in hashes:
                        a_hash.update(chunk)
                # save file if handler
                if file_save:
                    file_save.write(chunk)
        finally:
            # close file handler if used
            if file_save:
                file_save.close()

        download_dictionary["file_name"] = self.env.get("filename", "")
        download_dictionary["file_size"] = size
        self.env["file_size"] = size
        if hashes:
            self.store_hashes_in_env(
                {
                    "sha1": hashes[0].hexdigest(),
                    "sha256": hashes[1].hexdigest(),
                    "md5": hashes[2].hexdigest(),
                }
            )
            download_dictionary["file_sha1"] = self.env["file_sha1"]
            download_dictionary["file_sha256"] = self.env["file_sha256"]
            download_dictionary["file_md5"] = self.env["file_md5"]
        download_url = response.url or url
        download_dictionary["download_url"] = download_url
        self.env["download_url"] = download_url
        # download_dictionary['http_headers'] = response.info()
        download_dictionary["http_headers"] = self.download_headers(
            response.headers, size
        )
        self.env["etag"] = download_dictionary["http_headers"]["ETag"]
        self.env["last_modified"] = download_dictionary["http_headers"]["Last-Modified"]
        try:
            content_length = int(response.headers.get("Content-Length", size))
        except (TypeError, ValueError):
            content_length = size
        if content_length != size:
            self.output("WARNING: file size != content-length header")

        # We streamed a fresh copy (the remote resource changed, or the file was
        # missing and DOWNLOAD_MISSING_FILE is set), so move it into place.
        self.move_temp_file(file_save_path)

        # Save last-modified and etag headers to files xattr
        # This is for backwards compatibility with URLDownloader
        try:
            # this can throw errors on Linux running in WSL
            # it might also throw errors on Linux containers
            self.store_headers(response.info())
        except OSError as err:
            self.output(
                "ERROR xattr: ({err_type})\n{err}\n".format(
                    err=err, err_type=type(err).__name__
                ),
                1,
            )

        return download_dictionary

    def main(self) -> None:
        """Execution starts here"""
        # Clear and initialize data structures
        self.clear_vars()

        # self.prefetch_filename()

        # Ensure existence of necessary files, directories and paths
        filename = self.get_filename()
        if filename is None:
            return
        self.env["filename"] = filename
        download_dir = self.get_download_dir()
        self.env["pathname"] = os.path.join(download_dir, filename)

        # clear empty file from previous run
        self.clear_zero_file(self.env["pathname"])

        pathname_temporary = self.create_temp_file(download_dir)

        # download file
        download_dictionary = self.download_and_hash(pathname_temporary)

        self.output(
            "download_dictionary: \n{download_dictionary}\n".format(
                download_dictionary=download_dictionary
            ),
            2,
        )

        # clear temp file if 0 size
        self.clear_zero_file(pathname_temporary)

        if self.env["download_changed"] and download_dictionary is None:
            raise ProcessorError("Download did not produce metadata.")
        if download_dictionary is not None:
            self.write_metadata(download_dictionary)
            self.report_download(self.env["download_changed"])

        self.output(f"self.env: \n{self.env}\n", 4)


if __name__ == "__main__":
    PROCESSOR = URLDownloaderPython()
    PROCESSOR.execute_shell()
