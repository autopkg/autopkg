#!/usr/bin/python
#
# Copyright 2016 University of Oxford
# Based on PkgExtractor.py, Copyright 2013 Greg Neagle
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

"""See docstring for XipArchiveExpander class"""

import os
import FoundationPlist
import shutil
import tempfile

from autopkglib.DmgMounter import DmgMounter
from autopkglib import Processor,ProcessorError

__all__ = ["XipArchiveExpander"]

class XipArchiveExpander(Processor):
    """Expands an Xip Archive (a signed archive for secure distribution) to pkgroot."""
    description = __doc__
    input_variables = {
        "xip_path": {
            "required": True,
            "description":
                "Path to a xip file.",
        },
        "extract_root": {
            "required": True,
            "description":
                "Path to where the contents will be extracted.",
        },
    }
    output_variables = {
    }

    def extract_xip_payload(self, xip_path, extract_root):
        '''Extract xip package contents to extract_root, preserving intended
         directory structure'''
        # Experimentation (by Greg N) suggests that an xip file is
        # an xar file with gzip'd contents containing the application
        # data as a cpio archive and a signature in the table of contents.
        # 
        # We assume the signature has already been checked, and look 
        # to extract the xar file, and then use ditto to deal with
        # gzip'd cpio archive
        # 

        # Step 1: Extract xar archive to temporary path (within extract_root)
        try:
            xar_extracted_path = tempfile.mkdtemp(dir=extract_root)
        except (OSError, IOError), err:
            raise ProcessorError("Failed to create temporary xar directory: %s" % err)

        xar_extract_cmd = [ '/usr/bin/xar',
                             '-x', 
                             '-f', xip_path,
                             '-C', xar_extracted_path
                          ]
        try:
            # cmdexec will raise errors on failure
            self.cmdexec(xar_extract_cmd,
                         'Extract xip file %s' % xip_path) 
        except Exception as err:
            self.cleanup_dir(xar_extracted_path, ignore_errors = True)
            raise(err)

        # This should give us two files: Metadata and Content:
        xar_metadata_file = os.path.join(xar_extracted_path, 'Metadata')
        xar_content_file = os.path.join(xar_extracted_path, 'Content')

        if not os.path.exists(xar_metadata_file):
            self.cleanup_dir(xar_extracted_path, ignore_errors = True)
            raise ProcessorError("Metadata file missing from .xip file")

        if not os.path.exists(xar_content_file):
            self.cleanup_dir(xar_extracted_path, ignore_errors = True)
            raise ProcessorError("Content file missing from .xip file")

        # We can now expand the Contents payload using ditto
        # (which helpfully gunzips + extracts the cpio file)
        xar_extract_cmd = [ '/usr/bin/ditto',
                             '-x', 
                             xar_content_file,
                             extract_root,
                          ]

        try:
            # Will raise errors on failure
            self.cmdexec(xar_extract_cmd,
                          'Extract Contents of xip file %s' % xar_content_file ) 
        except Exception as err:
            self.cleanup_dir(extract_root, ignore_errors = True) # Clean up
            raise(err)

        # Clean up temporary files
        self.cleanup_dir(xar_extracted_path) # will raise error

    def cleanup_dir(self, directory, ignore_errors = False):
        '''Utility function to remove directroy contents, and report errors (or not) as the caller desires'''
        try:
            shutil.rmtree(directory, ignore_errors=ignore_errors)
        except (OSError, IOError), err:
            raise ProcessorError("Failed to remove %s: %s"
                                                % (directory,err) )
    def main(self):
        """Exand a XIP archive"""

        # Check input is as we would like
        xip_path = self.env.get('xip_path')
        if not xip_path.endswith('xip'): 
            raise ProcessorError('Expected xip archive with name ending .xip, got %s (not ending .xip)' % xip_path)

        if not os.path.exists(xip_path):
            raise ProcessorError('Input file %s not found' % xip_path)

        extract_root = self.env.get('extract_root')
        # Clean up any old content if this already exists
        if os.path.exists(extract_root):
            self.cleanup_dir( extract_root ) # rasise error

        # Create the required directories
        try:
            os.makedirs(extract_root, 0755)
        except (OSError, IOError), err:
            raise ProcessorError("Failed to create extract_root: %s" % err)

        # Extract the payload
        self.extract_xip_payload(xip_path, extract_root)

if __name__ == '__main__':
    PROCESSOR = XipArchiveExpander()
    PROCESSOR.execute_shell()
