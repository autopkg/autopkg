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


import os.path
import subprocess
import FoundationPlist
import math
from xml.etree.ElementTree import ElementTree 
from xml.etree.ElementTree import Element

from autopkglib import Processor, ProcessorError


__all__ = ["PkgInfoTemplateCreator"]


class PkgInfoTemplateCreator(Processor):
    description = "Creates a PackageInfo template file."
    input_variables = {
    	"template_values": {
    		"required": True,
    		"description": ("Dictionary of tags and attributes to be inserted into the template",
    						"Example:",
    						"<dict>",
    						"    <key>top_element_attributes</key>",
    						"    <dict>",
    						"        <key>format-version</key>",
    						"        <string>2</string>",
    						"        <key>install-location</key>",
    						"        <string>/</string>",
    						"        <key>auth</key>",
    						"        <string>root</string>",
    						"    </dict>",
    						"</dict>",
    						"For not, only top attributes are implemented. Support for child elements",
    						"will be added later on." )
    	},
    	"template_path": {
    		"required": False,
    		"description": ("Path to write PackageInfo template. Defaults to",
    						"%RECIPE_CACHE_DIR%/PackageInfoTemplate" )
    	}
    }
    output_variables = {
        "template_path": {
            "description": "An Info.plist template."
        }
    }
    
    __doc__ = description
    
    def template_path(self):
    	# check for input var
    	if "template_path" not in self.env:
    		# set default path
    		self.env[ "template_path" ] = self.env[ "RECIPE_CACHE_DIR" ] + "/PackageInfoTemplate"
    	
		return self.env[ "template_path" ]

    def main(self):
    
    	# separate out top element attributes dict from input var
    	top_element_attrs_dict = self.env[ "template_values" ]["top_element_attributes"]
    	
    	# create XML
    	top_element = Element( "pkg-info", top_element_attrs_dict )
    	tree = ElementTree( top_element )
    	
    	# write out to file
    	output_path = self.template_path()
    	tree.write( output_path )
    

if __name__ == '__main__':
    processor = PkgInfoTemplateCreator()
    processor.execute_shell()
	