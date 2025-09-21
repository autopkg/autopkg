#!/usr/local/autopkg/python
#
# Refactoring 2018 Michal Moravec
# Copyright 2015 Greg Neagle
# Based on URLTextSearcher.py, Copyright 2014 Jesse Peterson
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
"""See docstring for URLTextSearcher class"""

import re

from autopkglib import ProcessorError
from autopkglib.URLGetter import URLGetter

MATCH_MESSAGE = "Found matching text"
NO_MATCH_MESSAGE = "No match found on URL"

__all__ = ["URLTextSearcher"]


class URLTextSearcher(URLGetter):
    """Downloads a URL using curl and performs a regular expression match
    on the text.

    Requires version 1.4."""

    input_variables = {
        "re_pattern": {
            "required": True,
            "description": "Regular expression (Python) to match against page.",
        },
        "url": {
            "required": True,
            "description": "URL to search for the regex pattern.",
        },
        "result_output_var_name": {
            "required": False,
            "description": (
                "The name of the output variable that is returned "
                "by the match. If not specified then a default of "
                '"match" will be used.'
            ),
            "default": "match",
        },
        "request_headers": {
            "required": False,
            "description": (
                "Optional dictionary of headers to include with "
                "the download request."
            ),
        },
        "curl_opts": {
            "required": False,
            "description": (
                "Optional array of curl options to include with "
                "the download request."
            ),
        },
        "re_flags": {
            "required": False,
            "description": (
                "Optional array of strings of Python regular "
                "expression flags. E.g. IGNORECASE."
            ),
        },
    }
    output_variables = {
        "result_output_var_name": {
            "description": (
                "First matched sub-pattern from input found on the fetched "
                "URL. Note the actual name of variable depends on the input "
                'variable "result_output_var_name" or is assigned a default of '
                '"match."'
            )
        }
    }

    description = __doc__

    def prepare_curl_cmd(self) -> list[str]:
        """Assemble curl command and return it."""
        curl_cmd = super().prepare_curl_cmd()
        self.add_curl_common_opts(curl_cmd)
        curl_cmd.append(self.env["url"])
        return curl_cmd

    def prepare_re_flags(self) -> int:
        """Create flag variable for re.compile"""
        flag_accumulator = 0
        for flag in self.env.get("re_flags", {}):
            if flag in re.__dict__:
                flag_accumulator += re.__dict__[flag]
        return flag_accumulator

    def re_search(self, content) -> tuple[str, dict[str, str]] | None:
        """Search for re_pattern in content"""

        re_pattern = re.compile(self.env["re_pattern"], flags=self.prepare_re_flags())
        match = re_pattern.search(content)

        if not match:
            raise ProcessorError(f"{NO_MATCH_MESSAGE}: {self.env['url']}")

        # return the last matched group with the dict of named groups
        return (match.group(match.lastindex or 0), match.groupdict())

    def main(self) -> None:
        output_var_name = self.env["result_output_var_name"]

        # Prepare curl command
        curl_cmd = self.prepare_curl_cmd()

        # Execute curl command and search in content
        content = self.download_with_curl(curl_cmd)
        groupmatch, groupdict = self.re_search(content)

        # favor a named group over a normal group match
        if output_var_name not in groupdict.keys():
            groupdict[output_var_name] = groupmatch

        self.output_variables = {}
        for key in groupdict.keys():
            self.env[key] = groupdict[key]
            self.output(f"{MATCH_MESSAGE} ({key}): {self.env[key]}")
            self.output_variables[key] = {
                "description": "Matched regular expression group"
            }


if __name__ == "__main__":
    PROCESSOR = URLTextSearcher()
    PROCESSOR.execute_shell()
