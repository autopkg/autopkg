### 0.4.2 (Unreleased)

IMPROVEMENTS:

- CodeSignatureVerifier: support for 'DISABLE_CODE_SIGNATURE_VERIFICATION' input variable,
  which when set (to anything) will skip any verification performed by this processor. One
  would define this using the '--key' option for a run, or using a defaults preference.
  (GH-131)

### 0.4.1 (October 20, 2014)

IMPROVEMENTS:

- CodeSignatureVerifier: support for 'requirement' input variable for defining an expected
  requirement string in a binary or bundle. See Apple TN2206 for more details on code
  signing. (GH-114)
- CodeSignatureVerifier: use the '--deep' option for verify, when running on 10.9.5 or greater.
  (GH-124, GH-125)

### 0.4.0 (August 29, 2014)

IMPROVEMENTS:

- Recipe processors may now be used from recipes located outside the directory containing
  the processor. The recipe should refer to the processor as 'recipe.identifier/ProcessorName'.
  The recipe given by 'recipe.identifier' must be in the search path. See the [wiki page]
  (https://github.com/autopkg/autopkg/wiki/Processor-Locations) for more details. (GH-82)
- New Installer and InstallFromDMG processors, able to install pkgs and copy items from a disk
  image to the local filesystem. Allows for a new pattern of recipes that can install
  updates from recipes onto the system running autopkg.
- 'search' verb: Split repo and recipe path into two columns, making it easier to group repos
  visually and to pass to 'repo-add'. Allow searches that return up to 100 results.
- Processor input variables may now define a 'default' key, whose value will be substituted
  into that env key if it is not specified in the recipe. Removes the need to do manual
  default value code in the main processor logic. (GH-7, GH-107)

FIXES:

- Python scripts explicitly use OS X system Python at /usr/bin/python.

CHANGES:

- '--report-plist' is no longer a switch that toggles outputting the report to stdout,
  suppressing all other stdout logging. It now takes a path where the report will
  be saved, and logging to stdout not suppressed. The structure of the report remains
  the same. (GH-104)
- CACHE_DIR and RECIPE_REPO_DIR preferences can now include paths with a '~' that will
  be expanded, shell-style, to the user's home. (GH-105)

### 0.3.2 (July 24, 2014)

FIXES:

- Packaging server: When checking for permissions on the location of CACHE_DIR, handle
  possibility of unexpected diskutil output. This at least fixes an issue running pkg
  recipes on 10.6.
- MunkiImporter: Handle case where an installs array was present but an item is missing
  a 'type' key

CHANGES:

- PlistReader 'info_path' input variable, if given a path to a .dmg, previously mounted
  the dmg and searched the root for a bundle and its Info.plist. A path that _contains_
  a disk image can still be given and the image will be mounted, ie.
  "%RECIPE_CACHE_DIR/my.dmg/Some.app", but the behaviour of mounting a path containing
  _only_ the disk image was unused and an unusual pattern compared with other processors.
- Unarchiver: Create intermediate directories needed for 'destination_path' input var
  (GH-100)

### 0.3.1 (July 01, 2014)

ADDITIONS:

- New CodeSignatureVerifier processor, contributed by Hannes Juutilainen. (GH-92)
  - This can be used to verify code signatures for application bundles and
    installer packages against the expected certificate names, given as arguments
    to the processor. This would typically be used in download recipes to verify
    the authenticity of the downloaded item.


FIXES:

- Print a warning message when a recipe's ParentRecipe can't be found. (GH-30)
- Provide a more useful error message when a package cannot be built due to
  "ignore ownership on this volume" being set on the disk containing the pkg
  root. (GH-34)
- Fix a crash due to a missing import in a specific case where DmgMounter tries
  to handle an hdiutil-related error.
- Fix a crash as a result of parsing an incomplete recipe plist

### 0.3.0 (May 20, 2014)

ADDITIONS:

- New "search" autopkg CLI verb, used to search recipes using the GitHub API.
- MunkiInstallsItemsCreator and MunkiImporter now support setting 'version_comparison_key' to define this key for installs items. (GH-76, GH-54)
- MunkiImporter supports a new input variable, 'MUNKI_PKGINFO_FILE_EXTENSION', which when set, will save pkginfos with an alternate file extension. It is an all caps variable because you would typically define this globally using 'defaults write'.
- DmgCreator supports new input variables:
  - 'dmg_megabytes' to work around hdiutil sizing issues (GH-87)
  - 'dmg_format' and 'dmg_zlib_level' to set alternate disk image formats and gzip compression level (GH-14, GH-70)

CHANGES:

- PkgCreator processor does not rebuild a package on every run if one exists in the output directory with the same filename, identifier and version. This behavior can be overridden with the 'force_pkg_build' input variable.

FIXES:

- PlistReader, when searching a path for a bundle, no longer follows symlinks that don't contain extensions. It's common for a dmg to contain a symlink to '/Applications' and we don't want to go searching this path for bundles.
- autopkgserver's `pkg_request` argument no longer rejects an `id` that contains dashes between words (GH-91)

### 0.2.9 (February 28, 2014)

ADDITIONS:

- New FileMover processor, contributed by Jesse Peterson. (GH-64)
- New URLTextSearcher processor, contributed by Jesse Peterson. (GH-64)

### 0.2.8 (January 08, 2014)

FIXES:
- New package release to fix issue with autopkgsever launch daemon plist in 0.2.6 and 0.2.7 package releases.

### 0.2.7 (January 08, 2014)

FIXES:

- Fix unhandled exception when FoundationPlist encounters a malformed plist
- Fix long string wrapping in several Processor's descriptions and input/output variable descriptions. This caused `autopkg processor-info foo` to fail for several Processors.

### 0.2.6 (January 06, 2014)

FIXES:

- Fix for FoundationPlist functions under Snow Leopard. Changes to FoundationPlist in 0.2.5 broke autopkg under Snow Leopard; these changes remedy that.

### 0.2.5 (January 04, 2014)

ADDITIONS:

- New 'BrewCaskInfoProvider' processor: get URL and version info from crowd-sourced
  Homebrew formulae for many Mac applications (https://github.com/phinze/homebrew-cask)
- New 'PlistReader' processor contributed by Shea Craig. This can be used in place 
  of both the 'AppDmgVersioner' and 'Versioner' processors (which can now be considered 
  deprecated), and also supports reading arbitrary keys from plists and assigning them
  to arbitrary output variables for later use in recipes. (GH-56)
- Recipe Repo URLs for 'repo-' commands can now also be given in short GitHub-ish forms:
  1) 'ghuser/reponame' or 2) 'reponame', which will prefix the 'autopkg/' org name.
  Full URLs at any address can be given as before.
- Any input variable can now be set globally for all recipe runs by writing these as
  preference keys in the 'com.github.autopkg' domain. This is how the 'MUNKI_REPO' pref
  has been used up to now, but this now works for arbitrary keys, and the hardcoded
  support for MUNKI_REPO has been removed.

FIXES:

- FoundationPlist updated to use new Property List API methods.

### 0.2.4 (October 16, 2013)

ADDITIONS:

- New 'FlatPkgPacker' and 'FileFinder' processors, contributed by Jesse Peterson. (GH-36, GH-33)
- Copier processor supports glob wildcard characters for 'source_path', useful when
  exact path names vary. (GH-40)

CHANGES:

- 'FlatPkgUnpacker' processor now uses `pkgutil --expand` by default, meaning 'Scripts'
  archives will now be decompressed automatically. The `skip_payload` input variable
  will automatically switch the processor to use `xar` instead. (GH-36)

FIXES:

- Fix for MunkiImporter processor not finding an already-present pkg when using
  a manual `installs` key and with a unique `installer_item_hash`. (GH-35)
- Fix for 'mutating method sent to immutable object' errors, contributed by Joe
  Wollard and Michael Lynn (GH-24)
- MunkiImporter now checks for matching md5checksums when attempting to locate a matching
  pkginfo. (GH-41)

### 0.2.3 (September 27, 2013)

ADDITIONS:

- New 'FileFinder' processor for searching files, currently supports glob.
  Contributed by Jesse Peterson. (GH-33)

FIXES:

- Fix `autopkg info` showing a Description of a ParentRecipe instead of the actual recipe.
- Fix TypeError on Snow Leopard on list concatenation between Foundation and native Python list equivalents (GH-21)
- Fix case where a child recipe could not locate its parent(s) if the child was not already on the search path (GH-25)

### 0.2.2 (September 10, 2013)

CHANGES:

- Pkg recipe runs now print a report output similar to Munki recipes, and have version, identifier information available in the report.
- Fix for `autopkg version` when run from /usr/local/bin/autopkg

### 0.2.1 (September 2, 2013)

CHANGES:

- Relative paths given for "infofile", "resources", "options", "scripts" in a PkgCreator's pkg_request dictionary should now work if this path is found at the current working directory (GH-20)

### 0.2.0 (September 1, 2013)

CHANGES:

- The recipe identifier is now named "Identifier" and is a top-level recipe key. 
- The "recipe" key formerly seen in overrides has been renamed "ParentRecipe". Its value is now a string -- the identifier of its parent recipes.
- There is now essentially no difference between an "override" and a child recipe; a recipe can refer to a parent recipe, which can in turn refer to its own parent recipe, and so on.
- Child recipes can override keys in the Input dictionary and/or add new key/value pairs to the Input dictionary. This is the same functionality that RecipeOverrides have.
- Child recipes can add additional steps to the end of the Process of their ParentRecipe(s).  This is new functionality.
- Searching for recipes has changed: the order of searching by name and by identifier have been swapped: identifier is preferred to simple name.
- Certain Processors (specifically PkgInfoCreator and PkgCreator) are typically given paths to templates or resources or scripts pointing to the directory of the recipe. If a recipe can now have one or more parents, the meaning of "RECIPE_DIR" is a little unclear. So for this sort of thing, we now search the current child recipe directory for the requested resource, followed by any parent recipe's directory, then any parent recipe of the parent recipe's directory, etc. To support this behavior, give PkgInfoCreator and PkgCreator relative paths to PackageInfoTemplates and Resources and Scripts directories.
- New verbs to help people learn about Processors:
    - `autopkg list-processors` returns a list of "core" Processors -- those available to all recipes (in /Library/AutoPkg/autopkglib)
    - `autopkg processor-info PROCESSORNAME` prints basic documentation for PROCESSORNAME; use `autopkg processor-info PROCESSORNAME --recipe RECIPE` to get basic docs on a recipe-specific Processor (like MozillaURLProvider).

### 0.1.1 (August 27, 2013)

CHANGES:

  - Addresses an issue where creating RecipeOverrides failed if the recipe overrides directory (default: ~/Library/AutoPkg/ReceipeOverrides) is missing

### 0.1.0 (August 23, 2013)

FEATURES:

  - Initial pkg release.
