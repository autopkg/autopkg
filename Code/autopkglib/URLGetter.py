#!/usr/bin/python
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

from autopkglib import Processor, ProcessorError, get_pref, is_executable, log_err

__all__ = ["URLGetter"]


class URLGetter(Processor):
    """Handles curl HTTP operations. Serves only as superclass. Not for direct use."""

    description = __doc__

    def curl_binary(self):
        """Return a path to a curl binary, priority in the order below.
        Return None if none found.
        1. env['CURL_PATH']
        2. app pref 'CURL_PATH'
        3. a 'curl' binary that can be found in the PATH environment variable
        4. '/usr/bin/curl'
        """

        if "CURL_PATH" in self.env and is_executable(self.env["CURL_PATH"]):
            return self.env["CURL_PATH"]

        curl_path_pref = get_pref("CURL_PATH")
        if curl_path_pref:
            if is_executable(curl_path_pref):
                return curl_path_pref
            else:
                log_err(
                    "WARNING: curl path given in the 'CURL_PATH' preference:'{}' "
                    "either doesn't exist or is not executable! Falling back "
                    "to one set in PATH, or /usr/bin/curl.".format(curl_path_pref)
                )

        for path_env in os.environ["PATH"].split(":"):
            curlbin = os.path.join(path_env, "curl")
            if is_executable(curlbin):
                return curlbin

        if is_executable("/usr/bin/curl"):
            return "/usr/bin/curl"

        raise ProcessorError("Unable to locate or execute any curl binary")

    def prepare_curl_cmd(self):
        """Assemble basic curl command and return it."""
        return [self.curl_binary(), "--compressed", "--location"]

    def add_curl_headers(self, curl_cmd, headers):
        """Add headers to curl_cmd"""
        if headers:
            for header, value in headers.items():
                curl_cmd.extend(["--header", "{}: {}".format(header, value)])

    def add_curl_common_opts(self, curl_cmd):
        """Add request_headers and curl_opts to curl_cmd"""
        self.add_curl_headers(curl_cmd, self.env.get("request_headers"))

        for item in self.env.get("curl_opts", []):
            curl_cmd.extend([item])

    def clear_header(self, header):
        """Clear header dictionary"""
        # Save redirect URL before clear
        http_redirected = header.get("http_redirected", None)
        header.clear()
        header["http_result_code"] = "000"
        header["http_result_description"] = ""

        # Restore redirect URL
        header["http_redirected"] = http_redirected

    def parse_http_protocol(self, line, header):
        """Parse first HTTP header line"""
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
            elif self.env["url"].startswith("ftp://"):
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

    def execute_curl(self, curl_cmd):
        """Execute curl comamnd. Return stdout, stderr and return code."""
        proc = subprocess.Popen(
            curl_cmd,
            shell=False,
            bufsize=1,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        proc_stdout, proc_stderr = proc.communicate()

        return proc_stdout, proc_stderr, proc.returncode

    def download_with_curl(self, curl_cmd):
        """Launch curl, return its output, and handle failures."""

        proc_stdout, proc_stderr, retcode = self.execute_curl(curl_cmd)

        if retcode:  # Non-zero exit code from curl => problem with download
            curl_err = self.parse_curl_error(proc_stderr)
            raise ProcessorError(
                "curl failure: {} (exit code {})".format(curl_err, retcode)
            )

        return proc_stdout

    def download(self, url, headers=None, text=False):
        """Download content with default curl options"""

        curl_cmd = self.prepare_curl_cmd()
        self.add_curl_headers(curl_cmd, headers)
        curl_cmd.append(url)
        output = self.download_with_curl(curl_cmd)

        return output

    def main(self):
        pass


if __name__ == "__main__":
    PROCESSOR = URLGetter()
    PROCESSOR.execute_shell()
