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

import json
import os
import ssl
from hashlib import md5, sha1, sha256
from urllib.request import Request, urlopen

import certifi
from autopkglib.URLDownloader import URLDownloader

__all__ = ["URLDownloaderPython"]


class URLDownloaderPython(URLDownloader):
    """This is meant to be a pure python replacement for URLDownloader
    
    Prefetch Filename is still using URLDownloader's curl methods, rather than python.
    
    See: https://github.com/autopkg/autopkg/blob/master/Code/autopkglib/URLDownloader.py
    """

    description = __doc__
    input_variables = {
        "url": {"required": True, "description": "The URL to download."},
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
            "default": False,
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
        "COMPUTE_HASHES": {
            "required": False,
            "default": False,
            "description": (
                "Local path to the pkg/dmg we'd otherwise download. "
                "If provided, the download is skipped and we just use "
                "this package or disk image."
            ),
        },
        "HEADERS_TO_TEST": {
            "required": False,
            "default": ["ETag", "Last-Modified", "Content-Length"],
            "description": (
                "Local path to the pkg/dmg we'd otherwise download. "
                "If provided, the download is skipped and we just use "
                "this package or disk image."
            ),
        },
        "User_Agent": {
            "required": False,
            "description": ("User Agent Header String to use for download"),
        },
        "download_version": {
            "required": False,
            "description": ("version of download"),
        },
        "disable_ssl_validation": {
            "required": False,
            "default": False,
            "description": "Disables SSL Validation. WARNING: dangerous!",
        },
        "download_missing_file": {
            "required": False,
            "default": True,
            "description": """
            If the file is missing,
             but the metadata is present that shows it is the same file,
             skip download?
            """,
        },
        "download_save_file": {
            "required": False,
            "default": True,
            "description": """
            Save download file?
            If False, then only metadata will be saved, not the download file.
            This will cause problems if the download file is required for future steps.
            This is treated as True if `download_missing_file` is True
             regardless of value supplied.
            This is designed to be used in AWS Lambda or similar Docker use cases.
            Only as much RAM as consumed by `chunksize`
             within `download_and_hash()` plus overhead is requried
             because the file is never fully read into memory and never written to disk
             if this setting is used.
            """,
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
        "download_info": {"description": "Info from previous or current download."},
        "url_downloader_summary_result": {
            "description": "Description of interesting results."
        },
    }
    __doc__ = description

    def download_changed(self, header):
        """Check if downloaded file changed on server."""

        self.output("HTTP Headers: \n{headers}".format(headers=header), 2)

        # get the list of headers to check
        headers_to_test = self.env.get("HEADERS_TO_TEST", None)

        self.output(
            "headers_to_test: {headers_to_test}".format(
                headers_to_test=headers_to_test
            ),
            2,
        )

        # get previous info to compare
        previous_download_info = self.get_download_info_json()

        if not previous_download_info:
            # no previous download info to check against
            # could check against xattr values if supported?
            return True

        # store previous download info in case we don't download again
        self.env["download_info"] = previous_download_info

        # always store last modified in case we don't download again
        # this wouldn't get set if `download_version` is used for download detection
        try:
            self.env["last_modified"] = previous_download_info["http_headers"][
                "Last-Modified"
            ]
        except KeyError:
            pass

        self.output(
            "previous_download_info: \n{previous_download_info}\n".format(
                previous_download_info=previous_download_info
            ),
            2,
        )

        # store previous download_url in case we don't download again
        if "download_url" in previous_download_info:
            self.env["download_url"] = previous_download_info["download_url"]

        # check that previous download exits:
        previous_download_path = self.env.get("pathname", None)
        download_missing_file = self.env.get("download_missing_file", True)
        if not os.path.isfile(previous_download_path):
            # previous download doesn't exist!
            if download_missing_file:
                return True

        download_version = self.env.get("download_version", None)
        # compare versions:
        if download_version:
            self.output(download_version, 1)
            if "version" in previous_download_info:
                self.output(previous_download_info["version"], 1)
                if download_version != previous_download_info["version"]:
                    self.output(
                        "Download Changed: version does not match previous download"
                    )
                    return True
                else:
                    self.output(
                        "Download UNCHANGED: version does match previous download"
                    )
                    return False

        header_matches = 0

        try:
            # check Content-Length:
            if (
                headers_to_test
                and "Content-Length" in headers_to_test
                and (
                    int(previous_download_info["http_headers"]["Content-Length"])
                    != int(header.get("Content-Length"))
                )
            ):
                self.output("Content-Length is different", 1)
                return True
            else:
                header_matches += 1
        except (KeyError, TypeError) as err:
            self.output(
                "WARNING: 'Content-Length' missing. ({err_type}) {err}".format(
                    err=err, err_type=type(err).__name__
                ),
                1,
            )

        # check other headers:
        for test in headers_to_test:
            if test != "Content-Length":
                try:
                    if previous_download_info["http_headers"][test] != header.get(test):
                        self.output("{test} is different".format(test=test), 1)
                        return True
                    else:
                        header_matches += 1
                        if test == "Last-Modified":
                            self.env["last_modified"] = previous_download_info[
                                "http_headers"
                            ][test]
                        if test == "ETag":
                            self.env["etag"] = previous_download_info["http_headers"][
                                test
                            ]
                except (KeyError, TypeError) as err:
                    self.output(
                        "WARNING: header missing. ({err_type}) {err}".format(
                            err=err, err_type=type(err).__name__
                        ),
                        1,
                    )

        # if no header checks work without throwing exceptions:
        if header_matches == 0:
            return True
        # if all above pass, then return False:
        # NOTE: this could think the download is unchanged when 1 header matches
        #  but not all headers match
        return False

    def store_download_info_json(self, download_dictionary):
        """If file is downloaded, store info"""
        pathname = self.env.get("pathname")
        pathname_info_json = pathname + ".info.json"
        # put new download info into env:
        self.env["download_info"] = download_dictionary
        # https://stackoverflow.com/questions/16267767/python-writing-json-to-file
        with open(pathname_info_json, "w") as outfile:
            json.dump(download_dictionary, outfile, indent=4)
            # add newline at end of file:
            outfile.write("\n")

    def get_download_info_json(self):
        """get info from previous download"""
        pathname = self.env.get("pathname")
        pathname_info_json = pathname + ".info.json"

        try:
            with open(pathname_info_json, "r") as infile:
                info_json = json.load(infile)
        except FileNotFoundError as err:
            self.output(
                "WARNING: missing download info ({err_type})\n{err}\n".format(
                    err=err, err_type=type(err).__name__
                ),
                1,
            )
            return None

        return info_json

    def ssl_context_ignore(self):
        """ssl context - ignore SSL validation"""
        # this doesn't need to be a class method
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.output("WARNING: disabling SSL validation is insecure!!!")
        return ctx

    def ssl_context_certifi(self):
        """ssl context using certifi CAs"""
        # this doesn't need to be a class method
        # https://stackoverflow.com/questions/24374400/verifying-https-certificates-with-urllib-request
        return ssl.create_default_context(cafile=certifi.where())

    def download_and_hash(self, file_save_path):
        """stream down file from url and calculate size & hashes"""
        # it is much more efficient to calculate hashes WHILE downloading
        # this allows the file to be read only once and never from disk
        # https://github.com/jgstew/bigfix_prefetch/blob/master/src/bigfix_prefetch/prefetch_from_url.py
        url = self.env.get("url")
        download_dictionary = {}

        hashes = None
        if self.env.get("COMPUTE_HASHES", None):
            hashes = sha1(), sha256(), md5()

        # chunksize seems like it could be anything
        #   it is probably best if it is a multiple of a typical hash block_size
        #   a larger chunksize is probably best for faster downloads
        #   chunksize should be evenly divisible by 4096 due to 4k blocks of storage
        chunksize = 4096 * 100
        if hashes:
            chunksize = max(chunksize, max(a_hash.block_size for a_hash in hashes))

        size = 0

        file_save = None

        if file_save_path:
            file_save = open(file_save_path, "wb")

        # get http headers
        req = Request(url)
        # the following may be required in some cases:
        user_agent_value = self.env.get("User_Agent", None)
        if user_agent_value:
            req.add_header("User-Agent", user_agent_value)

        ssl_context = self.ssl_context_certifi()
        # ssl_context = ssl.create_default_context()
        disable_ssl_validation = self.env.get("disable_ssl_validation", False)
        if disable_ssl_validation:
            ssl_context = self.ssl_context_ignore()

        # timeout of 2 hours
        response = urlopen(req, context=ssl_context, timeout=7200)
        response_headers = response.info()

        self.env["download_changed"] = self.download_changed(response_headers)
        # check if download changed from last run:
        if not self.env.get("download_changed", None):
            # Close file handle
            if file_save:
                file_save.close()
            # Discard the temp file
            if file_save_path:
                self.clear_zero_file(file_save_path)
            return None

        self.output("INFO: Downloading New File")

        # download file
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

        # close file handler if used
        if file_save:
            file_save.close()

        if self.env.get("download_changed", None):
            # Move the new temporary download file to the pathname
            if file_save_path:
                self.move_temp_file(file_save_path)

        download_dictionary["file_name"] = self.env.get("filename", "")
        download_dictionary["file_size"] = size
        if hashes:
            download_dictionary["file_sha1"] = hashes[0].hexdigest()
            download_dictionary["file_sha256"] = hashes[1].hexdigest()
            download_dictionary["file_md5"] = hashes[2].hexdigest()
        download_dictionary["url"] = url

        # store new download url:
        if response.url:
            download_url = response.url
            download_dictionary["download_url"] = download_url
            self.env["download_url"] = download_url

        download_version = self.env.get(
            "download_version", self.env.get("version", None)
        )
        if download_version:
            download_dictionary["version"] = download_version
        # download_dictionary['http_headers'] = response.info()
        try:
            # save http header info to dict
            download_dictionary["http_headers"] = {}
            if "content-length" in response.headers:
                download_dictionary["http_headers"]["Content-Length"] = int(
                    response.headers["content-length"]
                )
                if download_dictionary["http_headers"]["Content-Length"] != size:
                    # should this be a halting error?
                    self.output("WARNING: file size != content-length header", 0)
            if "ETag" in response.headers:
                download_dictionary["http_headers"]["ETag"] = response.headers["ETag"]
            if "Last-Modified" in response.headers:
                download_dictionary["http_headers"]["Last-Modified"] = response.headers[
                    "Last-Modified"
                ]
        except (KeyError, TypeError) as err:
            # probably need to handle a missing header better than this
            self.output(
                "ERROR: header issue ({err_type})\n{err}\n".format(
                    err=err, err_type=type(err).__name__
                )
            )
            return download_dictionary

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

    def main(self):
        """Execution starts here"""
        # Clear and initiazize data structures
        self.clear_vars()

        # if download_missing_file is True, then download_save_file must be true
        download_missing_file = self.env.get("download_missing_file", True)
        if download_missing_file:
            self.env["download_save_file"] = True

        # Ensure existence of necessary files, directories and paths
        filename = self.get_filename()
        if filename is None:
            return

        # in some cases, the filename could have html parameters after:
        if "?" in filename:
            self.output("Removing ? and following characters from filename", 0)
            # this fix should be applied to URLDownloader.prefetch_filename()
            filename = filename.split("?", 1)[0]

        self.env["filename"] = filename
        download_dir = self.get_download_dir()
        self.env["pathname"] = os.path.join(download_dir, filename)

        # clear empty file from previous run
        self.clear_zero_file(self.env["pathname"])

        # change headers to test if CHECK_FILESIZE_ONLY
        if self.env.get("CHECK_FILESIZE_ONLY", None):
            self.env["HEADERS_TO_TEST"] = ["Content-Length"]

        download_save_file = self.env.get("download_save_file", True)
        pathname_temporary = None
        # if download_save_file is false, then do not store the file being "downloaded"
        if download_save_file:
            pathname_temporary = self.create_temp_file(download_dir)

        # download file
        download_dictionary = self.download_and_hash(pathname_temporary)

        self.output(
            "download_dictionary: \n{download_dictionary}\n".format(
                download_dictionary=download_dictionary
            )
        )

        # clear temp file if 0 size
        if pathname_temporary:
            self.clear_zero_file(pathname_temporary)

        if self.env.get("download_changed", None):
            # store download info for checking for existing download
            self.store_download_info_json(download_dictionary)

            if download_dictionary and "http_headers" in download_dictionary:
                if "ETag" in download_dictionary["http_headers"]:
                    self.env["etag"] = download_dictionary["http_headers"]["ETag"]
                if "Last-Modified" in download_dictionary["http_headers"]:
                    self.env["last_modified"] = download_dictionary["http_headers"][
                        "Last-Modified"
                    ]

            # Generate output messages and variables
            self.output(f"Downloaded {self.env['pathname']}")
            self.env["url_downloader_summary_result"] = {
                "summary_text": "The following new items were downloaded:",
                "data": {"download_path": self.env["pathname"]},
            }

        self.output("self.env: \n{self_env}\n".format(self_env=self.env), 4)


if __name__ == "__main__":
    PROCESSOR = URLDownloaderPython()
    PROCESSOR.execute_shell()
