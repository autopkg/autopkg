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


import FoundationPlist
import subprocess
import os
import datetime

from datetime import date
from autopkglib import Processor, ProcessorError


__all__ = ["DateTimeTagger"]


class DateTimeTagger(Processor):
    description = ( "Tags a package (or other file) with today's date." )
    input_variables = {
        "file_path": {
            "required": False,
            "description": ("(Optional) Path to the file to be tagged. Defaults to pkg_path if not present. ",
            				"If not present, then pkg_path is updated to the new name of the package file." )
        },
        "date_format": {
            "required": False,
            "description": "(Optional) Custom format string for date."
        }
    }
    output_variables = {
	}
	    
    __doc__ = description
    
    
    def rename_file(self, file_path):
    
        # split file_path to manipulate name
        file_dir = os.path.dirname( file_path )
        file_base_name = os.path.basename( file_path )
        ( file_name_no_extension, file_extension ) = os.path.splitext( file_base_name )
        
        # check for custom format string
        if "date_format" in self.env:
        	date_format = self.env[ "date_format" ]
        else:
        	date_format = "-%Y%m%d"
        
        extended_path = os.path.join( pkg_dir, pkg_name_no_extension + \
        	datetime.now().strftime( date_format ) + pkg_extension )

        rename( file_path, extended_path )
        
        return extended_path
    	
    
    def main(self):
    
    	# determine file path from self.env or pkg_path
    	if "file_path" in self.env:
    		self.rename_file( self.env[ "file_path" ] )
    	else:
    		updated_pkg_path = self.rename_file( self.env[ "pkg_path" ] )
    		self.env[ "pkg_path" ] = updated_pkg_path
    	

if __name__ == '__main__':
    processor = DateTimeTagger()
    processor.execute_shell()
    
