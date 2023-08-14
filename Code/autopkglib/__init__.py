#!/usr/local/autopkg/python
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
import plistlib
import pprint
import subprocess
import sys
import traceback
from distutils.version import LooseVersion
from typing import IO, Dict, List, Optional

import pkg_resources
import yaml
from autopkglib.common import (
    DEFAULT_SEARCH_DIRS,
    DEFAULT_USER_OVERRIDES_DIR,
    DEFAULT_RECIPE_MAP,
    RE_KEYREF,
    RECIPE_EXTS,
    FileOrPath,
    VarDict,
    autopkg_user_folder,
    is_linux,
    is_mac,
    is_windows,
    log,
    log_err,
)
from autopkglib.prefs import Preferences

try:
    from CoreFoundation import (  # type: ignore
        CFPreferencesAppSynchronize,
        CFPreferencesCopyAppValue,
        CFPreferencesCopyKeyList,
        CFPreferencesSetAppValue,
        kCFPreferencesAnyHost,
        kCFPreferencesAnyUser,
        kCFPreferencesCurrentHost,
        kCFPreferencesCurrentUser,
    )
    from Foundation import NSArray, NSDictionary, NSNumber  # type: ignore
except ImportError:
    if is_mac():
        print(
            "ERROR: Failed 'from Foundation import NSArray, NSDictionary' in "
            + __name__
        )
        print(
            "ERROR: Failed 'from CoreFoundation import "
            "CFPreferencesAppSynchronize, ...' in " + __name__
        )
        raise
    # On non-macOS platforms, the above imported names are stubbed out.
    NSArray = list
    NSDictionary = dict
    NSNumber = int

    def CFPreferencesAppSynchronize(*args, **kwargs):
        pass

    def CFPreferencesCopyAppValue(*args, **kwargs):
        pass

    def CFPreferencesCopyKeyList(*args, **kwargs):
        return []

    def CFPreferencesSetAppValue(*args, **kwargs):
        pass

    kCFPreferencesAnyHost = None
    kCFPreferencesAnyUser = None
    kCFPreferencesCurrentUser = None
    kCFPreferencesCurrentHost = None

# Set the global preferences object
globalPreferences = Preferences()

# Set the global recipe map
globalRecipeMap: Dict[str, Dict[str, str]] = {
    "identifiers": {},
    "shortnames": {},
    "overrides": {},
}


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


def remove_recipe_extension(name):
    """Removes supported recipe extensions from a filename or path.
    If the filename or path does not end with any known recipe extension,
    the name is returned as is."""
    for ext in RECIPE_EXTS:
        if name.endswith(ext):
            return name[: -len(ext)]
    return name


def recipe_from_file(filename):
    """Create a recipe dictionary from a file. Handle exceptions and log"""
    if not filename:
        # If we made GitHub search suggestions but the operator selected no, this will be None
        return
    if not os.path.isfile(filename):
        return

    if filename.endswith(".yaml"):
        try:
            # try to read it as yaml
            with open(filename, "rb") as f:
                recipe_dict = yaml.load(f, Loader=yaml.FullLoader)
            return recipe_dict
        except Exception as err:
            log_err(f"WARNING: yaml error for {filename}: {err}")
            raise

    else:
        try:
            # try to read it as a plist
            with open(filename, "rb") as f:
                recipe_dict = plistlib.load(f)
            return recipe_dict
        except Exception as err:
            log_err(f"WARNING: plist error for {filename}: {err}")
            raise


def valid_recipe_file(filename) -> bool:
    """Returns True if filename contains a valid recipe,
    otherwise returns False"""
    try:
        recipe_dict = recipe_from_file(filename)
    except Exception:
        # If we can't read the file due to a syntax or parsing error, we definitely don't have a valid dict
        return False
    return valid_recipe_dict(recipe_dict)


def valid_recipe_dict(recipe_dict) -> bool:
    """Returns True if recipe dict is a valid recipe,
    otherwise returns False"""
    return (
        valid_recipe_dict_with_keys(recipe_dict, ["Input", "Process"])
        or valid_recipe_dict_with_keys(recipe_dict, ["Input", "Recipe"])
        or valid_recipe_dict_with_keys(recipe_dict, ["Input", "ParentRecipe"])
    )


def valid_override_dict(recipe_dict) -> bool:
    """Returns True if the recipe is a valid override,
    otherwise returns False"""
    return valid_recipe_dict_with_keys(
        recipe_dict, ["Input", "ParentRecipe"]
    ) or valid_recipe_dict_with_keys(recipe_dict, ["Input", "Recipe"])


def valid_override_file(filename) -> bool:
    """Returns True if filename contains a valid override,
    otherwise returns False"""
    override_dict = recipe_from_file(filename)
    return valid_override_dict(override_dict)


def valid_recipe_dict_with_keys(recipe_dict, keys_to_verify) -> bool:
    """Attempts to read a dict and ensures the keys in
    keys_to_verify exist. Returns False on any failure, True otherwise."""
    if recipe_dict:
        for key in keys_to_verify:
            if key not in recipe_dict:
                return False
        # if we get here, we found all the keys
        return True
    return False


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


def get_identifier_from_recipe_file(filename) -> Optional[str]:
    """Attempts to read filename and get the
    identifier. Otherwise, returns None."""
    if valid_recipe_file(filename):
        recipe_dict = recipe_from_file(filename)
        return get_identifier(recipe_dict)
    return None


def find_recipe_by_identifier(
    identifier: str, skip_overrides: bool = False
) -> Optional[str]:
    """Search recipe map for an identifier"""
    if not skip_overrides and identifier in globalRecipeMap.get(
        "overrides-identifiers", {}
    ):
        if valid_recipe_file(globalRecipeMap["overrides-identifiers"][identifier]):
            log(f"Found {identifier} in recipe map overrides")
            return globalRecipeMap["overrides-identifiers"][identifier]
    if not skip_overrides and identifier in globalRecipeMap["identifiers"]:
        if valid_recipe_file(globalRecipeMap["identifiers"][identifier]):
            log(f"Found {identifier} in recipe map")
            return globalRecipeMap["identifiers"][identifier]
    return None


def find_recipe_by_name(name: str, skip_overrides: bool = False) -> Optional[str]:
    """Search recipe map for a shortname"""
    # Check the overrides first, unless skipping them
    if not skip_overrides and name in globalRecipeMap["overrides"]:
        if valid_recipe_file(globalRecipeMap["overrides"][name]):
            log(f"Found {name} in recipe map overrides")
            return globalRecipeMap["overrides"][name]
    # search by "Name" in the recipe map
    if name in globalRecipeMap["shortnames"]:
        if valid_recipe_file(globalRecipeMap["shortnames"][name]):
            log(f"Found {name} in recipe map")
            return globalRecipeMap["shortnames"][name]
    return None


def find_name_from_identifier(identifier: str) -> Optional[str]:
    """Find a recipe name from its identifier"""
    recipe_path = globalRecipeMap["identifiers"].get(identifier)
    for shortname, path in globalRecipeMap["shortnames"].items():
        if recipe_path == path:
            return shortname
    log_err(f"Could not find shortname from {identifier}!")
    return None


def find_identifier_from_name(name: str) -> Optional[str]:
    """Find a recipe identifier from its shortname"""
    recipe_path = globalRecipeMap["shortnames"].get(name)
    for id, path in globalRecipeMap["identifiers"].items():
        if recipe_path == path:
            return id
    log_err(f"Could not find identifier from {name}!")
    return None


def get_search_dirs() -> List[str]:
    """Return search dirs from preferences or default list"""
    default = [".", "~/Library/AutoPkg/Recipes", "/Library/AutoPkg/Recipes"]

    dirs: List[str] = get_pref("RECIPE_SEARCH_DIRS")
    if isinstance(dirs, str):
        # convert a string to a list
        dirs = [dirs]
    return dirs or default


def get_override_dirs() -> List[str]:
    """Return override dirs from preferences or default list"""
    default = ["~/Library/AutoPkg/RecipeOverrides"]

    dirs: List[str] = get_pref("RECIPE_OVERRIDE_DIRS")
    if isinstance(dirs, str):
        # convert a string to a list
        dirs = [dirs]
    return dirs or default


def calculate_recipe_map(
    extra_search_dirs: Optional[List[str]] = None,
    extra_override_dirs: Optional[List[str]] = None,
):
    """Recalculate the entire recipe map"""
    global globalRecipeMap
    globalRecipeMap = {
        "identifiers": {},
        "shortnames": {},
        "overrides": {},
        "overrides-identifiers": {},
    }
    # If extra search paths were provided as CLI arguments, let's search those too
    if extra_search_dirs is None:
        extra_search_dirs = []
    if extra_override_dirs is None:
        extra_override_dirs = []
    search_dirs = get_pref("RECIPE_SEARCH_DIRS") or DEFAULT_SEARCH_DIRS
    for search_dir in search_dirs + extra_search_dirs:
        if search_dir == ".":
            # skip searching cwd
            continue
        globalRecipeMap["identifiers"].update(
            map_key_to_paths("identifiers", search_dir)
        )
        globalRecipeMap["shortnames"].update(map_key_to_paths("shortnames", search_dir))
    # Do overrides separately
    for override in get_override_dirs() + extra_override_dirs:
        globalRecipeMap["overrides"].update(map_key_to_paths("overrides", override))
        globalRecipeMap["overrides-identifiers"].update(
            map_key_to_paths("overrides-identifiers", override)
        )
    if not extra_search_dirs or not extra_override_dirs:
        # Don't store the extra stuff in the cache; they're intended to be temporary
        write_recipe_map_to_disk()


def map_key_to_paths(keyname: str, repo_dir: str) -> Dict[str, str]:
    """Return a dict of keyname to absolute recipe paths"""
    recipe_map = {}
    normalized_dir = os.path.abspath(os.path.expanduser(repo_dir))
    patterns = [os.path.join(normalized_dir, f"*{ext}") for ext in RECIPE_EXTS]
    patterns.extend([os.path.join(normalized_dir, f"*/*{ext}") for ext in RECIPE_EXTS])
    for pattern in patterns:
        matches = glob.glob(pattern)
        for match in matches:
            if "identifiers" in keyname:
                key = get_identifier_from_recipe_file(match)
            else:
                key = remove_recipe_extension(os.path.basename(match))
            # In case the file was invalid, or missing a key
            if not key:
                print(
                    f"WARNING: {match} is potentially an invalid file, not adding it to the recipe map! "
                    "Please file a GitHub Issue for this repo."
                )
                continue
            # key is the recipe shortname at this point
            if key in recipe_map or key in globalRecipeMap[keyname]:
                # we already have this recipe, don't update it
                continue
            recipe_map[key] = match
    return recipe_map


def write_recipe_map_to_disk():
    """Write the recipe map to disk"""
    local_recipe_map = {}
    # try:
    #     with open(os.path.join(autopkg_user_folder(), "recipe_map.json"), "r") as f:
    #         local_recipe_map = json.load(f)
    # except (OSError):
    #     pass
    local_recipe_map.update(globalRecipeMap)
    with open(os.path.join(autopkg_user_folder(), "recipe_map.json"), "w") as f:
        json.dump(
            local_recipe_map,
            f,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )


def read_recipe_map(rebuild: bool = False) -> None:
    """Retrieve a dict of the recipe map of identifiers to paths"""
    global globalRecipeMap
    recipe_map = {}
    try:
        with open(os.path.join(autopkg_user_folder(), "recipe_map.json"), "r") as f:
            recipe_map = json.load(f)
        # Let's do some validation first
        expected_keys = [
            "identifiers",
            "overrides",
            "overrides-identifiers",
            "shortnames",
        ]
        if not set(expected_keys).issubset(recipe_map.keys()):
            raise OSError
        globalRecipeMap.update(recipe_map)
    except (OSError, json.decoder.JSONDecodeError):
        if rebuild:
            log("Cannot find or read the recipe map! Creating it now...")
            calculate_recipe_map()
        else:
            log(
                "Cannot parse the recipe map - it's either missing or invalid!"
                "\nTry adding or removing a repo to rebuild it."
            )
            raise


def get_autopkg_version():
    """Gets the version number of autopkg"""
    try:
        version_plist = plistlib.load(
            pkg_resources.resource_stream(__name__, "version.plist")
        )
    except Exception as ex:
        log_err(f"Unable to get autopkg version: {ex}")
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
                log_err(f"Use of undefined key in variable substitution: {err}")
        elif isinstance(item, (list, NSArray)):
            for index in range(len(item)):
                item[index] = do_variable_substitution(item[index])
        elif isinstance(item, (dict, NSDictionary)):
            # Modify a copy of the original
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


def is_executable(exe_path):
    """Is exe_path executable?"""
    return os.path.exists(exe_path) and os.access(exe_path, os.X_OK)


def find_binary(binary: str, env: Optional[Dict] = None) -> Optional[str]:
    r"""Returns the full path for `binary`, or `None` if it was not found.

    The search order is as follows:
    * A key in the optional `env` dictionary named `<binary>_PATH`.
        Where `binary` is uppercase. E.g., `git` -> `GIT`.
    * A preference named `<binary>_PATH` uppercase, as above.
    * The directories listed in the system-dependent `$PATH` environment variable.
    * On POSIX-y platforms only: `/usr/bin/<binary>`
    In all cases, the binary found at any path must be executable to be used.

    The `binary` parameter should be given without any file extension. A platform
    specific file extension for executables will be added automatically, as needed.

    Example: `find_binary('curl')` may return `C:\Windows\system32\curl.exe`.
    """

    if env is None:
        env = {}
    pref_key = f"{binary.upper()}_PATH"

    bin_env = env.get(pref_key)
    if bin_env:
        if not is_executable(bin_env):
            log_err(
                f"WARNING: path given in the '{pref_key}' environment: '{bin_env}' "
                "either doesn't exist or is not executable! "
                f"Continuing search for usable '{binary}'."
            )
        else:
            return env[pref_key]

    bin_pref = get_pref(pref_key)
    if bin_pref:
        if not is_executable(bin_pref):
            log_err(
                f"WARNING: path given in the '{pref_key}' preference: '{bin_pref}' "
                "either doesn't exist or is not executable! "
                f"Continuing search for usable '{binary}'."
            )
        else:
            return bin_pref

    if is_windows():
        extension = ".exe"
    else:
        extension = ""

    full_binary = f"{binary}{extension}"

    for search_dir in os.get_exec_path():
        exe_path = os.path.join(search_dir, full_binary)
        if is_executable(exe_path):
            return exe_path

    if (is_linux() or is_mac()) and is_executable(f"/usr/bin/{binary}"):
        return f"/usr/bin/{binary}"

    log_err(
        f"WARNING: Unable to find '{full_binary}' in either configured, "
        "or environmental locations. Things aren't guaranteed to work from here."
    )
    return None


# Processor and ProcessorError base class definitions


class ProcessorError(Exception):
    """Base Error class"""

    pass


class Processor:
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
        if int(self.env.get("verbose", 0)) >= verbose_level:
            print(f"{self.__class__.__name__}: {msg}")

    def main(self):
        """Stub method"""
        raise ProcessorError("Abstract method main() not implemented.")

    def get_manifest(self):
        """Return Processor's description, input and output variables"""
        try:
            return (self.description, self.input_variables, self.output_variables)
        except AttributeError as err:
            raise ProcessorError(f"Missing manifest: {err}") from err

    def read_input_plist(self):
        """Read environment from input plist."""

        try:
            indata = self.infile.buffer.read()
            if indata:
                self.env = plistlib.loads(indata)
            else:
                self.env = {}
        except BaseException as err:
            raise ProcessorError(err) from err

    def write_output_plist(self):
        """Write environment to output as plist."""

        if self.env is None:
            return

        try:
            with open(self.outfile, "wb") as f:
                plistlib.dump(self.env, f)
        except TypeError:
            plistlib.dump(self.env, self.outfile.buffer)
        except BaseException as err:
            raise ProcessorError(err) from err

    def parse_arguments(self):
        """Parse arguments as key='value'."""

        for arg in sys.argv[1:]:
            (key, sep, value) = arg.partition("=")
            if sep != "=":
                raise ProcessorError(f"Illegal argument '{arg}'")
            update_data(self.env, key, value)

    def inject(self, arguments):
        """Update environment data with arguments."""
        for key, value in list(arguments.items()):
            update_data(self.env, key, value)

    def process(self):
        """Main processing loop."""
        # Make sure all required arguments have been supplied.
        for variable, flags in list(self.input_variables.items()):
            # Apply default values to unspecified input variables
            if "default" in list(flags.keys()) and (variable not in self.env):
                self.env[variable] = flags["default"]
                self.output(
                    f"No value supplied for {variable}, setting default value "
                    f"of: {self.env[variable]}",
                    verbose_level=2,
                )
            # Make sure all required arguments have been supplied.
            if flags.get("required") and (variable not in self.env):
                raise ProcessorError(f"{self.__class__.__name__} requires {variable}")

        self.main()
        return self.env

    def cmdexec(self, command, description):
        """Execute a command and return output."""

        try:
            proc = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            (stdout, stderr) = proc.communicate()
        except OSError as err:
            raise ProcessorError(
                f"{command[0]} execution failed with error code "
                f"{err.errno}: {err.strerror}"
            ) from err
        if proc.returncode != 0:
            raise ProcessorError(f"{description} failed: {stderr}")

        return stdout

    def execute_shell(self):
        """Execute as a standalone binary on the commandline."""

        try:
            self.read_input_plist()
            self.parse_arguments()
            self.process()
            self.write_output_plist()
        except ProcessorError as err:
            log_err(f"ProcessorError: {err}")
            sys.exit(10)
        else:
            sys.exit(0)

    def load_plist_from_file(
        self,
        plist_file: FileOrPath,
        exception_text: str = "Unable to load plist",
    ) -> VarDict:
        """Load plist from a path or file-like object and return content as dictionary.

        If there is an error loading the file, the exception raised will be prefixed
        with `exception_text`.
        """
        if isinstance(plist_file, (str, bytes, int)):
            try:
                fh: IO = open(plist_file, "rb")
            except OSError as err:
                raise ProcessorError(f"{exception_text}: {err}") from err
        else:
            fh = plist_file
        try:
            return plistlib.load(fh)
        except Exception as err:
            raise ProcessorError(f"{exception_text}: {err}") from err
        finally:
            fh.close()


# AutoPackager class defintion


class AutoPackagerError(Exception):
    """Error class"""

    pass


class AutoPackagerLoadError(Exception):
    """Represent an exception loading a recipe or processor."""

    pass


class AutoPackager:
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
        """Return the identifier given an input recipe dict."""
        identifier = recipe.get("Identifier") or recipe["Input"].get("IDENTIFIER")
        if not identifier:
            log_err("ID NOT FOUND")
            # build a pseudo-identifier based on the recipe pathname
            recipe_path = self.env.get("RECIPE_PATH")
            # get rid of filename extension
            recipe_path = remove_recipe_extension(recipe_path)
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
                    f"version {recipe.get('MinimumVersion')}, but we are autopkg "
                    f"version {self.env['AUTOPKG_VERSION']}."
                )

        # Initialize variable set with input variables.
        variables = set(recipe["Input"].keys())
        # Add environment.
        variables.update(set(self.env.keys()))
        # Check each step of the process.
        for step in recipe["Process"]:
            try:
                processor_class = get_processor(
                    step["Processor"], verbose=self.verbose, recipe=recipe, env=self.env
                )
            except (KeyError, AttributeError) as err:
                msg = f"Unknown processor '{step['Processor']}'."
                if "SharedProcessorRepoURL" in step:
                    msg += (
                        " This shared processor can be added via the "
                        f"repo: {step['SharedProcessorRepoURL']}."
                    )
                raise AutoPackagerError(msg) from err
            except AutoPackagerLoadError as err:
                msg = (
                    f"Unable to import '{step['Processor']}', likely due "
                    "to syntax or Python error."
                )
                raise AutoPackagerError(msg) from err
            # Add arguments to set of variables.
            variables.update(set(step.get("Arguments", {}).keys()))
            # Make sure all required input variables exist.
            for key, flags in list(processor_class.input_variables.items()):
                if flags["required"] and (key not in variables):
                    raise AutoPackagerError(
                        f"{step['Processor']} requires missing argument {key}"
                    )

            # Add output variables to set.
            variables.update(set(processor_class.output_variables.keys()))

    def process(self, recipe):
        """Process a recipe."""
        identifier = self.get_recipe_identifier(recipe)
        # define a cache/work directory for use by the recipe
        cache_dir = self.env.get("CACHE_DIR") or os.path.expanduser(
            os.path.join(autopkg_user_folder(), "Cache"),
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
                    f"Could not create RECIPE_CACHE_DIR {self.env['RECIPE_CACHE_DIR']}:"
                    f" {err}"
                ) from err

        if self.verbose > 2:
            pprint.pprint(self.env)

        for step in recipe["Process"]:

            if self.verbose:
                print(step["Processor"])

            processor_name = extract_processor_name_with_recipe_identifier(
                step["Processor"]
            )[0]
            processor_class = get_processor(processor_name, verbose=self.verbose)
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
                if self.verbose > 2:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    traceback.print_exc(file=sys.stdout)
                    traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
                # Well-behaved processors should handle exceptions and
                # raise ProcessorError. However, we catch Exception
                # here to ensure that unexpected/unhandled exceptions
                # from one processor do not prevent execution of
                # subsequent recipes.
                log_err(err)
                raise AutoPackagerError(
                    f"Error in {identifier}: Processor: {step['Processor']}: "
                    f"Error: {err}"
                ) from err

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


def _cmp(x, y):
    """
    Replacement for built-in function cmp that was removed in Python 3
    Compare the two objects x and y and return an integer according to
    the outcome. The return value is negative if x < y, zero if x == y
    and strictly positive if x > y.
    """
    return (x > y) - (x < y)


class APLooseVersion(LooseVersion):
    """Subclass of distutils.version.LooseVersion to fix issues under Python 3"""

    def _pad(self, version_list, max_length):
        """Pad a version list by adding extra 0 components to the end if needed."""
        # copy the version_list so we don't modify it
        cmp_list = list(version_list)
        while len(cmp_list) < max_length:
            cmp_list.append(0)
        return cmp_list

    def _compare(self, other):
        """Complete comparison mechanism since LooseVersion's is broken in Python 3."""
        if not isinstance(other, (LooseVersion, APLooseVersion)):
            other = APLooseVersion(other)
        max_length = max(len(self.version), len(other.version))
        self_cmp_version = self._pad(self.version, max_length)
        other_cmp_version = self._pad(other.version, max_length)
        cmp_result = 0
        for index, value in enumerate(self_cmp_version):
            try:
                cmp_result = _cmp(value, other_cmp_version[index])
            except TypeError:
                # integer is less than character/string
                if isinstance(value, int):
                    return -1
                return 1
            else:
                if cmp_result:
                    return cmp_result
        return cmp_result

    def __hash__(self):
        """Hash method."""
        return hash(self.version)

    def __eq__(self, other):
        """Equals comparison."""
        return self._compare(other) == 0

    def __ne__(self, other):
        """Not-equals comparison."""
        return self._compare(other) != 0

    def __lt__(self, other):
        """Less than comparison."""
        return self._compare(other) < 0

    def __le__(self, other):
        """Less than or equals comparison."""
        return self._compare(other) <= 0

    def __gt__(self, other):
        """Greater than comparison."""
        return self._compare(other) > 0

    def __ge__(self, other):
        """Greater than or equals comparison."""
        return self._compare(other) >= 0


_CORE_PROCESSOR_NAMES = []
_PROCESSOR_NAMES = []


def import_processors() -> None:
    processor_files: List[str] = [
        os.path.splitext(name)[0]
        for name in pkg_resources.resource_listdir(__name__, "")
        if name.endswith(".py")
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
    for name in filter(lambda f: f not in ("__init__", "xattr"), processor_files):
        globals()[name] = getattr(
            __import__(__name__ + "." + name, fromlist=[name]), name
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


def get_processor(processor_name, verbose=None, recipe=None, env=None):
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
                processor_recipe_id
            )
            if shared_processor_recipe_path:
                processor_search_dirs.append(
                    os.path.dirname(shared_processor_recipe_path)
                )

        # search recipe dirs for processor
        if recipe.get("PARENT_RECIPES"):
            # also look in the directories containing the parent recipes
            parent_recipe_dirs = list(
                {os.path.dirname(item) for item in recipe["PARENT_RECIPES"]}
            )
            processor_search_dirs.extend(parent_recipe_dirs)

        # Dedupe the list first
        deduped_processors = set([dir for dir in processor_search_dirs])
        for directory in deduped_processors:
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
                    log_err(f"WARNING: {processor_filename}: {err}")
                    if verbose > 2:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        traceback.print_exc(file=sys.stdout)
                        traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
                    raise AutoPackagerLoadError(err) from err

    return globals()[processor_name]


def processor_names():
    """Return our Processor names"""
    return _PROCESSOR_NAMES


def core_processor_names():
    """Returns the names of the 'core' processors"""
    return _CORE_PROCESSOR_NAMES


def plist_serializer(obj):
    """Serialize an object to ensure it can be dumped in plist format.

    Args:
        obj (dict, list): Object is assumed to be either a dict or list
            that will be parsed.

    Returns:
        (any): The received object will be returned, modified if required.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = "" if v is None else plist_serializer(v)
    elif isinstance(obj, list):
        for item in range(len(obj)):
            plist_serializer(obj[item])
    return obj


# when importing autopkglib, need to also import all the processors
# in this same directory


import_processors()
