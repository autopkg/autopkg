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

EXTNS = {
    'zip': ['zip'],
    'tar_gzip': ['tar.gz', 'tgz'],
    'tar_bzip2': ['tar.bz2', 'tbz']
}

class Unzipper(Processor):
    description = "Unzips an archive."
    input_variables = {
        "archive_path": {
            "required": True,
            "description": "Path to an archive.",
        },
        "destination_path": {
            "required": True,
            "description": "Directory where archive will be unpacked, created if necessary.",
        },
        "purge_destination": {
            "required": False,
            "description": "Whether the contents of the destination directory will be removed before unpacking.",
        },
        "archive_format": {
            "required": False,
            "description": ("The archive format. Currently supported: 'zip', 'tar_gzip', 'tar_bzip2'. "
                           "If omitted, the format will try to be guessed by the file extension.")
        }
    }
    output_variables = {
    }
    
    __doc__ = description
    
    def get_archive_format(self, archive_path):
        for format, extns in EXTNS.items():
            for extn in extns:
                if archive_path.endswith(extn):
                    return format
        # We found no known archive file extension if we got this far
        return None

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
        
        fmt = self.env.get("archive_format")
        if fmt is None:
            fmt = self.get_archive_format(self.env.get("archive_path"))
            self.output("Guessed archive format '%s' from filename %s" %
                        (fmt, os.path.basename(self.env.get("archive_path"))))
        elif fmt not in EXTNS.keys():
            raise ProcessorError("'%s' is not valid for the 'archive_format' variable. Must be one of %s." %
                                (fmt, ", ".join(EXTNS.keys())))

        if fmt == "zip":
            cmd = ["/usr/bin/ditto",
                   "--noqtn",
                   "-x",
                   "-k",
                   self.env['archive_path'],
                   self.env['destination_path']]
        elif fmt.startswith("tar_"):
            cmd = ["/usr/bin/tar",
                   "-x",
                   "-f",
                   self.env['archive_path'],
                   "-C",
                   self.env['destination_path']]
            if fmt.endswith("gzip"):
                cmd.append("-z")
            elif fmt.endswith("bzip2"):
                cmd.append("-j")

        # Call command.
        try:
            p = subprocess.Popen(cmd,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            (out, err) = p.communicate()
        except OSError as e:
            raise ProcessorError("%s execution failed with error code %d: %s" % (
                                  os.path.basename(cmd[0]), e.errno, e.strerror))
        if p.returncode != 0:
            raise ProcessorError("Unarchiving %s with %s failed: %s" % (
                                  self.env['archive_path'], os.path.basename(cmd[0]), err))
        
        self.output("Unarchived %s to %s" 
                    % (self.env['archive_path'], self.env['destination_path']))

if __name__ == '__main__':
    processor = Unzipper()
    processor.execute_shell()
    
