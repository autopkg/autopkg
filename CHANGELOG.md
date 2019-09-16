### [1.2](https://github.com/autopkg/autopkg/compare/v1.1...1.2) (Unreleased)

FIXES:

- Fixes erroneous `curl` using `--compress` instead of `--compressed` (https://github.com/autopkg/autopkg/commit/3c8bc23d89e902d9e7f69ff698179f38f36a9a44)
- Redirect from GitHub resulted in two header blocks (https://github.com/autopkg/autopkg/commit/b851d6d5de1bbab2523807c898dbb093d5f9fbcb)
- PkgCopier would incorrectly use the pre-globbed input path if a destination was
  not specified (https://github.com/autopkg/autopkg/commit/02f461cf6f503dfc65151aef5180a882cc6f6f72)

ADDITIONS:
- Preferences can now be provided from an external file using `--prefs`. The input
  file can be either in JSON or plist format, and will be treated identically
  to preferences from macOS. (https://github.com/autopkg/autopkg/commit/7ae2f552535741cb4ee131131d16a1fd93186c14)

IMPROVEMENTS:
- Several unit tests have been added for some core AutoPkg functionality, and
  certain processors.
- All occurrences of `print()` in the core autopkg script were replaced with `log` and `log_err` (https://github.com/autopkg/autopkg/commit/8300b807e29553be92c8c74894090442c8312b6d)
- The groundwork has been laid for running AutoPkg on alternative platforms.
- AutoPkg now uses a pre-commit hook that enforces the use of black, isort, and
  flake8 to ensure code quality. This includes a new CONTRIBUTING guide (https://github.com/autopkg/autopkg/blob/master/CONTRIBUTING.md)

### [1.1RC2](https://github.com/autopkg/autopkg/compare/v1.0.4...v1.1RC2) (May 23, 2019)

FIXES:

- Fix for autopkg output in 1.1RC1 going to stderr instead of stdout (https://github.com/autopkg/autopkg/commit/d67a8888e0bd900f0fba595a1d3d95bbf391d095)
- Add `--compress` option to `curl` calls in SparkleUpdateInfoProvider and URLTextSearcher
  to work around websites that return compressed results even when request does not indicate
  they will be accepted. (GH-461)
- URLDownloader: Better handling of more HTTP 3xx redirects (GH-429)
- Better handling of paths starting with `~/` (GH-437) (https://github.com/autopkg/autopkg/commit/603f2207df3cd88b3a2cb3e59543923648ac6522)
- `generate_processor_docs` sorts the sidebar alphabetically (GH-520)

ADDITIONS:

- New `--force` option for `autopkg make-override` (GH-425)
- Add `-q/--quiet` option to suppress Github search and suggestions (GH-426)
- New `new-recipe` subcommand (https://github.com/autopkg/autopkg/commit/f92a0a46042c14de502379ed7f454e1aa9053db1)
- Added DeprecationWarning processor to core processors (https://github.com/autopkg/autopkg/commit/7b4abac0ce4955689a8af482249963c5253038ae)

IMPROVEMENTS:

- Code run through several processors/formatters (flake8, isort, black, python-modernize) to
  prepare for Python 3 compatibility

### [1.0.4](https://github.com/autopkg/autopkg/compare/v1.0.3...v1.0.4) (March 05, 2018)

FIXES:

- All GitHub API requests are now performed using curl. This fixes TLS errors with
  GitHubReleasesInfoProvider processor and `autopkg search` functionality on macOS 10.12
  and earlier. (GH-408)

IMPROVEMENTS:

- A GitHub token can now be specified in AutoPkg preferences (GITHUB_TOKEN) or in a file: ~/.autopkg_gh_token (Original PR was GH-407, code merged here as part of GH-408: https://github.com/autopkg/autopkg/commit/8e0f19b99ce24311752d1300ed408d90713e144c)
- In parent trust info, store paths within user home as ~/some/path. When verifying
  trust info, expand ~ to current user home directory.
- FlatPkgUnpacker, PkgPayloadUnpacker and PkgRootCreator will now create intermediary
  directories (GH-401)
- URLDownloader and URLTextSearcher now accept `curl_opts` input variable to provide
  additional arguments to curl (GH-384, GH-386)

### [1.0.3](https://github.com/autopkg/autopkg/compare/v1.0.2...v1.0.3) (September 22, 2017)

FIXES:

- Better handling of bundle items in MunkiImporter (GH-352)
- Prevent stack trace when parent recipe does not exist (GH-363)

IMPROVEMENTS:

- DmgCreator now explicitly specifies HFS+ format when creating disk images.
  Avoids an issue where APFS images were created under High Sierra,
  potentially causing issues with machines running older macOS versions.
  (GH-357)
- Improvements to CodeSignatureVerifier (GH-373)
  - Added strict_verification variable to control whether to pass --strict,
    --no-strict or nothing at all to `codesign`.
  - Added deep_verification variable to control whether to pass --deep to
    `codesign` or not. Deep verification was previously on by default (and
    still is) but it can now be explicitly disabled.
  - Added codesign_additional_arguments variable for specifying additional
    arguments for `codesign` tool.
  - Removed the .app file extension checking and no longer require the input to
    be a specific file type. Only check for .pkg, .mpkg or .xip extensions and
    pass those to `pkgutil`, everything else should go to `codesign`.

### [1.0.2](https://github.com/autopkg/autopkg/compare/v1.0.1...v1.0.2) (April 07, 2017)

FIXES:

- Trust info is ignored if it is ever present in a recipe which is not an override,
  and warns if any such trust info is found (GH-334)
- Fix a regression in PlistReader and handling disk images
- PkgCopier can now mount a diskimage in the source path even if its extension is not
  `.dmg` (GH-349)

IMPROVEMENTS:

- If an `autopkg run` has recipes failing due to trust verification failure, this is
  clarified in the output as the reason for the failure.
- URLDownloader now handles file sizes in FTP server responses, avoiding repeated
  downloads from `ftp://` server URLs (GH-338)
- FileFinder can now mount DMG files given as part of its input `pattern` (GH-263)
- When PkgCreator logs `Invalid version`, it now includes the offending version string
  in this output (GH-343)

### [1.0.1](https://github.com/autopkg/autopkg/compare/v1.0.0...v1.0.1) (November 30, 2016)

FIXES:

- Fix a crash when parsing a plaintext `--recipe-list` containing a single item
  (GH-323)

### [1.0.0](https://github.com/autopkg/autopkg/compare/v0.6.1...v1.0.0) (November 16, 2016)

ADDITIONS:

- New `audit` verb, used to output helpful information about any recipes that:
  - Are missing a CodeSignatureVerifier step
  - Use non-HTTP URLs for downloads
  - Supply their own processors and thus will run code not provided by AutoPkg itself
  - Use processors that may potentially be modifying the original software
    downloaded from the vendor
- New `verify-trust-info` and `update-trust-info` verbs. These can be used to
  add "trust" hash information to a recipe override. If a parent recipe and/or
  its processor(s)  is later updated (typically via a third-party recipe repo and
  running `autopkg repo-update` against this or all recipe repos), this
  trust information will be invalid and prevent the recipe from running
  until the trust information has been updated. Running `verify-trust-info` with
  additional verbosity will print out full diffs of upstream changes made since
  the last trust information was recorded, and `update-trust-info` will update
  it to match the current state of parent recipes. This behaviour can be bypassed
  using the `FAIL_RECIPES_WITHOUT_TRUST_INFO` AutoPkg preference. See the
  [wiki article](https://github.com/autopkg/autopkg/wiki/Autopkg-and-recipe-parent-trust-info) for more information.
- New `AppPkgCreator` processor, a single processor replacing the several steps
  previously required for building a package from an application bundle.
- Support for "rich" recipe lists in property list format, which can specify
  pre/post-processors and additional input variables for that specific run. See the
  [Running Multpiple Recipes article](https://github.com/autopkg/autopkg/wiki/Running-Multiple-Recipes) for more details.

FIXES:

- Fix SparkleUpdateInfoProvider ignoring `appcast_request_headers` argument since
  switching from urllib2 to curl. (GH-277)
- Miscellaneous fixes to better handle unicode in `autopkg` message output.
  (GH-299)
- Fix GitHub API error on `autopkg search` for a recipe name containing spaces.
  (GH-305)

IMPROVEMENTS:

- URLDownloader now passes `--fail` option so that most 400-class error codes
  will result in a failed recipe run. (GH-284)
- AutoPkg now reports an exit code of `70` if any recipe in an `autopkg run`
  fails. Eventually other exit codes may later be added to report on other
  specific behavior. (GH-297)
- MunkiImporter now accepts an `uninstaller_pkg_path` input variable, used to
  copy Adobe uninstaller packages and set `uninstaller_item_location` in pkginfos.
- MunkiImporter should now be able to detect existing Adobe CCP-built package
  items in a Munki repo as generated by `makepkginfo` in Munki tools version 2.8.0
  and higher.

### [0.6.1](https://github.com/autopkg/autopkg/compare/v0.6.0...v0.6.1) (March 18, 2016)

FIXES:

- Fix too-restrictive 600 permissions on files downloaded by curl. This caused an issue
  where a file copied to either a local or remote Munki repo may not be readable by the
  webserver. Modes of downloaded files are now set to 644.

### [0.6.0](https://github.com/autopkg/autopkg/compare/v0.5.2...v0.6.0) (March 15, 2016)

CHANGES:

- URLDownloader, URLTextSearcher and SparkleUpdateInfoProvider now all use
  the `/usr/bin/curl` binary for performing HTTP requests. This resolves
  several ongoing issues with Apple's Python urllib2 module and SSL.
  CURLDownloader and CURLTextSearcher processors refer internally to the same
  processors, and recipes using them can be safely switched back to the
  "standard" versions.
  An alternate cURL binary can be specified using the `CURL_PATH` input variable.
- The BrewCaskInfoProvider processor is now deprecated. The [Cask DSL](https://github.com/caskroom/homebrew-cask/tree/master/doc/cask_language_reference) has added
  over time logic for specifying URLs that requires the ability to actually invoke Ruby
  code, and this processor was never widely used. It will remain in AutoPkg for
  some time but will not function with all Cask files.
- CodeSignatureVerifier: the use of `expected_authority_names` to verify .app
  bundles is now deprecated, and will be removed in a future AutoPkg release. Use
  [`requirement`](https://github.com/autopkg/autopkg/wiki/Using-CodeSignatureVerification) instead. (GH-256)


FIXES:

- CodeSignatureVerifier: globbing is performed on all paths, rather than only
  within a disk image path. (GH-252)

IMPROVEMENTS:

- URLDownloader: support for 'CHECK_FILESIZE_ONLY' input variable,
  which skips checks for Last-Modified and ETag headers when checking whether a
  download has changed on the server, and uses only the file size. This is useful
  for recipes that redirect to various mirrors for downloads, where these server
  header values differ, causing repeated downloads. This can be set in a recipe's
  Input section, or like any other variable it can also be altered on the CLI using
  the '--key/-k' option during any given run, for example:
  `autopkg run -k CHECK_FILESIZE_ONLY=true VLC.munki`
    - related issue: (GH-219)
- CodeSignatureVerifier: support for xip archives
- Unarchiver: support for gzip archives

### [0.5.2](https://github.com/autopkg/autopkg/compare/v0.5.1...v0.5.2) (January 13, 2016)

FIXES:

- Fix for curl/CURLDownloader saving zero-byte files. (GH-237)
- Don't prompt to search recipes when running `autopkg run --recipe-list`. (GH-223)
- Fix a regression in 0.5.1 in running .install recipes on OS X 10.9 and earlier.
- Properly handle the case of SparkleUpdateInfoProvider finding no items in an appcast feed. (GH-208)

### [0.5.1](https://github.com/autopkg/autopkg/compare/v0.5.0...v0.5.1) (September 02, 2015)

ADDITIONS:

- New processor, PackageRequired. Can be added to recipes that require a --pkg
  argument (or `PKG` variable), where a public .download recipe is not feasible. (GH-207)
- New proof-of-concept processors CURLDownloader and CURLTextSearcher, drop-in
  replacements for URLDownloader and URLTextSearcher which use cURL instead of
  Python urllib2. Can be used to mitigate issues with SSL and the system Python.

IMPROVEMENTS:

- PathDeleter: Guard against the mistake of `path_list` being a single string instead
  of a list of strings. (GH-200)
- Compatibility fixes in packaging and install daemons for future OS X releases.
- `MUNKI_PKGINFO_FILE_EXTENSION` default variable can now be an empty string to
  eliminate a pkginfo file extension altogether. (GH-212)
- MunkiImporter: When attempting to match previous versions of existing items, check `bundle`
  `installs` types in addition to well as `application` types. (GH-216)
- PkgCreator: Previously, in `pkg_request`'s `chown` dict, if an absolute path was
  given in `path`, that literal path would be used rather than relative to the pkg
  root. Now, if an absolute path is given, it will still be properly joined to the
  pkg root. (GH-220)
- Fix issue where an unhandled exception in any recipe processor would halt the entire
  AutoPkg run and Python would abort with a traceback. The output of `--report-plist`
  now stores the relevant traceback within `failures` item dicts. (GH-147)

FIXES:

- URLDownloader: Fix issue where URL has updated ETag/Last-Modified but a matching
  filesize, and would not continue downloading the new file. (GH-219)

### [0.5.0](https://github.com/autopkg/autopkg/compare/v0.4.2...v0.5.0) (July 17, 2015)

BREAKING CHANGES:

- The structure of a plist output by `--report-plist` has changed to reflect the
  structure of the summary results described below in ADDITIONS. (GH-163)

ADDITIONS:

- New processor, GitHubReleasesInfoProvider. Used to fetch download URLs and metadata about
  releases posted on GitHub.
- `autopkg run` interactively offers suggestions for similar recipe names when a recipe can't
  be found, and also offers to search for the desired recipe on GitHub.
- New `install` verb. `autopkg install Firefox` is equivalent to `autopkg run Firefox.install`
- Processors may now define their own summary reporting data. Previously AutoPkg provided
  summary data only for several known, core processors like URLDownloader, PkgCreator, etc.
  Now AutoPkg will print out data provided within a dict value of an env key ending in
  `_summary_result` (see [Processor Summary Reporting](https://github.com/autopkg/autopkg/wiki/Processor-Summary-Reporting) on the AutoPkg wiki). (GH-163)

IMPROVEMENTS:

- SparkleUpdateInfoProvider now sets the `version` key based on what feed item it has
  processed. This key can be used in later steps of the recipe. (GH-166)
- AutoPkg now warns against being run as root.
- Use of new launchd 2.0 socket API is used by autopkgserver if running on Yosemite or
  higher. (GH-176)
- URLDownloader is now able to decompress gzip-encoded content. (GH-184)
- FileCreator now supports optional `file_mode` input variable.
- SparkleUpdateInfoProvider processor is now skipped early if `--pkg` argument is given
  to `autopkg run`, similar to URLDownloader.

FIXES:

- Fixes in MunkiImporter's logic when attempting to locate a matching item in a repo.
- PkgCreator: fix an exception when setting `mode` on a direcotry (in `chown`, in
  `pkg_request`). (GH-177)
- BrewCaskInfoProvider now properly interpolates '#{version}' within 'url' strings.

### [0.4.2](https://github.com/autopkg/autopkg/compare/v0.4.1...v0.4.2) (December 12, 2014)

ADDITIONS:

- Support for adding pre- and postprocessors via the `--preprocessor/--pre` and
  `--post/--postprocessor` options to `autopkg run`. See the
  [new wiki page](https://github.com/autopkg/autopkg/wiki/PreAndPostProcessorSupport)
  for more details. (GH-108)

IMPROVEMENTS:

- CodeSignatureVerifier: support for 'DISABLE_CODE_SIGNATURE_VERIFICATION' input variable,
  which when set (to anything) will skip any verification performed by this processor. One
  would define this using the '--key' option for a run, or using a defaults preference.
  (GH-131)
- new `list-recipes` command options for more detailed listings. Listings can now include
  identifiers, recipe paths, and can be output in a parsable plist format. (GH-135)

### [0.4.1](https://github.com/autopkg/autopkg/compare/v0.4.0...v0.4.1) (October 20, 2014)

IMPROVEMENTS:

- CodeSignatureVerifier: support for 'requirement' input variable for defining an expected
  requirement string in a binary or bundle. See Apple TN2206 for more details on code
  signing. (GH-114)
- CodeSignatureVerifier: use the '--deep' option for verify, when running on 10.9.5 or greater.
  (GH-124, GH-125)

### [0.4.0](https://github.com/autopkg/autopkg/compare/v0.3.2...v0.4.0) (August 29, 2014)

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

### [0.3.2](https://github.com/autopkg/autopkg/compare/v0.3.1...v0.3.2) (July 24, 2014)

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

### [0.3.1](https://github.com/autopkg/autopkg/compare/v0.3.0...v0.3.1) (July 01, 2014)

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

### [0.3.0](https://github.com/autopkg/autopkg/compare/v0.2.9...v0.3.0) (May 20, 2014)

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

### [0.2.9](https://github.com/autopkg/autopkg/compare/v0.2.8...v0.2.9) (February 28, 2014)

ADDITIONS:

- New FileMover processor, contributed by Jesse Peterson. (GH-64)
- New URLTextSearcher processor, contributed by Jesse Peterson. (GH-64)

### [0.2.8](https://github.com/autopkg/autopkg/compare/v0.2.7...v0.2.8) (January 08, 2014)

FIXES:
- New package release to fix issue with autopkgsever launch daemon plist in 0.2.6 and 0.2.7 package releases.

### [0.2.7](https://github.com/autopkg/autopkg/compare/v0.2.6...v0.2.7) (January 08, 2014)

FIXES:

- Fix unhandled exception when FoundationPlist encounters a malformed plist
- Fix long string wrapping in several Processor's descriptions and input/output variable descriptions. This caused `autopkg processor-info foo` to fail for several Processors.

### [0.2.6](https://github.com/autopkg/autopkg/compare/v0.2.5...v0.2.6) (January 06, 2014)

FIXES:

- Fix for FoundationPlist functions under Snow Leopard. Changes to FoundationPlist in 0.2.5 broke autopkg under Snow Leopard; these changes remedy that.

### [0.2.5](https://github.com/autopkg/autopkg/compare/v0.2.4...v0.2.5) (January 04, 2014)

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

### [0.2.4](https://github.com/autopkg/autopkg/compare/v0.2.3...v0.2.4) (October 16, 2013)

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

### [0.2.3](https://github.com/autopkg/autopkg/compare/v0.2.2...v0.2.3) (September 27, 2013)

ADDITIONS:

- New 'FileFinder' processor for searching files, currently supports glob.
  Contributed by Jesse Peterson. (GH-33)

FIXES:

- Fix `autopkg info` showing a Description of a ParentRecipe instead of the actual recipe.
- Fix TypeError on Snow Leopard on list concatenation between Foundation and native Python list equivalents (GH-21)
- Fix case where a child recipe could not locate its parent(s) if the child was not already on the search path (GH-25)

### [0.2.2](https://github.com/autopkg/autopkg/compare/v0.2.1...v0.2.2) (September 10, 2013)

CHANGES:

- Pkg recipe runs now print a report output similar to Munki recipes, and have version, identifier information available in the report.
- Fix for `autopkg version` when run from /usr/local/bin/autopkg

### [0.2.1](https://github.com/autopkg/autopkg/compare/v0.2.0...v0.2.1) (September 2, 2013)

CHANGES:

- Relative paths given for "infofile", "resources", "options", "scripts" in a PkgCreator's pkg_request dictionary should now work if this path is found at the current working directory (GH-20)

### [0.2.0](https://github.com/autopkg/autopkg/compare/v0.1.1...v0.2.0) (September 1, 2013)

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

### [0.1.1](https://github.com/autopkg/autopkg/compare/v0.1.0...v0.1.1) (August 27, 2013)

CHANGES:

  - Addresses an issue where creating RecipeOverrides failed if the recipe overrides directory (default: ~/Library/AutoPkg/ReceipeOverrides) is missing

### 0.1.0 (August 23, 2013)

FEATURES:

  - Initial pkg release.
