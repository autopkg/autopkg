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


import sys
import re
import plistlib
import subprocess


__all__ = [
    "Processor",
    "ProcessorError"
]


re_keyref = re.compile(r'%(?P<key>[a-zA-Z_][a-zA-Z_0-9]*)%')


class ProcessorError(Exception):
    pass

class Processor(object):
    """Processor base class.
    
    Processors accept a property list as input, process its contents, and
    returns a new or updated property list that can be processed further.
    """
    
    def __init__(self, env=None, infile=None, outfile=None):
        super(Processor, self).__init__()
        self.env = env
        if infile is None:
            self.infile = sys.stdin
        else:
            self.infile = infile
        if outfile is None:
            self.outfile = sys.stdout
        else:
            self.outfile = outfile
    
    def main(self):
        raise ProcessorError("Abstract method main() not implemented.")
    
    def get_manifest(self):
        try:
            return (self.description,
                    self.input_variables,
                    self.output_variables)
        except AttributeError as e:
            raise ProcessorError("Missing manifest: %s" % e)
    
    def read_input_plist(self):
        """Read environment from input plist."""
        
        try:
            indata = self.infile.read()
            if indata:
                self.env = plistlib.readPlistFromString(indata)
            else:
                self.env = dict()
        except BaseException as e:
            raise ProcessorError(e)
    
    def write_output_plist(self):
        """Write environment to output as plist."""
        
        if self.env is None:
            return
        
        try:
            plistlib.writePlist(self.env, self.outfile)
        except BaseException as e:
            raise ProcessorError(e)
    
    def update_data(self, key, value):
        """Update environment keys with value. Existing data can be referenced
        by wrapping the key in %percent% signs."""
        
        def getdata(m):
            return self.env[m.group("key")]
            
        def do_variable_substitution(item):
            """Do variable substitution for item"""
            if isinstance(item, str):
                item = re_keyref.sub(getdata, item)
            elif isinstance(item, list):
                for index in range(len(item)):
                    item[index] = do_variable_substitution(item[index])
            elif isinstance(item, dict):
                for key, value in item.iteritems():
                    item[key] = do_variable_substitution(value)
            return item
        
        self.env[key] = do_variable_substitution(value)
    
    def parse_arguments(self):
        """Parse arguments as key='value'."""
        
        for arg in sys.argv[1:]:
            (key, sep, value) = arg.partition("=")
            if sep != "=":
                raise ProcessorError("Illegal argument '%s'" % arg)
            self.update_data(key, value)
            
    def inject(self, arguments):
        # Update data with arguments.
        for key, value in arguments.items():
            self.update_data(key, value)
        
    def process(self):
        """Main processing loop."""
        
        # Make sure all required arguments have been supplied.
        for variable, flags in self.input_variables.items():
            if flags["required"] and (variable not in self.env):
                raise ProcessorError(
                    "%s requires %s" % (self.__name__, variable))
        
        self.main()
        return self.env
    
    def cmdexec(self, command, description):
        """Execute a command and return output."""
        
        try:
            p = subprocess.Popen(command,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            (out, err) = p.communicate()
        except OSError as e:
            raise ProcessorError(
                "%s execution failed with error code %d: %s" 
                % (command[0], e.errno, e.strerror))
        if p.returncode != 0:
            raise ProcessorError("%s failed: %s" % (description, err))
        
        return out
    
    def execute_shell(self):
        """Execute as a standalone binary on the commandline."""
        
        try:
            self.read_input_plist()
            self.parse_arguments()
            self.main()
            self.write_output_plist()
        except ProcessorError as e:
            print >> sys.stderr, "ProcessorError: %s" % e
            sys.exit(10)
        else:
            sys.exit(0)
        

