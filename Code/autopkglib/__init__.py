#!/usr/bin/python3
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


import glob
import imp
import json
import os
import platform
import plistlib
import pprint
import re
import subprocess
import sys
from distutils.version import LooseVersion


class memoize(dict):
    """Class to cache the return values of an expensive function.
    This version supports only functions with non-keyword arguments"""

    def __init__(self, func):
        self.func = func

    def __call__(self, *args):
        return self[args]

    def __missing__(self, key):
        result = self[key] = self.func(*key)
        return result


# @memoize
def is_mac():
    """Return True if current OS is macOS."""
    return "Darwin" in platform.platform()


# @memoize
def is_windows():
    """Return True if current OS is Windows."""
    return "Windows" in platform.platform()


# @memoize
def is_linux():
    """Return True if current OS is Linux."""
    return "Linux" in platform.platform()


try:
    from Foundation import NSArray, NSDictionary
    from CoreFoundation import (
        CFPreferencesAppSynchronize,
        CFPreferencesCopyAppValue,
        CFPreferencesCopyKeyList,
        CFPreferencesSetAppValue,
        kCFPreferencesAnyHost,
        kCFPreferencesAnyUser,
        kCFPreferencesCurrentUser,
        kCFPreferencesCurrentHost,
    )
    from PyObjCTools import Conversion
except Exception:
    pass

BUNDLE_ID = "com.github.autopkg"

RE_KEYREF = re.compile(r"%(?P<key>[a-zA-Z_][a-zA-Z_0-9]*)%")


class PreferenceError(Exception):
    """Preference exception"""

    pass


class Preferences(object):
    """An abstraction to hold all preferences."""

    def __init__(self):
        """Init."""
        self.prefs = {}
        # What type of preferences input are we using?
        self.type = None
        # Path to the preferences file we were given
        self.file_path = None
        # If we're on macOS, read in the preference domain first.
        if is_mac():
            self.prefs = self._get_macos_prefs()

    def _parse_json_or_plist_file(self, file_path):
        """Parse the file. Start with plist, then JSON."""
        try:
            with open(file_path, "r") as f:
                data = plistlib.load(f)
            self.type = "plist"
            self.file_path = file_path
            return data
        except Exception:
            pass
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                self.type = "json"
                self.file_path = file_path
                return data
        except Exception:
            pass
        return {}

    def _get_macos_pref(self, key):
        """Get a specific macOS preference key."""
        value = CFPreferencesCopyAppValue(key, BUNDLE_ID)
        # Casting NSArrays and NSDictionaries to native Python types.
        # This a workaround for 10.6, where PyObjC doesn't seem to
        # support as many common operations such as list concatenation
        # between Python and ObjC objects.
        if isinstance(value, NSArray) or isinstance(value, NSDictionary):
            value = Conversion.pythonCollectionFromPropertyList(value)
        return value

    def _get_macos_prefs(self):
        """Return a dict (or an empty dict) with the contents of all
        preferences in the domain."""
        prefs = {}

        # get keys stored via 'defaults write [domain]'
        user_keylist = CFPreferencesCopyKeyList(
            BUNDLE_ID, kCFPreferencesCurrentUser, kCFPreferencesAnyHost
        )

        # get keys stored via 'defaults write /Library/Preferences/[domain]'
        system_keylist = CFPreferencesCopyKeyList(
            BUNDLE_ID, kCFPreferencesAnyUser, kCFPreferencesCurrentHost
        )

        # CFPreferencesCopyAppValue() in get_macos_pref() will handle returning the
        # appropriate value using the search order, so merging prefs in order
        # here isn't necessary
        for keylist in [system_keylist, user_keylist]:
            if keylist:
                for key in keylist:
                    prefs[key] = self._get_macos_pref(key)
        return prefs

    def _set_macos_pref(self, key, value):
        """Sets a preference for domain"""
        try:
            CFPreferencesSetAppValue(key, value, BUNDLE_ID)
            if not CFPreferencesAppSynchronize(BUNDLE_ID):
                raise PreferenceError("Could not synchronize %s preference: %s" % key)
        except Exception as err:
            raise PreferenceError("Could not set %s preference: %s" % (key, err))

    def read_file(self, file_path):
        """Read in a file and add the key/value pairs into preferences."""
        # Determine type or file: plist or json
        data = self._parse_json_or_plist_file(file_path)
        for k in data:
            self.prefs[k] = data[k]

    def _write_json_file(self):
        """Write out the prefs into JSON."""
        try:
            with open(self.file_path, "w") as f:
                json.dump(
                    self.prefs,
                    f,
                    skipkeys=True,
                    ensure_ascii=True,
                    indent=2,
                    sort_keys=True,
                )
        except Exception as e:
            log_err("Unable to write out JSON: {}".format(e))

    def _write_plist_file(self):
        """Write out the prefs into a Plist."""
        try:
            with open(self.file_path, "wb") as f:
                plistlib.dump(self.prefs, f)
        except Exception as e:
            log_err("Unable to write out plist: {}".format(e))

    def write_file(self):
        """Write preferences back out to file."""
        if not self.file_path:
            # Nothing to do if we weren't given a file
            return
        if self.type == "json":
            self._write_json_file()
        elif self.type == "plist":
            self._write_plist_file()

    def get_pref(self, key):
        """Retrieve a preference value."""
        return self.prefs.get(key)

    def get_all_prefs(self):
        """Retrieve a dict of all preferences."""
        return self.prefs

    def set_pref(self, key, value):
        """Set a preference value."""
        self.prefs[key] = value
        # On macOS, write it back to preferences domain if we didn't use a file
        if is_mac() and self.type is None:
            self._set_macos_pref(key, value)
        elif self.file_path:
            self.write_file()


# Set the global preferences object
globalPreferences = Preferences()


def get_pref(key):
    """Return a single pref value (or None) for a domain."""
    return globalPreferences.get_pref(key)


def set_pref(key, value):
    """Sets a preference for domain"""
    globalPreferences.set_pref(key, value)


def get_all_prefs():
    """Return a dict (or an empty dict) with the contents of all
    preferences in the domain."""
    return globalPreferences.get_all_prefs()


def log(msg, error=False):
    """Message logger, prints to stdout/stderr."""
    if error:
        print(str(msg).encode("UTF-8"), file=sys.stderr)
    else:
        print(str(msg).encode("UTF-8"))


def log_err(msg):
    """Message logger for errors."""
    log(msg, error=True)


def get_identifier(recipe):
    """Return identifier from recipe dict. Tries the Identifier
    top-level key and falls back to the legacy key location."""
    try:
        return recipe["Identifier"]
    except (KeyError, AttributeError):
        try:
            return recipe["Input"]["IDENTIFIER"]
        except (KeyError, AttributeError):
            return None
    except TypeError:
        return None


def get_identifier_from_recipe_file(filename):
    """Attempts to read plist file filename and get the
    identifier. Otherwise, returns None."""
    try:
        # make sure we can read it
        with open(filename, "r") as f:
            recipe_plist = plistlib.load(f)
    except Exception as err:
        # unicode() doesn't exist in Python3, and we'd have to
        # change the behavior by importing unicode_literals from
        # __future__, which is a significant change requiring a lot of
        # testing. For now, we're going to leave this as-is until
        # the conversion to python3 is more mature.
        log_err("WARNING: plist error for %s: %s" % (filename, str(err)))  # noqa TODO
        return None
    return get_identifier(recipe_plist)


def find_recipe_by_identifier(identifier, search_dirs):
    """Search search_dirs for a recipe with the given
    identifier"""
    for directory in search_dirs:
        normalized_dir = os.path.abspath(os.path.expanduser(directory))
        patterns = [
            os.path.join(normalized_dir, "*.recipe"),
            os.path.join(normalized_dir, "*/*.recipe"),
        ]
        for pattern in patterns:
            matches = glob.glob(pattern)
            for match in matches:
                if get_identifier_from_recipe_file(match) == identifier:
                    return match

    return None


def get_autopkg_version():
    """Gets the version number of autopkg"""
    try:
        with open(os.path.join(os.path.dirname(__file__), "version.plist"), "r") as f:
            version_plist = plistlib.load(f)
    except Exception:
        return "UNKNOWN"
    try:
        return version_plist["Version"]
    except (AttributeError, TypeError):
        return "UNKNOWN"


def version_equal_or_greater(this, that):
    """Compares two LooseVersion objects. Returns True if this is
    equal to or greater than that"""
    return LooseVersion(this) >= LooseVersion(that)


def update_data(a_dict, key, value):
    """Update a_dict keys with value. Existing data can be referenced
    by wrapping the key in %percent% signs."""

    def getdata(match):
        """Returns data from a match object"""
        return a_dict[match.group("key")]

    def do_variable_substitution(item):
        """Do variable substitution for item"""
        if isinstance(item, str):
            try:
                item = RE_KEYREF.sub(getdata, item)
            except KeyError as err:
                log_err("Use of undefined key in variable substitution: %s" % err)
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
            for key, value in list(item.items()):
                item_copy[key] = do_variable_substitution(value)
            return item_copy
        return item

    a_dict[key] = do_variable_substitution(value)


def curl_cmd():
    """Returns a path to a curl binary, priority in the order below.
    Returns None if none found.
    1. app pref 'CURL_PATH'
    2. a 'curl' binary that can be found in the PATH environment variable
    3. '/usr/bin/curl'
    """

    def is_executable(exe_path):
        """Is exe_path executable?"""
        return os.path.exists(exe_path) and os.access(exe_path, os.X_OK)

    curl_path_pref = get_pref("CURL_PATH")
    if curl_path_pref:
        if is_executable(curl_path_pref):
            # take a CURL_PATH pref
            return curl_path_pref
        else:
            log_err(
                "WARNING: Curl path given in the 'CURL_PATH' preference:'%s' "
                "either doesn't exist or is not executable! Falling back "
                "to one set in PATH, or /usr/bin/curl." % curl_path_pref
            )
    for path_env in os.environ["PATH"].split(":"):
        curlbin = os.path.join(path_env, "curl")
        if is_executable(curlbin):
            # take the first 'curl' in PATH that we find
            return curlbin
    if is_executable("/usr/bin/curl"):
        # fall back to /usr/bin/curl
        return "/usr/bin/curl"
    return None


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
        # super(Processor, self).__init__()
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
        if self.env.get("verbose", 0) >= verbose_level:
            print("%s: %s" % (self.__class__.__name__, msg))

    def main(self):
        """Stub method"""
        # pylint: disable=no-self-use
        raise ProcessorError("Abstract method main() not implemented.")

    def get_manifest(self):
        """Return Processor's description, input and output variables"""
        # pylint: disable=no-member
        try:
            return (self.description, self.input_variables, self.output_variables)
        except AttributeError as err:
            raise ProcessorError("Missing manifest: %s" % err)

    def read_input_plist(self):
        """Read environment from input plist."""

        try:
            indata = self.infile.read()
            if indata:
                self.env = plistlib.loads(indata)
            else:
                self.env = {}
        except BaseException as err:
            raise ProcessorError(err)

    def write_output_plist(self):
        """Write environment to output as plist."""

        if self.env is None:
            return

        try:
            with open(self.outfile, "wb") as f:
                plistlib.dump(self.env, f)
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
        """Update environment data with arguments."""
        for key, value in list(arguments.items()):
            update_data(self.env, key, value)

    def process(self):
        """Main processing loop."""
        # pylint: disable=no-member
        # Make sure all required arguments have been supplied.
        for variable, flags in list(self.input_variables.items()):
            # Apply default values to unspecified input variables
            if "default" in list(flags.keys()) and (variable not in self.env):
                self.env[variable] = flags["default"]
                self.output(
                    "No value supplied for %s, setting default value "
                    "of: %s" % (variable, self.env[variable]),
                    verbose_level=2,
                )
            # Make sure all required arguments have been supplied.
            if flags.get("required") and (variable not in self.env):
                raise ProcessorError("%s requires %s" % (self.__name__, variable))

        self.main()
        return self.env

    def cmdexec(self, command, description):
        """Execute a command and return output."""
        # pylint: disable=no-self-use

        try:
            proc = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            (stdout, stderr) = proc.communicate()
        except OSError as err:
            raise ProcessorError(
                "%s execution failed with error code %d: %s"
                % (command[0], err.errno, err.strerror)
            )
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
            log_err("ProcessorError: %s" % err)
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
            print(msg)

    def get_recipe_identifier(self, recipe):
        """Return the identifier given an input recipe plist."""
        identifier = recipe.get("Identifier") or recipe["Input"].get("IDENTIFIER")
        if not identifier:
            log_err("ID NOT FOUND")
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
        for key, value in list(self.env.items()):
            update_data(self.env, key, value)

    def verify(self, recipe):
        """Verify a recipe and check for errors."""

        # Check for MinimumAutopkgVersion
        if "MinimumVersion" in list(recipe.keys()):
            if not version_equal_or_greater(
                self.env["AUTOPKG_VERSION"], recipe.get("MinimumVersion")
            ):
                raise AutoPackagerError(
                    "Recipe (or a parent recipe) requires at least autopkg "
                    "version %s, but we are autopkg version %s."
                    % (recipe.get("MinimumVersion"), self.env["AUTOPKG_VERSION"])
                )

        # Initialize variable set with input variables.
        variables = set(recipe["Input"].keys())
        # Add environment.
        variables.update(set(self.env.keys()))
        # Check each step of the process.
        for step in recipe["Process"]:
            try:
                processor_class = get_processor(
                    step["Processor"], recipe=recipe, env=self.env
                )
            except (KeyError, AttributeError):
                msg = "Unknown processor '%s'." % step["Processor"]
                if "SharedProcessorRepoURL" in step:
                    msg += (
                        " This shared processor can be added via the "
                        "repo: %s." % step["SharedProcessorRepoURL"]
                    )
                raise AutoPackagerError(msg)
            # Add arguments to set of variables.
            variables.update(set(step.get("Arguments", {}).keys()))
            # Make sure all required input variables exist.
            for key, flags in list(processor_class.input_variables.items()):
                if flags["required"] and (key not in variables):
                    raise AutoPackagerError(
                        "%s requires missing argument %s" % (step["Processor"], key)
                    )

            # Add output variables to set.
            variables.update(set(processor_class.output_variables.keys()))

    def process(self, recipe):
        """Process a recipe."""
        identifier = self.get_recipe_identifier(recipe)
        # define a cache/work directory for use by the recipe
        cache_dir = self.env.get("CACHE_DIR") or os.path.expanduser(
            "~/Library/AutoPkg/Cache"
        )
        self.env["RECIPE_CACHE_DIR"] = os.path.join(cache_dir, identifier)

        recipe_input_dict = {}
        for key in list(self.env.keys()):
            recipe_input_dict[key] = self.env[key]
        self.results.append({"Recipe input": recipe_input_dict})

        # make sure the RECIPE_CACHE_DIR exists, creating it if needed
        if not os.path.exists(self.env["RECIPE_CACHE_DIR"]):
            try:
                os.makedirs(self.env["RECIPE_CACHE_DIR"])
            except OSError as err:
                raise AutoPackagerError(
                    "Could not create RECIPE_CACHE_DIR %s: %s"
                    % (self.env["RECIPE_CACHE_DIR"], err)
                )

        if self.verbose > 2:
            pprint.pprint(self.env)

        for step in recipe["Process"]:

            if self.verbose:
                print(step["Processor"])

            processor_name = extract_processor_name_with_recipe_identifier(
                step["Processor"]
            )[0]
            processor_class = get_processor(processor_name)
            processor = processor_class(self.env)
            processor.inject(step.get("Arguments", {}))

            input_dict = {}
            for key in list(processor.input_variables.keys()):
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
                log_err(str(err))  # noqa TODO
                raise AutoPackagerError(
                    "Error in %s: Processor: %s: Error: %s"
                    % (identifier, step["Processor"], str(err))
                )  # noqa TODO

            output_dict = {}
            for key in list(processor.output_variables.keys()):
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

            self.results.append(
                {
                    "Processor": step["Processor"],
                    "Input": input_dict,
                    "Output": output_dict,
                }
            )

            if self.env.get("stop_processing_recipe"):
                # processing should stop now
                break

        if self.verbose > 2:
            pprint.pprint(self.env)


_CORE_PROCESSOR_NAMES = []
_PROCESSOR_NAMES = []


def import_processors():
    """Imports processors from the directory this init file is in"""
    # get the directory this __init__.py file is in
    mydir = os.path.dirname(os.path.abspath(__file__))
    mydirname = os.path.basename(mydir)

    # find all the .py files (minus this one)
    processor_files = [
        os.path.splitext(name)[0]
        for name in os.listdir(mydir)
        if name.endswith(".py") and not name == "__init__.py"
    ]

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
        globals()[name] = getattr(
            __import__(mydirname + "." + name, fromlist=[name]), name
        )
        _PROCESSOR_NAMES.append(name)
        _CORE_PROCESSOR_NAMES.append(name)


# convenience functions for adding and accessing processors
# since these can change dynamically
def add_processor(name, processor_object):
    """Adds a Processor to the autopkglib namespace"""
    globals()[name] = processor_object
    if name not in _PROCESSOR_NAMES:
        _PROCESSOR_NAMES.append(name)


# pylint: disable=invalid-name
def extract_processor_name_with_recipe_identifier(processor_name):
    """Returns a tuple of (processor_name, identifier), given a Processor
    name.  This is to handle a processor name that may include a recipe
    identifier, in the format:

    com.github.autopkg.recipes.somerecipe/ProcessorName

    identifier will be None if one was not extracted."""
    identifier, delim, processor_name = processor_name.partition("/")
    if not delim:
        # if no '/' was found, the first item in the tuple will be the
        # full string, the processor name
        processor_name = identifier
        identifier = None
    return (processor_name, identifier)


# pylint: enable=invalid-name


def get_processor(processor_name, recipe=None, env=None):
    """Returns a Processor object given a name and optionally a recipe,
    importing a processor from the recipe directory if available"""
    if env is None:
        env = {}
    if recipe:
        recipe_dir = os.path.dirname(recipe["RECIPE_PATH"])
        processor_search_dirs = [recipe_dir]

        # check if our processor_name includes a recipe identifier that
        # should be used to locate the recipe.
        # if so, search for the recipe by identifier in order to add
        # its dirname to the processor search dirs
        (
            processor_name,
            processor_recipe_id,
        ) = extract_processor_name_with_recipe_identifier(processor_name)
        if processor_recipe_id:
            shared_processor_recipe_path = find_recipe_by_identifier(
                processor_recipe_id, env["RECIPE_SEARCH_DIRS"]
            )
            if shared_processor_recipe_path:
                processor_search_dirs.append(
                    os.path.dirname(shared_processor_recipe_path)
                )

        # search recipe dirs for processor
        if recipe.get("PARENT_RECIPES"):
            # also look in the directories containing the parent recipes
            parent_recipe_dirs = list(
                {[os.path.dirname(item) for item in recipe["PARENT_RECIPES"]]}
            )
            processor_search_dirs.extend(parent_recipe_dirs)

        for directory in processor_search_dirs:
            processor_filename = os.path.join(directory, processor_name + ".py")
            if os.path.exists(processor_filename):
                try:
                    # attempt to import the module
                    _tmp = imp.load_source(processor_name, processor_filename)
                    # look for an attribute with the step Processor name
                    _processor = getattr(_tmp, processor_name)
                    # add the processor to autopkglib's namespace
                    add_processor(processor_name, _processor)
                    # we've added a Processor, so stop searching
                    break
                except (ImportError, AttributeError) as err:
                    # if we aren't successful, that might be OK, we're
                    # going see if the processor was already imported
                    log_err("WARNING: %s: %s" % (processor_filename, err))

    return globals()[processor_name]


def processor_names():
    """Return our Processor names"""
    return _PROCESSOR_NAMES


def core_processor_names():
    """Returns the names of the 'core' processors"""
    return _CORE_PROCESSOR_NAMES


# when importing autopkglib, need to also import all the processors
# in this same directory


import_processors()
