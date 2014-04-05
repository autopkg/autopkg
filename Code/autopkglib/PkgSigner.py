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
        },
        "suffix_with_date": {
            "required": False,
            "description": "(Optional) append a date string yyyymmdd to the file name. Defaults to False"
        }
    }
    output_variables = {
        "pkg_path": {
            "description": "Path to the package signed pacakge."
        },
        "pkg_basename": {
        	"description": "Base name of the signed package (without the path)."
        }
   }
    
    __doc__ = description
    
    def main(self):
    
        # split package_path to manipulate name
        pkg_dir = os.path.dirname( self.env[ "pkg_path" ] )
        pkg_base_name = os.path.basename( self.env[ "pkg_path" ] )
        ( pkg_name_no_extension, pkg_extension ) = os.path.splitext( pkg_base_name )
        
        unsigned_pkg_path = self.env[ "pkg_path" ]
        self.env[ "pkg_path" ] = os.path.join( pkg_dir, pkg_name_no_extension + \
                                    "-signed" + pkg_extension )

        #  if suffix_with_date then tag on the date instead of "-signed"
        if "suffix_with_date" in self.env:
            if self.env[ "suffix_with_date" ]:
                self.env[ "pkg_path" ]  = os.path.join( pkg_dir, pkg_name_no_extension + \
                                    date.today().strftime( "-%Y%m%d" ) + pkg_extension )

                
        command_line_list = [ "/usr/bin/productsign", \
                              "--sign", \
                              self.env[ "signing_cert" ], \
                              unsigned_pkg_path, \
                              self.env[ "pkg_path" ]  ]
                              
        subprocess.call( command_line_list )
#        self.env[ "pkg_basename" ] = pkg_name_no_extension + \
#                                    date.today().strftime( "-%Y%m%d" ) + pkg_extension
            

if __name__ == '__main__':
    processor = PkgSigner()
    processor.execute_shell()
    
