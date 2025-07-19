#!/usr/local/autopkg/python
#
# Copyright 2013 Greg Neagle
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
"""See docstring for MunkiCatalogBuilder class"""

import os

from autopkglib import Processor, remove_recipe_extension

__all__ = ["MunkiCatalogBuilder"]


class MunkiCatalogBuilder(Processor):
    """DEPRECATED. This processor now emits a warning and performs no function.
    Previously it rebuilt Munki catalogs."""

    input_variables = {}
    output_variables = {}
    description = __doc__

    def main(self) -> None:
        warning_message = self.env.get(
            "warning_message",
            "### The MunkiCatalogBuilder processor has been deprecated. It currently does nothing. It will be removed in the future. ###",
        )
        self.output(warning_message)
        recipe_name = os.path.basename(self.env["RECIPE_PATH"])
        recipe_name = remove_recipe_extension(recipe_name)
        self.env["deprecation_summary_result"] = {
            "summary_text": "The following recipes have deprecation warnings:",
            "report_fields": ["name", "warning"],
            "data": {"name": recipe_name, "warning": warning_message},
        }


if __name__ == "__main__":
    PROCESSOR = MunkiCatalogBuilder()
    PROCESSOR.execute_shell()
