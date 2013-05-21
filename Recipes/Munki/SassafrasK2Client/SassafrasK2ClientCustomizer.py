#!/usr/bin/env python
#
# Copyright 2013 Tim Sutton
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
import subprocess

from autopkglib import Processor, ProcessorError


__all__ = ["SassafrasK2ClientCustomizer"]

CONFIG_SCRIPT_PATH = 'Contents/Resources/k2clientconfig'

class SassafrasK2ClientCustomizer(Processor):
    description = ("Provides URL to the latest bundle-style K2Client package "
                   "designed for customization.")
    input_variables = {
        "base_mpkg_path": {
            "required": True,
            "description": "Path to the root of an mpkg-bundle K2Client-Config package. "
                           "Path must be writable."
        },
        "k2clientconfig_options": {
            "required": True,
            "description": "Array of command arguments to be passed to k2clientconfig."
        }
    }
    output_variables = {
    }

    __doc__ = description

    def main(self):
        script = os.path.join(self.env["base_mpkg_path"],
                              "Contents/Resources/k2clientconfig")
        cmd = [script] + [n for n in self.env["k2clientconfig_options"].split()]
        p = subprocess.Popen(cmd,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        out, err = p.communicate()
        if err:
            raise ProcessorError("k2clientconfig returned errors:\n%s" % err)


if __name__ == "__main__":
    processor = SassafrasK2ClientCustomizer()
    processor.execute_shell()
