#!/usr/bin/python
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
import FoundationPlist
import pprint
import re
import subprocess

from Foundation import NSArray, NSDictionary
from CoreFoundation import CFPreferencesAppSynchronize, \
                           CFPreferencesCopyAppValue, \
                           CFPreferencesCopyKeyList, \
                           CFPreferencesSetAppValue, \
                           kCFPreferencesAnyHost, \
                           kCFPreferencesAnyUser, \
                           kCFPreferencesCurrentUser, \
                           kCFPreferencesCurrentHost

from distutils.version import LooseVersion

BUNDLE_ID = "com.github.autopkg"

re_keyref = re.compile(r'%(?P<key>[a-zA-Z_][a-zA-Z_0-9]*)%')

class PreferenceError(Exception):
    """Preference exception"""
    pass


def get_pref(key, domain=BUNDLE_ID):
    """Return a single pref value (or None) for a domain."""
    value = CFPreferencesCopyAppValue(key, domain) or None
    # Casting NSArrays and NSDictionaries to native Python types.
    # This a workaround for 10.6, where PyObjC doesn't seem to
    # support as many common operations such as list concatenation
    # between Python and ObjC objects.
    if isinstance(value, NSArray):
        value = list(value)
    elif isinstance(value, NSDictionary):
        value = dict(value)
    return value


def set_pref(key, value, domain=BUNDLE_ID):
    """Sets a preference for domain"""
    try:
        CFPreferencesSetAppValue(key, value, domain)
        if not CFPreferencesAppSynchronize(domain):
            raise PreferenceError(
                "Could not synchronize %s preference: %s" % key)
    except Exception, err:
        raise PreferenceError(
            "Could not set %s preference: %s" % (key, err))


def get_all_prefs(domain=BUNDLE_ID):
    """Return a dict (or an empty dict) with the contents of all
    preferences in the domain."""
    prefs = {}
    
    # get keys stored via 'defaults write [domain]'
    user_keylist = CFPreferencesCopyKeyList(
        BUNDLE_ID, kCFPreferencesCurrentUser, kCFPreferencesAnyHost)

    # get keys stored via 'defaults write /Library/Preferences/[domain]'
    system_keylist = CFPreferencesCopyKeyList(
        BUNDLE_ID, kCFPreferencesAnyUser, kCFPreferencesCurrentHost)

    # CFPreferencesCopyAppValue() in get_pref() will handle returning the appropriate
    # value using the search order, so merging prefs in order here isn't be necessary
    for keylist in [system_keylist, user_keylist]:
        if keylist:
            for key in keylist:
                prefs[key] = get_pref(key, domain)
    return prefs
    
    
def get_autopkg_version():
    try:
        version_plist = FoundationPlist.readPlist(
            os.path.join(os.path.dirname(__file__), "version.plist"))
    except FoundationPlist.FoundationPlistException:
        return "UNKNOWN"
    try:
        return version_plist["Version"]
    except (AttributeError, TypeError):
        return "UNKNOWN"


def version_equal_or_greater(a, b):
    return LooseVersion(a) >= LooseVersion(b)


def update_data(a_dict, key, value):
    """Update a_dict keys with value. Existing data can be referenced
    by wrapping the key in %percent% signs."""
    
    def getdata(m):
        return a_dict[m.group("key")]
        
    def do_variable_substitution(item):
        """Do variable substitution for item"""
        if isinstance(item, basestring):
            try:
                item = re_keyref.sub(getdata, item)
            except KeyError, err:
                print >> sys.stderr, (
                    "Use of undefined key in variable substitution: %s"
                    % err)
        elif isinstance(item, (list, NSArray)):
            for index in range(len(item)):
                item[index] = do_variable_substitution(item[index])
        elif isinstance(item, (dict, NSDictionary)):
            # Modify a copy of the orginal
            if isinstance(item, dict):
                item_copy = item.copy()
            else:
                # Need to specify the copy is mutable for NSDictionary
                item_copy = item.mutableCopy()
            for key, value in item.items():
                item_copy[key] = do_variable_substitution(value)
            return item_copy
        return item
    
    a_dict[key] = do_variable_substitution(value)

# Processor and ProcessorError base class definitions

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
                self.env = FoundationPlist.readPlistFromString(indata)
            else:
                self.env = dict()
        except BaseException as e:
            raise ProcessorError(e)
    
    def write_output_plist(self):
        """Write environment to output as plist."""
        
        if self.env is None:
            return
        
        try:
            FoundationPlist.writePlist(self.env, self.outfile)
        except BaseException as e:
            raise ProcessorError(e)
    
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
            update_data(self.env, key, value)
        
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
        self.env["AUTOPKG_VERSION"] = get_autopkg_version()
        
    def output(self, msg, verbose_level=1):
        if self.verbose >= verbose_level:
            print msg

    def get_recipe_identifier(self, recipe):
        """Return the identifier given an input recipe plist."""
        identifier = (recipe.get("Identifier") or
                      recipe["Input"].get("IDENTIFIER"))
        if not identifier:
            print "ID NOT FOUND"
            # build a pseudo-identifier based on the recipe pathname
            recipe_path = self.env.get("RECIPE_PATH")
            # get rid of filename extension
            recipe_path = os.path.splitext(recipe_path)[0]
            path_parts = recipe_path.split("/")
            identifier = "-".join(path_parts)
        return identifier

    def process_cli_overrides(self, recipe, cli_values):
        """Override env with input values from the CLI:
        Start with items in recipe's 'Input' dict, merge and
        overwrite any key-value pairs appended to the
        autopkg command invocation, of the form: NAME=value
        """

        # Set up empty container for final output
        inputs = {}
        inputs.update(recipe["Input"])
        inputs.update(cli_values)
        self.env.update(inputs)
        # do any internal string substitutions
        for key, value in self.env.items():
            update_data(self.env, key, value)

    def verify(self, recipe):
        """Verify a recipe and check for errors."""

        # Check for MinimumAutopkgVersion
        if "MinimumVersion" in recipe.keys():
            if not version_equal_or_greater(self.env["AUTOPKG_VERSION"],
                recipe.get("MinimumVersion")):
                raise AutoPackagerError(
                        "Recipe (or a parent recipe) requires at least version %s, "
                        "but we are version %s."
                        % (recipe.get("MinimumVersion"),
                           self.env["AUTOPKG_VERSION"]))

        # Initialize variable set with input variables.
        variables = set(recipe["Input"].keys())
        # Add environment.
        variables.update(set(self.env.keys()))
        # Check each step of the process.
        for step in recipe["Process"]:
            try:
                processor_class = get_processor(
                                      step["Processor"],
                                      recipe=recipe,
                                      env=self.env)
            except (KeyError, AttributeError):
                msg = "Unknown processor '%s'." % step["Processor"]
                if "SharedProcessorRepoURL" in step:
                    msg += (" This shared processor can be added via the "
                            "repo: %s." % step["SharedProcessorRepoURL"])
                raise AutoPackagerError(msg)
            # Add arguments to set of variables.
            variables.update(set(step.get("Arguments", dict()).keys()))
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
            processor.inject(step.get("Arguments", dict()))

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
                print >> sys.stderr, unicode(e)
                raise AutoPackagerError(
                    "Error in %s: Processor: %s: Error: %s"
                    %(identifier, step["Processor"], unicode(e)))

            output_dict = {}
            for key in processor.output_variables.keys():
                # Safety workaround for Processors that may output differently-named
                # output variables than are given in their output_variables
                # TODO: develop a generic solution for processors that can
                #       dynamically set their output_variables
                if processor.env.get(key):
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


_processor_names = []
def import_processors():
    '''Imports processors from the directory this init file is in'''
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
        _processor_names.append(name)


# convenience functions for adding and accessing processors
# since these can change dynamically
def add_processor(name, processor_object):
    '''Adds a Processor to the autopkglib namespace'''
    globals()[name] = processor_object
    if not name in _processor_names:
        _processor_names.append(name)


def get_processor(processor_name, recipe=None, env={}):
    '''Returns a Processor object given a name and optionally a recipe, 
    importing a processor from the recipe directory if available'''
    if recipe:
        recipe_dir = os.path.dirname(recipe['RECIPE_PATH'])
        processor_search_dirs = []

        # look for any shared processors in the search dirs, by checking
        # for a "SharedProcessors" dir at the roots
        for r in env["RECIPE_SEARCH_DIRS"]:
            repo_shared_proc_dir = os.path.join(r, "SharedProcessors")
            if os.path.isdir(repo_shared_proc_dir):
                processor_search_dirs.append(repo_shared_proc_dir)

        # search recipe dirs for processor
        processor_search_dirs.append(recipe_dir)
        if recipe.get("PARENT_RECIPES"):
            # also look in the directories containing the parent recipes
            parent_recipe_dirs = list(set([
                os.path.dirname(item) 
                for item in recipe["PARENT_RECIPES"]]))
            processor_search_dirs.extend(parent_recipe_dirs)

        for directory in processor_search_dirs:
            processor_filename = os.path.join(
                                    directory, processor_name + '.py')
            if os.path.exists(processor_filename):
                try:
                    # attempt to import the module
                    _tmp = imp.load_source(
                        processor_name, processor_filename)
                    # look for an attribute with the step Processor name
                    _processor = getattr(_tmp, processor_name)
                    # add the processor to autopkglib's namespace
                    add_processor(processor_name, _processor)
                    # we've added a Processor, so stop searching
                    break
                except (ImportError, AttributeError), err:
                    # if we aren't successful, that might be OK, we're going
                    # see if the processor was already imported
                    print >> sys.stderr, (
                        "WARNING: %s: %s" % (processor_filename, err))

    return globals()[processor_name]


def processor_names():
    return _processor_names


# when importing autopkglib, need to also import all the processors 
# in this same directory
import_processors()
