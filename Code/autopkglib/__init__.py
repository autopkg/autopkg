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

"""Core/shared autopkglib functions"""

import os
import sys
import imp
import FoundationPlist
import pprint
import re
import subprocess
import glob

#pylint: disable=no-name-in-module
try:
    from Foundation import NSArray, NSDictionary
    from CoreFoundation import CFPreferencesAppSynchronize, \
                               CFPreferencesCopyAppValue, \
                               CFPreferencesCopyKeyList, \
                               CFPreferencesSetAppValue, \
                               kCFPreferencesAnyHost, \
                               kCFPreferencesAnyUser, \
                               kCFPreferencesCurrentUser, \
                               kCFPreferencesCurrentHost
except:
    print "WARNING: Failed 'from Foundation import NSArray, NSDictionary' in " + __name__
    print "WARNING: Failed 'from CoreFoundation import CFPreferencesAppSynchronize, ...' in " + __name__
#pylint: enable=no-name-in-module

from distutils.version import LooseVersion

BUNDLE_ID = "com.github.autopkg"

RE_KEYREF = re.compile(r'%(?P<key>[a-zA-Z_][a-zA-Z_0-9]*)%')

class PreferenceError(Exception):
    """Preference exception"""
    pass


def get_pref(key, domain=BUNDLE_ID):
    """Return a single pref value (or None) for a domain."""
    value = CFPreferencesCopyAppValue(key, domain)
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

    # CFPreferencesCopyAppValue() in get_pref() will handle returning the
    # appropriate value using the search order, so merging prefs in order
    # here isn't necessary
    for keylist in [system_keylist, user_keylist]:
        if keylist:
            for key in keylist:
                prefs[key] = get_pref(key, domain)
    return prefs


def get_identifier(recipe):
    '''Return identifier from recipe dict. Tries the Identifier
    top-level key and falls back to the legacy key location.'''
    try:
        return recipe["Identifier"]
    except (KeyError, AttributeError):
        try:
            return recipe["Input"]["IDENTIFIER"]
        except (KeyError, AttributeError):
            return None


def get_identifier_from_recipe_file(filename):
    '''Attempts to read plist file filename and get the
    identifier. Otherwise, returns None.'''
    try:
        # make sure we can read it
        recipe_plist = FoundationPlist.readPlist(filename)
    except FoundationPlist.FoundationPlistException, err:
        print >> sys.stderr, (
            "WARNING: plist error for %s: %s" % (filename, unicode(err)))
        return None
    return get_identifier(recipe_plist)


def find_recipe_by_identifier(identifier, search_dirs):
    '''Search search_dirs for a recipe with the given
    identifier'''
    for directory in search_dirs:
        normalized_dir = os.path.abspath(os.path.expanduser(directory))
        patterns = [
            os.path.join(normalized_dir, "*.recipe"),
            os.path.join(normalized_dir, "*/*.recipe")
        ]
        for pattern in patterns:
            matches = glob.glob(pattern)
            for match in matches:
                if get_identifier_from_recipe_file(match) == identifier:
                    return match

    return None


def get_autopkg_version():
    '''Gets the version number of autopkg'''
    try:
        version_plist = FoundationPlist.readPlist(
            os.path.join(os.path.dirname(__file__), "version.plist"))
    except FoundationPlist.FoundationPlistException:
        return "UNKNOWN"
    try:
        return version_plist["Version"]
    except (AttributeError, TypeError):
        return "UNKNOWN"


def version_equal_or_greater(this, that):
    '''Compares two LooseVersion objects. Returns True if this is
    equal to or greater than that'''
    return LooseVersion(this) >= LooseVersion(that)


def update_data(a_dict, key, value):
    """Update a_dict keys with value. Existing data can be referenced
    by wrapping the key in %percent% signs."""

    def getdata(match):
        '''Returns data from a match object'''
        return a_dict[match.group("key")]

    def do_variable_substitution(item):
        """Do variable substitution for item"""
        if isinstance(item, basestring):
            try:
                item = RE_KEYREF.sub(getdata, item)
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
    """Base Error class"""
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
        """Print a message if verbosity is >= verbose_level"""
        if self.env.get('verbose', 0) >= verbose_level:
            print "%s: %s" % (self.__class__.__name__, msg)

    def main(self):
        """Stub method"""
        #pylint: disable=no-self-use
        raise ProcessorError("Abstract method main() not implemented.")

    def get_manifest(self):
        """Return Processor's description, input and output variables"""
        #pylint: disable=no-member
        try:
            return (self.description,
                    self.input_variables,
                    self.output_variables)
        except AttributeError as err:
            raise ProcessorError("Missing manifest: %s" % err)

    def read_input_plist(self):
        """Read environment from input plist."""

        try:
            indata = self.infile.read()
            if indata:
                self.env = FoundationPlist.readPlistFromString(indata)
            else:
                self.env = dict()
        except BaseException as err:
            raise ProcessorError(err)

    def write_output_plist(self):
        """Write environment to output as plist."""

        if self.env is None:
            return

        try:
            FoundationPlist.writePlist(self.env, self.outfile)
        except BaseException as err:
            raise ProcessorError(err)

    def parse_arguments(self):
        """Parse arguments as key='value'."""

        for arg in sys.argv[1:]:
            (key, sep, value) = arg.partition("=")
            if sep != "=":
                raise ProcessorError("Illegal argument '%s'" % arg)
            update_data(self.env, key, value)

    def inject(self, arguments):
        '''Update environment data with arguments.'''
        for key, value in arguments.items():
            update_data(self.env, key, value)

    def process(self):
        """Main processing loop."""
        #pylint: disable=no-member
        # Make sure all required arguments have been supplied.
        for variable, flags in self.input_variables.items():
            # Apply default values to unspecified input variables
            if "default" in flags.keys() and (variable not in self.env):
                self.env[variable] = flags["default"]
                self.output("No value supplied for %s, setting default value "
                            "of: %s" % (variable, self.env[variable]),
                            verbose_level=2)
            # Make sure all required arguments have been supplied.
            if flags.get("required") and (variable not in self.env):
                raise ProcessorError(
                    "%s requires %s" % (self.__name__, variable))

        self.main()
        return self.env

    def cmdexec(self, command, description):
        """Execute a command and return output."""
        #pylint: disable=no-self-use

        try:
            proc = subprocess.Popen(command,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            (stdout, stderr) = proc.communicate()
        except OSError as err:
            raise ProcessorError(
                "%s execution failed with error code %d: %s"
                % (command[0], err.errno, err.strerror))
        if proc.returncode != 0:
            raise ProcessorError("%s failed: %s" % (description, stderr))

        return stdout

    def execute_shell(self):
        """Execute as a standalone binary on the commandline."""

        try:
            self.read_input_plist()
            self.parse_arguments()
            self.main()
            self.write_output_plist()
        except ProcessorError as err:
            print >> sys.stderr, "ProcessorError: %s" % err
            sys.exit(10)
        else:
            sys.exit(0)

# AutoPackager class defintion

class AutoPackagerError(Exception):
    """Error class"""
    pass

class AutoPackager(object):
    """Instantiate and execute processors from a recipe."""

    def __init__(self, options, env):
        self.verbose = options.verbose
        self.env = env
        self.results = []
        self.env["AUTOPKG_VERSION"] = get_autopkg_version()

    def output(self, msg, verbose_level=1):
        """Print msg if verbosity is >= than verbose_level"""
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
                    "Recipe (or a parent recipe) requires at least version "
                    "%s, but we are version %s."
                    % (recipe.get("MinimumVersion"),
                       self.env["AUTOPKG_VERSION"]))

        # Initialize variable set with input variables.
        variables = set(recipe["Input"].keys())
        # Add environment.
        variables.update(set(self.env.keys()))
        # Check each step of the process.
        for step in recipe["Process"]:
            try:
                processor_class = get_processor(step["Processor"],
                                                recipe=recipe, env=self.env)
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
            except OSError, err:
                raise AutoPackagerError(
                    "Could not create RECIPE_CACHE_DIR %s: %s"
                    % (self.env["RECIPE_CACHE_DIR"], err))

        if self.verbose > 2:
            pprint.pprint(self.env)

        for step in recipe["Process"]:

            if self.verbose:
                print step["Processor"]

            processor_name = extract_processor_name_with_recipe_identifier(
                step["Processor"])[0]
            processor_class = get_processor(processor_name)
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
            except Exception as err:
                # Well-behaved processors should handle exceptions and
                # raise ProcessorError. However, we catch Exception
                # here to ensure that unexpected/unhandled exceptions
                # from one processor do not prevent execution of
                # subsequent recipes.
                print >> sys.stderr, unicode(err)
                raise AutoPackagerError(
                    "Error in %s: Processor: %s: Error: %s"
                    % (identifier, step["Processor"], unicode(err)))

            output_dict = {}
            for key in processor.output_variables.keys():
                # Safety workaround for Processors that may output
                # differently-named output variables than are given in
                # their output_variables
                # TODO: develop a generic solution for processors that
                #       can dynamically set their output_variables
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


_PROCESSOR_NAMES = []
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
        _PROCESSOR_NAMES.append(name)


# convenience functions for adding and accessing processors
# since these can change dynamically
def add_processor(name, processor_object):
    '''Adds a Processor to the autopkglib namespace'''
    globals()[name] = processor_object
    if not name in _PROCESSOR_NAMES:
        _PROCESSOR_NAMES.append(name)


#pylint: disable=invalid-name
def extract_processor_name_with_recipe_identifier(processor_name):
    '''Returns a tuple of (processor_name, identifier), given a Processor
    name.  This is to handle a processor name that may include a recipe
    identifier, in the format:

    com.github.autopkg.recipes.somerecipe/ProcessorName

    identifier will be None if one was not extracted.'''
    identifier, delim, processor_name = processor_name.partition('/')
    if not delim:
        # if no '/' was found, the first item in the tuple will be the
        # full string, the processor name
        processor_name = identifier
        identifier = None
    return (processor_name, identifier)
#pylint: enable=invalid-name


def get_processor(processor_name, recipe=None, env=None):
    '''Returns a Processor object given a name and optionally a recipe,
    importing a processor from the recipe directory if available'''
    if env is None:
        env = {}
    if recipe:
        recipe_dir = os.path.dirname(recipe['RECIPE_PATH'])
        processor_search_dirs = [recipe_dir]

        # check if our processor_name includes a recipe identifier that
        # should be used to locate the recipe.
        # if so, search for the recipe by identifier in order to add
        # its dirname to the processor search dirs
        (processor_name, processor_recipe_id) = (
            extract_processor_name_with_recipe_identifier(processor_name))
        if processor_recipe_id:
            shared_processor_recipe_path = (
                find_recipe_by_identifier(processor_recipe_id,
                                          env["RECIPE_SEARCH_DIRS"]))
            if shared_processor_recipe_path:
                processor_search_dirs.append(
                    os.path.dirname(shared_processor_recipe_path))

        # search recipe dirs for processor
        if recipe.get("PARENT_RECIPES"):
            # also look in the directories containing the parent recipes
            parent_recipe_dirs = list(set([
                os.path.dirname(item)
                for item in recipe["PARENT_RECIPES"]]))
            processor_search_dirs.extend(parent_recipe_dirs)

        for directory in processor_search_dirs:
            processor_filename = os.path.join(directory, processor_name + '.py')
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
                    # if we aren't successful, that might be OK, we're
                    # going see if the processor was already imported
                    print >> sys.stderr, (
                        "WARNING: %s: %s" % (processor_filename, err))

    return globals()[processor_name]


def processor_names():
    """Return our Processor names"""
    return _PROCESSOR_NAMES


# when importing autopkglib, need to also import all the processors
# in this same directory
import_processors()
