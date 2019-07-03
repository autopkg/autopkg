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

from autopkglib import Processor, ProcessorError, get_pref, log_err

__all__ = ["URLGetter"]


class URLGetter(Processor):
    """Handles curl HTTP operatios. Server only as superclass. Not for direct use."""

    description = __doc__

    def curl_binary(self):
        """Returns a path to a curl binary, priority in the order below.
        Returns None if none found.
        1. env['CURL_PATH']
        2. app pref 'CURL_PATH'
        3. a 'curl' binary that can be found in the PATH environment variable
        4. '/usr/bin/curl'
        """

        def is_executable(exe_path):
            """Is exe_path executable?"""
            return os.path.exists(exe_path) and os.access(exe_path, os.X_OK)

        if "CURL_PATH" in self.env and is_executable(self.env["CURL_PATH"]):
            return self.env["CURL_PATH"]

        curl_path_pref = get_pref("CURL_PATH")
        if curl_path_pref:
            if is_executable(curl_path_pref):
                # take a CURL_PATH pref
                return curl_path_pref
            else:
                log_err(
                    "WARNING: Curl path given in the 'CURL_PATH' preference:'%s' "
                    "either doesn't exist or is not executable! Falling back "
                    "to one set in PATH, or /usr/bin/curl." % curl_path_pref
                )

        for path_env in os.environ["PATH"].split(":"):
            curlbin = os.path.join(path_env, "curl")
            if is_executable(curlbin):
                # take the first 'curl' in PATH that we find
                return curlbin

        if is_executable("/usr/bin/curl"):
            # fall back to /usr/bin/curl
            return "/usr/bin/curl"

        raise ProcessorError("Unable to execute any curl binary")

    def add_curl_common_opts(self, curl_cmd):
        """Adds request_headers and curl_opts to curl_cmd"""
        for header, value in self.env.get("request_headers", {}).items():
            curl_cmd.extend(["--header", "%s: %s" % (header, value)])

        for item in self.env.get("curl_opts", []):
            curl_cmd.extend([item])

    def clear_header(self, header):
        """Clear header dictionary"""
        header.clear()
        header["http_result_code"] = "000"
        header["http_result_description"] = ""

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
        """Report Curl failure."""
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

    def parse_headers(self, proc_stdout, header):
        """Parse headers from Curl."""
        for line in proc_stdout.splitlines():
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
                    self.clear_header(header)

    def execute_curl(self, curl_cmd):
        """Executes curl comamnd. Returns stdout, stderr and return code."""
        proc = subprocess.Popen(
            curl_cmd,
            shell=False,
            bufsize=1,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        proc_stdout, proc_stderr = proc.communicate()
        retcode = proc.returncode

        return proc_stdout, proc_stderr, retcode

    def download(self, curl_cmd):
        """Downloads file using curl and returns raw headers."""

        proc_stdout, proc_stderr, retcode = self.execute_curl(curl_cmd)

        if retcode:  # Non-zero exit code from curl => problem with download
            curl_err = self.parse_curl_error(proc_stderr)
            raise ProcessorError(
                "Curl failure: %s (exit code %s)" % (curl_err, retcode)
            )

        return proc_stdout

    def main(self):
        pass


if __name__ == "__main__":
    PROCESSOR = URLGetter()
    PROCESSOR.execute_shell()
