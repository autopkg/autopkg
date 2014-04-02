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


import subprocess

from autopkglib import Processor, ProcessorError

__all__ = ["SshCommandRunner"]


class SshCommandRunner(Processor):
    description = ( "Executes a remote command via ssh. "
                    "NOTE: authentication MUST be via key pair." )
    
    input_variables = {
        "dest_server": {
            "required": True,
            "description": "Hostname for destination server",
        },
        "dest_username": {
            "required": False,
            "description": "(Optional) username to use for upload"
        },
        "dest_port": {
            "required": False,
            "description": "(Optional) alternative TCP port to use on destination server"
        },
        "remote_command": {
        	"required": True,
        	"description": "Command to be executed on the remote system"
        }
    }
    output_variables = {

    }

    __doc__ = description
                

    def main(self):
        command_line_list = [ "/usr/bin/ssh" ]
        
        if "dest_port" in self.env:
            command_line_list.append( "-p" )
            command_line_list.append( self.env[ "dest_port" ] )
        
        if "dest_username" in self.env:
            username_arg = self.env[ "dest_username" ] + "@"
        command_line_list.append( username_arg + self.env[ "dest_server" ] )
        
        command_line_list.append( self.env[ "remote_command" ] )
        
        # print command_line_list
        subprocess.call( command_line_list )

            
        
if __name__ == "__main__":
    processor = ScpUploader()
    processor.execute_shell()
