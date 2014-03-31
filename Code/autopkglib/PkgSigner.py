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

from autopkglib import Processor, ProcessorError


__all__ = ["PkgSigner"]


class PkgSigner(Processor):
    description = ( "Signs a package.", 
    				"WARNING: The keychain that contains the signing certificate and key",
    				"MUST be unlocked. Run the productsign command once manually so that",
    				"you can give it access to the correct key so that autopkg can run",
    				"without manual intervention." )
    input_variables = {
        "pkg_path": {
            "required": True,
            "description": "Path to the package to be signed"
        },
        "signing_cert": {
            "required": True,
            "description": "Name of the certificate used to sign the package. Must be an EXACT match. "
        }
    }
    output_variables = {
        "pkg_path": {
             "description": "Path to the package signed pacakge."
        }
   }
    
    __doc__ = description
    
    def main(self):
    
    	# rename unsigned package so that we can slot the signed package into place
        pkg_dir = os.path.dirname( self.env[ "pkg_path" ] )
        pkg_base_name = os.path.basename( self.env[ "pkg_path" ] )
        ( pkg_name_no_extension, pkg_extension ) = os.path.splitext( pkg_base_name )
        
        unsigned_pkg_path = os.path.join( pkg_dir, pkg_name_no_extension + "-unsigned" + pkg_extension )
        os.rename( self.env[ "pkg_path" ], unsigned_pkg_path )
                
        command_line_list = [ "/usr/bin/productsign", \
                              "--sign", \
                              self.env[ "signing_cert" ], \
                              unsigned_pkg_path, \
                              self.env[ "pkg_path" ] ]
                              
        print command_line_list

        # print command_line_list
        subprocess.call( command_line_list )

        
            

if __name__ == '__main__':
    processor = PkgSigner()
    processor.execute_shell()
    
