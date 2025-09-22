#!/usr/local/autopkg/python
#
# Copyright 2019 Greg Neagle
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
"""See docstring for DeprecationWarning class"""


from autopkglib import Processor

__all__ = ["DeprecationWarning"]


# pylint: disable=W0622
class DeprecationWarning(Processor):
    """This processor outputs a warning that a recipe has been deprecated."""

    input_variables = {
        "warning_message": {
            "required": False,
            "description": "Warning message to output.",
        }
    }
    output_variables = {
        "deprecation_summary_result": {
            "description": "Description of interesting results."
        }
    }
    description = __doc__

    def main(self) -> None:
        warning_message = self.env.get(
            "warning_message",
            "### This recipe has been deprecated. It may be removed soon. ###",
        )
        self.show_deprecation(warning_message)


if __name__ == "__main__":
    PROCESSOR = DeprecationWarning()
    PROCESSOR.execute_shell()
