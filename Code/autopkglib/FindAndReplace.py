#!/usr/local/autopkg/python
#
# Copyright 2016-2025 Elliot Jordan
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
"""See docstring for FindAndReplace class"""

from autopkglib import Processor  # noqa: F401

__all__ = ["FindAndReplace"]


class FindAndReplace(Processor):
    """Searches the provided 'input_string' and replaces instances of the 'find'
    string with the 'replace' string.

    Returns 'output_string' containing the result of the find/replace operation.

    Requires version 2.7.6.
    """

    input_variables = {
        "input_string": {
            "required": True,
            "description": "The string you want to perform find/replace on.",
        },
        "find": {
            "required": True,
            "description": "This string, if found, will be replaced with the "
            '"replace" string.',
        },
        "replace": {
            "required": True,
            "description": 'The string that you want to replace the "find" '
            "string with.",
        },
        "replace_output_var": {
            "required": False,
            "default": "output_string",
            "description": "Variable to store the output to, defaults to `output_string`",
        },
    }
    output_variables = {
        "output_string": {
            "description": "The result of find/replace on the input string."
        }
    }
    description = __doc__

    def main(self) -> None:
        """Main process."""

        input_string = self.env["input_string"]
        
        # get name of variable to store output
        replace_output_var = self.env.get("replace_output_var", "output_string")
        
        find = self.env["find"]
        replace = self.env["replace"]
        self.output(f'Replacing "{find}" with "{replace}" in "{input_string}".')
        self.env[replace_output_var] = self.env["input_string"].replace(find, replace)

        # remove output_string from output variables in case a custom one was specified.
        del self.output_variables["output_string"]
        # set the custom or default output variable name in output_variables so it shows up in verbose output.
        self.output_variables[replace_output_var] = {
            "description": "The result of find/replace on the input string.",
        }


if __name__ == "__main__":
    PROCESSOR = FindAndReplace()
    PROCESSOR.execute_shell()
