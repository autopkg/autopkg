#!/usr/local/autopkg/python
#
# Copyright 2018 Michal Moravec
# Based on code from Greg Neagle, Timothy Sutton and Per Olofsson
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
"""See docstring for URLGetter class"""

import os.path
import subprocess

from autopkglib import Processor, ProcessorError, find_binary, is_windows

__all__ = ["URLGetter"]


class URLGetter(Processor):
    """Handles curl HTTP operations. Serves only as superclass. Not for direct use."""

    description = __doc__

    def __init__(self, env=None, infile=None, outfile=None):
        super().__init__(env, infile, outfile)
        if not self.env:
            self.env = {}

    def curl_binary(self):
        """Return a path to a curl binary, priority in the order below.
        Return None if none found.
        1. env['CURL_PATH']
        2. app pref 'CURL_PATH'
        3. a 'curl' binary that can be found in the PATH environment variable
        4. '/usr/bin/curl' (POSIX-y platforms only)
        """

        curlbin = find_binary("curl", self.env)
        if curlbin is not None:
            return curlbin

        raise ProcessorError("Unable to locate or execute any curl binary")

    def prepare_curl_cmd(self):
        """Assemble basic curl command and return it."""
        curl_bin_path = self.curl_binary()
        # fix windows default curl support
        if is_windows() and "windows\\system32" in curl_bin_path.lower():
            return [curl_bin_path, "--location"]
        return [curl_bin_path, "--compressed", "--location"]

    def add_curl_headers(self, curl_cmd, headers):
        """Add headers to curl_cmd."""
        if headers:
            for header, value in headers.items():
                curl_cmd.extend(["--header", f"{header}: {value}"])

    def add_curl_common_opts(self, curl_cmd):
        """Add request_headers and curl_opts to curl_cmd."""
        self.add_curl_headers(curl_cmd, self.env.get("request_headers"))

        for item in self.env.get("curl_opts", []):
            curl_cmd.extend([item])

    def produce_etag_headers(self, filename):
        """Produce a dict of curl headers containing etag headers from the download."""
        headers = {}
        # If the download file already exists, add some headers to the request
        # so we don't retrieve the content if it hasn't changed
        if os.path.exists(filename):
            self.existing_file_size = os.path.getsize(filename)
            etag = self.getxattr(self.xattr_etag)
            last_modified = self.getxattr(self.xattr_last_modified)
            if etag:
                headers["If-None-Match"] = etag
            if last_modified:
                headers["If-Modified-Since"] = last_modified
        return headers

    def clear_header(self, header):
        """Clear header dictionary."""
        # Save redirect URL before clear
        http_redirected = header.get("http_redirected", None)
        header.clear()
        header["http_result_code"] = "000"
        header["http_result_description"] = ""
        # Restore redirect URL
        header["http_redirected"] = http_redirected

    def parse_http_protocol(self, line, header):
        """Parse first HTTP header line."""
        try:
            header["http_result_code"] = line.split(None, 2)[1]
            header["http_result_description"] = line.split(None, 2)[2]
        except IndexError:
            pass

    def parse_http_header(self, line, header):
        """Parse single HTTP header line."""
        part = line.split(None, 1)
        fieldname = part[0].rstrip(":").lower()
        try:
            header[fieldname] = part[1]
        except IndexError:
            header[fieldname] = ""

    def parse_curl_error(self, proc_stderr):
        """Report curl failure."""
        curl_err = ""
        try:
            curl_err = proc_stderr.rstrip("\n")
            curl_err = curl_err.split(None, 2)[2]
        except IndexError:
            pass

        return curl_err

    def parse_ftp_header(self, line, header):
        """Parse single FTP header line."""
        part = line.split(None, 1)
        responsecode = part[0]
        if responsecode == "213":
            # This is the reply to curl's SIZE command on the file
            # We can map it to the HTTP content-length header
            try:
                header["content-length"] = part[1]
            except IndexError:
                pass
        elif responsecode.startswith("55"):
            header["http_result_code"] = "404"
            header["http_result_description"] = line
        elif responsecode == "150" or responsecode == "125":
            header["http_result_code"] = "200"
            header["http_result_description"] = line

    def parse_headers(self, raw_headers):
        """Parse headers from curl."""
        header = {}
        self.clear_header(header)
        for line in raw_headers.splitlines():
            if line.startswith("HTTP/"):
                self.parse_http_protocol(line, header)
            elif ": " in line:
                self.parse_http_header(line, header)
            elif self.env.get("url", "").startswith("ftp://"):
                self.parse_ftp_header(line, header)
            elif line == "":
                # we got an empty line; end of headers (or curl exited)
                if header.get("http_result_code") in [
                    "301",
                    "302",
                    "303",
                    "307",
                    "308",
                ]:
                    # redirect, so more headers are coming.
                    # Throw away the headers we've received so far
                    header["http_redirected"] = header.get("location", None)
                    self.clear_header(header)
        return header

    def execute_curl(self, curl_cmd, text=True):
        """Execute curl command. Return stdout, stderr and return code."""
        errors = "ignore" if text else None
        try:
            result = subprocess.run(
                curl_cmd,
                shell=False,
                bufsize=1,
                capture_output=True,
                check=True,
                text=text,
                errors=errors,
            )
        except subprocess.CalledProcessError as e:
            raise ProcessorError(e)
        return result.stdout, result.stderr, result.returncode

    def download_with_curl(self, curl_cmd, text=True):
        """Launch curl, return its output, and handle failures."""
        proc_stdout, proc_stderr, retcode = self.execute_curl(curl_cmd, text)
        self.output(f"Curl command: {curl_cmd}", verbose_level=4)
        if retcode:  # Non-zero exit code from curl => problem with download
            curl_err = self.parse_curl_error(proc_stderr)
            raise ProcessorError(f"curl failure: {curl_err} (exit code {retcode})")
        return proc_stdout

    def download(self, url, headers=None, text=False):
        """Download content with default curl options."""
        curl_cmd = self.prepare_curl_cmd()
        self.add_curl_headers(curl_cmd, headers)
        curl_cmd.append(url)
        output = self.download_with_curl(curl_cmd, text)
        return output

    def download_to_file(self, url, filename, headers=None):
        """Download content to a file with default curl options."""
        curl_cmd = self.prepare_curl_cmd()
        self.add_curl_headers(curl_cmd, headers)
        curl_cmd.append(url)
        curl_cmd.extend(["-o", filename])
        self.download_with_curl(curl_cmd, text=False)
        if os.path.exists(filename):
            return filename
        raise ProcessorError(f"{filename} was not written!")

    def main(self):
        pass


if __name__ == "__main__":
    PROCESSOR = URLGetter()
    PROCESSOR.execute_shell()
