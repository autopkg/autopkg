#!/usr/bin/python
#
# Copyright 2015 Shea G. Craig
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
"""See docstring for OptionSelector class"""

import re
import urllib2

from autopkglib import Processor, ProcessorError

__all__ = ["OptionSelector"]

class OptionSelector(Processor):
    """Selects an option from a dictionary to assign to a variable.

    In most cases, simply using an Input variable to allow overriding an
    argument for a processor is sufficient. This processor allows the
    recipe author to provide a dictionary of values to choose from for
    instances where that value may be more involved than the recipe-user
    should be responsible for. For example, selecting the correct regex
    to supply to a URLTextSearcher later in the recipe chain is not
    as trivial as specifying a Culture Code.
    """

    input_variables = {
        "result_output_var_name": {
            "description": "The name of the output variable that is returned. "
                           "If not specified, a default of 'selection' will "
                           "be used.",
            "required": False,
            "default": "selection",
        },
        "selection": {
            "description": "Key of option to select. The corresponding value "
                           "will be returned as the result_output_var_name's "
                           "value.",
            "required": True,
        },
        "options": {
            "description": "Dictionary of options. Keys are used as values "
                           "for the selection argument. The value is returned "
                           "as the output of this processor.",
            "required": True,
        },
    }
    output_variables = {
        "result_output_var_name": {
            "description": "The value of 'selection' in the 'options'. "
                           "NOTE: The name of this variable is controlled "
                           "by the 'result_output_var_name' variable "
                           "(the default is 'selection')",
        }
    }

    description = __doc__

    def main(self):
        output_name = self.env["result_output_var_name"]
        selection = self.env["selection"]
        options = self.env["options"]
        if selection not in options:
            raise ProcessorError(
                "Specified selection is not in the dictionary!")
        else:
            result = options[selection]

        self.output_variables = {
            output_name: {"description": "Selected option."}}
        self.env[output_name] = result
        self.output("Selection '{}': '{}'".format(selection, result))


if __name__ == "__main__":
    PROCESSOR = OptionSelector()
    PROCESSOR.execute_shell()
