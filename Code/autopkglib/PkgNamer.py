#!/usr/bin/env python

import os
import shutil
import subprocess

from autopkglib import Processor, ProcessorError
from Foundation import NSData, NSPropertyListSerialization, NSPropertyListMutableContainers

__all__ = ["PkgNamer"]

class PkgNamer(Processor):

    description = "Extracts version and name information"

    input_variables = {
        "app_bundle_path": {
            "required": False,
            "description": "Path to a .app bundle",
        },
        "pkg_info_bundle_path": {
            "required": False,
            "description": "Path to a Info.plist inside a .pkg",
        }
    }
    output_variables = {
    	"pkg_long_name": {
    		"description": "Long name for package."
    	},
    	"pkg_version_string": {
    		"description": "Version string for package."
    	},
    	"pkg_creation_date": {
    	    "description": "Compressed date for package"
    	}
    }

    __doc__ = description

    # Dig through a .app bundle, get name, version, date
    def run_app(self):
        
        plistpath = os.path.join( self.env["app_bundle_path"], "Contents", "Info.plist")
        info, format, error = \
            NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(
                NSData.dataWithContentsOfFile_(plistpath),
                NSPropertyListMutableContainers,
                None,
                None
            )
        if error:
            raise ProcessorError("Can't read %s: %s" % (plistpath, error))
        
        # got the plist in memory
        # pkg_long_name - title case, then trim any spaces out of name
        self.env["pkg_long_name"] = "".join( info["CFBundleName"].title().split )
        # pkg_version_string - trim out any spaces
        self.env["pkg_version_string"] = info["CFBundleShortVersionString"].replace( ' ', '' )
        # pkg_creation_date - YYYYMMDD
        self.env["pkg_creation_date"] = date.today().strftime( "%Y%m%d" )

        print self.env

    # Dig through a .pkg bundle, get name, version, date
    def run_pkg(self):
        
        info, format, error = \
            NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(
                NSData.dataWithContentsOfFile_(self.env["pkg_info_bundle_path"]),
                NSPropertyListMutableContainers,
                None,
                None
            )
        if error:
            raise ProcessorError("Can't read %s: %s" % (self.env["pkg_info_bundle_path"], error))
        
        # got the plist in memory
        # pkg_long_name - title case, then trim any spaces out of name
        self.env["pkg_long_name"] = "".join( info["CFBundleName"].title().split )
        # pkg_version_string - trim out any spaces
        self.env["pkg_version_string"] = info["CFBundleShortVersionString"].replace( ' ', '' )
        # pkg_creation_date - YYYYMMDD
        self.env["pkg_creation_date"] = date.today().strftime( "%Y%m%d" )
        
        print self.env

    # Determines which of the two (.app/.pkg) will be used to create the name
    def main(self):
        if app_bundle_path is not None:
            self.run_app()
        elif pkg_info_bundle_path is not None:
            self.run_pkg()
        else:
            raise ProcessorError("Must have one of app path or Info.plist path")
        

if __name__ == '__main__':
    processor = PkgNamer()
    processor.execute_shell()
    