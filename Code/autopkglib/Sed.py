#!/usr/bin/env python
#
# Copyright 2014 Yoann Gini
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

import os
import time

from autopkglib import Processor, ProcessorError
from tempfile import NamedTemporaryFile

__all__ = ["Sed"]


class Sed(Processor):
    description = "Run sed command on target_file (with backup option enabled)."
    input_variables = {
        "target_file": {
            "required": True,
            "description": ("Execute sed commands against this file."),
        },
        "sed_commands": {
            "required": True,
            "description": "An array of sed commands to be executed.",
        },
        
        "sed_debug": {
            "required": False,
            "description": "Set to true if you want to keep the temporary sed file created during the process, for debug purpose. False by default.",
        },
    }
    output_variables = {
    }
    
    __doc__ = description
    
    def main(self):
        sed_debug = self.env.get('sed_debug', False)
        target_file = self.env['target_file']
        sed_commands = self.env['sed_commands']
        if not target_file:
            raise ProcessorError("Expected an 'target_file' input variable but none is set!")
        if not os.path.exists(target_file):
            raise ProcessorError("The target file don't exist! (%s)" % target_file)
        if not sed_commands:
            raise ProcessorError("Expected instruction from 'sed_commands' input variable but none is set!")
        tmp_sed_commands_file = NamedTemporaryFile(delete=not sed_debug)
        if sed_debug:
            self.output("[DEBUG] Sed file is %s" % tmp_sed_commands_file.name)
        for command in sed_commands:
            tmp_sed_commands_file.write(command)
            tmp_sed_commands_file.write('\n')
        tmp_sed_commands_file.flush()
        os.system("sed -f %s -i .%s %s" % (tmp_sed_commands_file.name, time.time(), target_file))
        tmp_sed_commands_file.close()
        self.output("Editing done %s" % target_file)

if __name__ == '__main__':
    processor = Sed()
    processor.execute_shell()
    
