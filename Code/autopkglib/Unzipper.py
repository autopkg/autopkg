#!/usr/bin/env python
#
# Copyright 2010 Per Olofsson
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
import shutil

from autopkglib import Processor, ProcessorError


__all__ = ["Unzipper"]


class Unzipper(Processor):
    description = "Unzips an archive."
    input_variables = {
        "archive_path": {
            "required": True,
            "description": "Path to a zip archive.",
        },
        "destination_path": {
            "required": True,
            "description": "Directory where archive will be unpacked, created if necessary.",
        },
        "purge_destination": {
            "required": False,
            "description": "Whether the contents of the destination directory will be removed before unpacking.",
        },
    }
    output_variables = {
    }
    
    __doc__ = description
    
    def main(self):
        # Create the directory if needed.
        if not os.path.exists(self.env['destination_path']):
            try:
                os.mkdir(self.env['destination_path'])
            except OSError as e:
                raise ProcessorError("Can't create %s: %s" % (path, e.strerror))
        elif self.env.get('purge_destination'):
            for entry in os.listdir(self.env['destination_path']):
                path = os.path.join(self.env['destination_path'], entry)
                try:
                    if os.path.isdir(path) and not os.path.islink(path):
                        shutil.rmtree(path)
                    else:
                        os.unlink(path)
                except OSError as e:
                    raise ProcessorError("Can't remove %s: %s" % (path, e.strerror))
        
        # Call ditto.
        try:
            p = subprocess.Popen(["/usr/bin/ditto",
                                  "--noqtn",
                                  "-x",
                                  "-k",
                                  self.env['archive_path'],
                                  self.env['destination_path']],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            (out, err) = p.communicate()
        except OSError as e:
            raise ProcessorError("ditto execution failed with error code %d: %s" % (
                                  e.errno, e.strerror))
        if p.returncode != 0:
            raise ProcessorError("unzipping %s with ditto failed: %s" % (self.env['archive_path'], err))
        
        self.output("Unzipped %s to %s" 
                    % (self.env['archive_path'], self.env['destination_path']))

if __name__ == '__main__':
    processor = Unzipper()
    processor.execute_shell()
    
