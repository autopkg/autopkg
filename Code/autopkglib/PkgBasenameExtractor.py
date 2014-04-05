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


__all__ = ["PkgBasenameExtractor"]


class PkgBasenameExtractor(Processor):
    description = ( "Extracts the basename of the package. " )
    input_variables = {
        "pkg_path": {
            "required": True,
            "description": "Path to the package to be signed"
        }
    }
    output_variables = {
        "pkg_basename": {
        	"description": "Base name of the package (without the path)."
        }
   }
    
    __doc__ = description
    
    def main(self):
        self.env[ "pkg_basename" ] = os.path.basename( self.env[ "pkg_path" ] )
        
if __name__ == '__main__':
    processor = PkgBasenameExtractor()
    processor.execute_shell()

