#!/usr/bin/env python
#
# Copyright 2014 ps Enable, Inc.
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


from subprocess import call

from autopkglib import Processor, ProcessorError

__all__ = ["ScpUploaderProvider"]


class ScpUploaderProvider(Processor):
    description = ( "Uploads a package file to a server via SSH. "
    				"NOTE: authentication MUST be via key pair." )
    
    input_variables = {
        "dest_server": {
            "required": True,
            "description": "Hostname for destination server",
        },
        "dest_path": {
        	"required": True,
        	"description": "Path to target directory on destination server"
        },
        "pkg_path": {
        	"required": True,
        	"description": "Path to the newly created package"
        },
        "dest_username": {
        	"required": False,
        	"description": "(Optional) username to use for upload"
        },
        "dest_port": {
        	"required": False,
        	"description": "(Optional) alternative TCP port to use on destination server"
        }
    }
    output_variables = {

    }

    __doc__ = description
                

    def main(self):
    	command_line_list = [ "/usr/bin/scp" ]
    	
    	if dest_port:
	    	command_line_list.append( "-P" )
	    	command_line_list.append( dest_port )
	    
	    if dest_username:
	    	command_line_list.append( "-l" )
	    	command_line_list.append( dest_username )
	    
	    command_line_list.append( pkg_path )
	    command_line_list.append( dest_server + ":" + dest_path )
	    
	    print command_line_list
#    	subprocess.call( command_line_list )

            
        
if __name__ == "__main__":
    processor = ScpUploaderProvider()
    processor.execute_shell()
