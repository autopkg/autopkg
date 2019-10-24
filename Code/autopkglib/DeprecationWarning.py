#!/usr/bin/python
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
"""Processor that outputs a warning message. Intended to alert recipe users of
upcoming removal of a recipe."""


import os

from autopkglib import Processor


__all__ = ["DeprecationWarning"]


class DeprecationWarning(Processor):
    """This processor outputs a warning that the recipe has been deprecated."""

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

    def main(self):
        warning_message = self.env.get(
            "warning_message",
            "### This recipe has been deprecated. It may be removed soon. ###",
        )
        self.output(warning_message)
        recipe_name = os.path.basename(self.env["RECIPE_PATH"])
        if recipe_name.endswith(".recipe"):
            recipe_name = os.path.splitext(recipe_name)[0]
        self.env["deprecation_summary_result"] = {
            "summary_text": "The following recipes have deprecation warnings:",
            "report_fields": ["name", "warning"],
            "data": {"name": recipe_name, "warning": warning_message},
        }


if __name__ == "__main__":
    PROCESSOR = DeprecationWarning()
    PROCESSOR.execute_shell()
