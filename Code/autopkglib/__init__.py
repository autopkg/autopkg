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
import sys

import imp
import plistlib
import pprint
import re
import subprocess


BUNDLE_ID = "com.googlecode.autopkg"
LOCAL_OVERRIDE_KEY = "RecipeInputOverrides"

# Processor base class definition
re_keyref = re.compile(r'%(?P<key>[a-zA-Z_][a-zA-Z_0-9]*)%')

class ProcessorError(Exception):
    pass

class Processor(object):
    """Processor base class.
    
    Processors accept a property list as input, process its contents, and
    returns a new or updated property list that can be processed further.
    """
    
    def __init__(self, env=None, infile=None, outfile=None):
        #super(Processor, self).__init__()
        self.env = env
        if infile is None:
            self.infile = sys.stdin
        else:
            self.infile = infile
        if outfile is None:
            self.outfile = sys.stdout
        else:
            self.outfile = outfile
            
    def output(self, msg, verbose_level=1):
        if self.env.get('verbose', 0) >= verbose_level:
            print "%s: %s" % (self.__class__.__name__, msg)
    
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

# AutoPackager class defintion

class AutoPackagerError(Exception):
    pass

class AutoPackager(object):
    """Instantiate and execute processors from a recipe."""

    def __init__(self, options, env):
        self.verbose = options.verbose
        self.env = env
        self.results = []

    def output(msg, verbose_level=1):
        if self.verbose >= verbose_level:
            print msg

    def get_recipe_identifier(self, recipe):
        """Return the identifier given an input recipe plist."""
        identifier = recipe["Input"].get("IDENTIFIER")
        if not identifier:
            print "ID NOT FOUND"
            # build a pseudo-identifier based on the recipe pathname
            recipe_path = self.env.get("RECIPE_PATH")
            # get rid of filename extension
            recipe_path = os.path.splitext(recipe_path)[0]
            path_parts = recipe_path.split("/")
            identifier = "-".join(path_parts)
        return identifier

    def process_input_overrides(self, recipe, cli_values):
        """Update env with 'composited' input values from overrides:
        1. Start with items in recipe's 'Input' dict
        2. Merge and overwrite any keys defined in app plist:
        <key>RecipeInputOverrides</key>
        <dict>
            <key>com.googlecode.autopkg.some_app</key>
            <dict>
                <key>MUNKI_CATALOG</key>
                <string>my_custom_catalog</string>
        3. Merge and overwrite any key-value pairs appended to the
        autopkg command invocation, of the form: NAME=value

        (3) takes precedence over (2), which takes precedence over (1)
        """

        # Set up empty container for final output
        inputs = {}
        inputs.update(recipe["Input"])
        identifier = self.get_recipe_identifier(recipe)
        if self.env.get(LOCAL_OVERRIDE_KEY):
            recipe_overrides = self.env.get(LOCAL_OVERRIDE_KEY).get(identifier)
            if recipe_overrides:
                if not hasattr(recipe_overrides, "has_key"):
                    raise AutoPackagerError(
                        "Local recipe values for %s found in %s, "
                        "but is of type %s, when it should "
                        "be a dict of variables and values."
                        % (identifier, LOCAL_OVERRIDE_KEY, 
                           recipe_overrides.__class__.__name__))
                inputs.update(recipe_overrides)

        # handle CLI
        inputs.update(cli_values)
        self.env.update(inputs)

    def verify(self, recipe):
        """Verify a recipe and check for errors."""

        # Initialize variable set with input variables.
        variables = set(recipe["Input"].keys())
        # Add environment.
        variables.update(set(self.env.keys()))
        recipe_dir = self.env.get('RECIPE_DIR')
        # Check each step of the process.
        for step in recipe["Process"]:
            # Look for the processor in the same directory as the recipe
            processor_filename = os.path.join(
                                    recipe_dir, step["Processor"] + '.py')
            if os.path.exists(processor_filename):
                try:
                    # attempt to import the module
                    _tmp = imp.load_source(
                        step["Processor"], processor_filename)
                    # look for an attribute with the step Processor name
                    _processor = getattr(_tmp, step["Processor"])
                    # add the processor to autopkglib's namespace
                    add_processor(step["Processor"], _processor)
                except (ImportError, AttributeError):
                    # if we aren't successful, that's OK, we're going
                    # see if the processor was already imported
                    pass
            try:
                processor_class = get_processor(step["Processor"])
            except AttributeError:
                raise AutoPackagerError(
                        "Unknown processor '%s'" % step["Processor"])
            # Add arguments to set of variables.
            variables.update(set(step["Arguments"].keys()))
            # Make sure all required input variables exist.
            for key, flags in processor_class.input_variables.items():
                if flags["required"] and (key not in variables):
                    raise AutoPackagerError("%s requires missing argument %s" 
                                            % (step["Processor"], key))
            # Add output variables to set.
            variables.update(set(processor_class.output_variables.keys()))

    def process(self, recipe):
        """Process a recipe."""
        identifier = self.get_recipe_identifier(recipe)
        # define a cache/work directory for use by the recipe
        cache_dir = self.env.get("CACHE_DIR") or os.path.expanduser(
            "~/Library/AutoPkg/Cache")
        self.env["RECIPE_CACHE_DIR"] = os.path.join(
            cache_dir, identifier)

        recipe_input_dict = {}
        for key in self.env.keys():
            recipe_input_dict[key] = self.env[key]
        self.results.append({"Recipe input": recipe_input_dict})

        # make sure the RECIPE_CACHE_DIR exists, creating it if needed
        if not os.path.exists(self.env["RECIPE_CACHE_DIR"]):
            try:
                os.makedirs(self.env["RECIPE_CACHE_DIR"])
            except OSError, e:
                raise AutoPackagerError(
                    "Could not create RECIPE_CACHE_DIR %s: %s"
                    % (self.env["RECIPE_CACHE_DIR"], e))

        if self.verbose > 2:
            pprint.pprint(self.env)

        for step in recipe["Process"]:

            if self.verbose:
                print step["Processor"]

            processor_class = get_processor(step["Processor"])
            processor = processor_class(self.env)
            processor.inject(step["Arguments"])

            input_dict = {}
            for key in processor.input_variables.keys():
                if key in processor.env:
                    input_dict[key] = processor.env[key]

            if self.verbose > 1:
                # pretty print any defined input variables
                pprint.pprint({"Input": input_dict})

            try:
                self.env = processor.process()
            except ProcessorError as e:
                print >> sys.stderr, str(e)
                raise AutoPackagerError(
                    "Error in %s: Processor: %s: Error: %s"
                    %(identifier, step["Processor"], str(e)))

            output_dict = {}
            for key in processor.output_variables.keys():
                output_dict[key] = self.env[key]
            if self.verbose > 1:
                # pretty print output variables
                pprint.pprint({"Output": output_dict})

            self.results.append({'Processor': step["Processor"],
                                 'Input': input_dict,
                                 'Output': output_dict})

            if self.env.get("stop_processing_recipe"):
                # processing should stop now
                break

        if self.verbose > 2:
            pprint.pprint(self.env)


# get the directory this __init__.py file is in
mydir = os.path.dirname(os.path.abspath(__file__))
mydirname = os.path.basename(mydir)

# find all the .py files (minus this one)
processor_files = [
        os.path.splitext(name)[0] 
        for name in os.listdir(mydir) 
        if name.endswith('.py') and not name == '__init__.py']

# Warning! Fancy dynamic importing ahead!
#
# import the filename as a submodule
# then add the attribute with the same name to the globals()
#
# This is the equivalent of:
#
#    from Bar.Foo import Foo
#
for name in processor_files:
    globals()[name] = getattr(__import__(
        mydirname + '.' + name, fromlist=[name]), name)

# convenience functions for adding and accessing processors
# since these can change dynamically
def add_processor(processor_name, processor_object):
    globals()[processor_name] = processor_object
    
def get_processor(processor_name):
    return globals()[processor_name]
    
