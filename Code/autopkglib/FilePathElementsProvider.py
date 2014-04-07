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

from autopkglib import Processor, ProcessorError


__all__ = ["FilePathElementsProvider"]


class FilePathElementsProvider(Processor):
    description = ( "Extracts file path elements of given path. For example, if the input_path is ",
    				"/Users/ladmin/Library/AutoPkg/Cache/com.github.ladmin-recipes.pkg.Foobar/downloads/Foobar-3.1.dmg," 
    				"then the results will be: ",
    				"dirname = /Users/ladmin/Library/AutoPkg/Cache/com.github.ladmin-recipes.pkg.Foobar/downloads", 
    				"basename = Foobar-3.1.dmg", 
    				"basename_no_ext = Foobar-3.1", 
    				"extension = .dmg" )
    input_variables = {
        "input_path": {
            "required": False,
            "description": ("Path to be sliced up. ", 
            				"Defaults to pkg_path, or if pkg_path is not defined, pathname. " )
        },
        "result_prefix": {
        	"required": False,
        	"description": ("Prefix to output variable names. If you want to have the output",
        					"variable names differentiated from other splits. E.g., if ",
        					"result_prefix = foo, then the output variables will be ",
        					"foo_dirname, foo_basename, foo_basename_no_ext, foo_extension. " )
        }
    }
    output_variables = {
        "dirname": {
        	"description": "path up to and including the containing directory."
        },
        "basename": {
        	"description": "Base name of the target file/folder (without the path)."
        },
        "basename_no_ext": {
        	"description": "Base name of the target without the filename extension."
        },
        "extension": {
        	"description": "Filename extension of the target."
        }
   }
    
    __doc__ = description
    
    def main(self):
    	
    	# determine whether we need to pull in input_path, pkg_path, or pathname
    	if "input_path" in self.env:
    		input_path = self.env[ "input_path" ]
    	elif "pkg_path" in self.env:
    		input_path = self.env[ "pkg_path" ]
    	elif "pathname" in self.env:
    		input_path = self.env[ "pathname" ]
    	else:
    		raise KeyError( "FilePathElementsProvider: input_path, pkg_path, and pathname all not found" )
    	
    	# we have the path, now do the split
    	dirname = os.path.dirname( input_path)
        basename = os.path.basename( input_path )
        (basename_no_ext, extension) = os.path.splitext( basename )
        
        # check to see if we need to prefix the output
        if "result_prefix" in self.env:
        	prefix = self.env[ "result_prefix" ] + "_"
        else:
        	prefix = ""
        
        # put results into self.env
        self.env[ prefix + "dirname" ] = dirname
        self.env[ prefix + "basename" ] = basename
        self.env[ prefix + "basename_no_ext" ] = basename_no_ext
        self.env[ prefix + "extension" ] = extension
        
if __name__ == '__main__':
    processor = FilePathElementsProvider()
    processor.execute_shell()

