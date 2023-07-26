### [2.8.0](https://github.com/autopkg/autopkg/compare/v2.7.2...HEAD) (Unreleased)

New features:
* The recipe map branch has now been merged in. This means that AutoPkg will build a recipe map (JSON on disk) of all repos and recipes when you add or delete repos, and use that for searching for recipes. This drastically speeds up recipe search, especially if you have lots of repos checked out. The old on-disk search method is a fallback, but will be removed in the future.
* The recipe map feature was merged in after a long hiatus, and I can't currently guarantee everything was merged correctly. Please test this and let us know if there are any problems or bugs.
* MunkiImporter now creates pkginfo files with a supported architecture in the filename if and only if there is exactly one supported architecture (i.e. "SomePackage-1.0.0-x86_64.pkginfo"). This will make it much easier to distinguish multiple architecture pkginfos for the same package. A similar PR was merged for Munki (https://github.com/munki/munki/pull/1185).

Fixes:
* Error handling in URLDownloader to address some curl issues (https://github.com/autopkg/autopkg/pull/850)
* Fixes for URLDownloaderPython (https://github.com/autopkg/autopkg/pull/854)
* Indenting blocks in YAML to match spec (https://github.com/autopkg/autopkg/pull/861)
* PkgCopier now only allows copying of .pkg / .mpkg files (https://github.com/autopkg/autopkg/pull/864)

### [2.7.2](https://github.com/autopkg/autopkg/compare/v2.7.1...v2.7.2) (December 07, 2022)

* Fix for SparkleUpdateInfoProvider. (https://github.com/autopkg/autopkg/pull/845)

**Full Changelog**: https://github.com/autopkg/autopkg/compare/v2.71..v2.7.2

### [2.7.1](https://github.com/autopkg/autopkg/compare/v2.7.1...v2.7.1) (December 06, 2022)

* GitHubReleasesInfoProvider -- add support for a "latest_only" input variable (https://github.com/autopkg/autopkg/pull/846)
* GitHubReleasesInfoProvider -- add "asset_created_at" output variable
* PkgPayloadUnpacker -- use "aa" to expand archives if "ditto" fails and "aa" is available (https://github.com/autopkg/autopkg/pull/804)
* Fix for plist serialization when json input contains null values (https://github.com/autopkg/autopkg/pull/810)
* SparkleUpdateInfoProvider -- add support for channels (https://github.com/autopkg/autopkg/commit/716dcea47237ec8895617c374bfa67a329a7188c)
* Fix for autopkginstalld on recent versions of macOS. Fixes .install recipes. (https://github.com/autopkg/autopkg/pull/838)

**Full Changelog**: https://github.com/autopkg/autopkg/compare/v2.7..v2.7.1

### [2.7.0](https://github.com/autopkg/autopkg/compare/v2.6.0...v2.7) (August 22, 2022)

## Python 3.10.6
AutoPkg now uses Python 3.10.6, and PyObjc 8.5. Python 3.10 brings several new general improvements and may result in some warnings or errors in processors still using some legacy Python2-conversion-to-3-isms. Please file appropriate issues with recipe authors or bring it to our attention in #autopkg in Slack.

## Automated tests on GitHub
Thanks to the incredible work by @jgstew, AutoPkg now has automatic unit tests and a test recipe being run as an automatic GitHub action! This will help provide confidence in AutoPkg's functionality, and empowers contributors to be more confident in testing their code. Here's hoping this opens up more more people interested in contributing!

Similarly, thanks to @homebysix for doing a similar action for linting, ensuring consistent Python style rules are being applied.

## Other Changes
* the make_new_release script is a lot easier to use (only really benefits maintainers, but hey)
* remove incompatibility notice non-macs by @jgstew in https://github.com/autopkg/autopkg/pull/795
* add automated UnitTests for AutoPkg with GitHub Actions by @jgstew in https://github.com/autopkg/autopkg/pull/796
* Create linting/auto-formatting workflow in GH Actions by @homebysix in https://github.com/autopkg/autopkg/pull/793
* Always return list when finding matching pkgs by @octomike in https://github.com/autopkg/autopkg/pull/794
* Preserve YAML scalar types when writing YAML to disk by @bfreezy in https://github.com/autopkg/autopkg/pull/770
* MunkiInstallsItemsCreator.py - Add option to derive minimum os version by @macmule in https://github.com/autopkg/autopkg/pull/801
* Update tests.yaml - remove bad schedule by @jgstew in https://github.com/autopkg/autopkg/pull/815
* Fix URLGetter.py when default windows curl is used. by @jgstew in https://github.com/autopkg/autopkg/pull/816

**Full Changelog**: https://github.com/autopkg/autopkg/compare/v2.7.0...v2.5

### [2.3.1](https://github.com/autopkg/autopkg/compare/v2.3...v2.3.1) (March 03, 2021)

FIXES:

- Resolved a bug preventing `autopkg repo-update` and `autopkg repo-delete` operations on local file paths ([#724](https://github.com/autopkg/autopkg/issues/724); fixes [#723](https://github.com/autopkg/autopkg/issues/723) and [lindegroup/autopkgr#666](https://github.com/lindegroup/autopkgr/issues/666))

### [2.3](https://github.com/autopkg/autopkg/compare/v2.2...v2.3) (March 01, 2021)

NEW FEATURES:

AutoPkg now supports recipes in [yaml](https://yaml.org/) format ([#698](https://github.com/autopkg/autopkg/pull/698), [example recipe](https://github.com/autopkg/autopkg/pull/698#issuecomment-783522503)). Yaml recipes tend to be more human-readable than plist recipes, especially for those who don't work with plists on a daily basis.

AutoPkg can produce new recipes in yaml format using `autopkg new-recipe SomeCoolApp.pkg.recipe.yaml` and make overrides in yaml format using `autopkg make-override --format=yaml SomeCoolApp.pkg`. Searching for public yaml recipes on GitHub is also possible using `autopkg search`.

NOTES FOR RECIPE AUTHORS:

- Because yaml recipes will require AutoPkg 2.3 or later in order to run, and because some members of the AutoPkg community may still be using AutoPkg 1.x, recipe authors are encouraged to be conservative and keep existing public recipes in their current format for a while.
- If you have both plist and yaml recipes for the same app in your repo, you may experience unexpected behavior now that AutoPkg detects and uses yaml recipes.

OTHER CHANGES FROM 2.2:

- Added support for internal GitHub URLs ([#649](https://github.com/autopkg/autopkg/pull/649))
- `autopkg make-override` no longer creates override for deprecated recipes by default ([#685](https://github.com/autopkg/autopkg/pull/685))
- Typo fixed in the recipe template created by `autopkg new-recipe`
- Fixed a bug causing `autopkg repo-add` and `autopkg repo-delete` to fail for repos in GitHub organizations with non-alphanumeric characters in their names ([#712](https://github.com/autopkg/autopkg/issues/712), [#715](https://github.com/autopkg/autopkg/pull/715))
- CodeSignatureVerifier warns when certain incorrect input variables are detected
- MunkiImporter now uses consistent pkginfo matching logic ([#671](https://github.com/autopkg/autopkg/pull/671))
- Minor edits to help text
- Improvements to Versioner processor ([#600](https://github.com/autopkg/autopkg/pull/600))
- Help is now shown for `autopkg list-processors --help`, matching behavior of most other verbs ([#717](https://github.com/autopkg/autopkg/pull/717))
- The output of `autopkg list-recipes --plist` is now text instead of binary (this matches previous behavior in AutoPkg 1.x)
- More output when using `autopkg repo-add` and `autopkg repo-delete` ([#704](https://github.com/autopkg/autopkg/pull/704))
- Fixed a bug in MunkiImporter that caused incorrect `uninstaller_item_location` path ([#702](https://github.com/autopkg/autopkg/pull/702))
- Building a foundation for long term expansion of platform support ([#648](https://github.com/autopkg/autopkg/pull/648), [#651](https://github.com/autopkg/autopkg/pull/651), [#653](https://github.com/autopkg/autopkg/pull/653), [#656](https://github.com/autopkg/autopkg/pull/656), [#658](https://github.com/autopkg/autopkg/pull/658), [#666](https://github.com/autopkg/autopkg/pull/666), [#670](https://github.com/autopkg/autopkg/pull/670))

KNOWN ISSUES:

- [#710](https://github.com/autopkg/autopkg/issues/710) is currently affecting some `autopkg search` results (regardless of whether the recipes are plist or yaml)

### [2.2](https://github.com/autopkg/autopkg/compare/v2.1...v2.2) (August 24, 2020)

NEW FEATURES
MunkiImporter now supports Munki repo plugins, thanks to @tboyko. The default behavior
is still to use FileRepo as the default local behavior, so existing behavior is
unchanged. (https://github.com/autopkg/autopkg/pull/654)


CHANGES FROM 2.1:
- URLDownloader handles Content-Disposition filenames with quotes correctly (https://github.com/autopkg/autopkg/pull/633)
- README and CONTRIBUTING guides updated with correct Python 3 framework info (https://github.com/autopkg/autopkg/pull/638)
- PyYAML updated to 5.3.1 to address PyYAML-CVE-2020-1747 (https://github.com/autopkg/autopkg/pull/642)
- Internal autopkg code structure is being shifted, with more code moving into separate
  shared modules. Lots of various lint fixes, formatting, and safety handling improvements.
- GitHub API queries no longer fail when searching for recipes with spaces in the name,
  and are now quoted correctly (https://github.com/autopkg/autopkg/pull/664)
- Processor subclasses now automatically configure an empty dictionary for `self.env` if
  none is provided. This doesn't have any practical effect, but makes it easier to create
  and use new Processor subclasses in the future.

### [2.1](https://github.com/autopkg/autopkg/compare/v2.0.2...v2.1) (May 19, 2020)

NEW FEATURES
AutoPkg now supports the verbs `list-repos` and `processor-list` for convenience (https://github.com/autopkg/autopkg/pull/628)

`autopkg info --pull`/`-p` now allows you to fetch all parent repos of a recipe
automatically.

Example:
```
$ autopkg repo-delete recipes
$ autopkg info -p GoogleChrome.munki
Didn't find a recipe for com.github.autopkg.munki.google-chrome.
Found this recipe in repository: recipes
Attempting git clone...

Adding /Users/nmcspadden/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes to RECIPE_SEARCH_DIRS...
Updated search path:
  '.'
  '~/Library/AutoPkg/Recipes'
  '/Library/AutoPkg/Recipes'
  '/Users/nmcspadden/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes'

Description:         Downloads the latest Google Chrome disk image and imports into Munki.
Identifier:          local.munki.GoogleChrome
Munki import recipe: True
Has check phase:     True
Builds package:      False
Recipe file path:    /Users/nmcspadden/Library/AutoPkg/RecipeOverrides/GoogleChrome.munki.recipe
Parent recipe(s):    /Users/nmcspadden/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes/GoogleChrome/GoogleChrome.munki.recipe
                     /Users/nmcspadden/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes/GoogleChrome/GoogleChrome.download.recipe
```

The automatic fetching works by looking at the parent identifier of a recipe, and
searching GitHub via API for that file. It fetches that parent file from GitHub
directly, and adds the repo that it belongs to. Then it parses its parent, recursively
until it finds a recipe with no parents.

Note that the only verb to support this is `autopkg info`. You can use this feature to
dynamically fetch parents on-demand, instead of preconfiguring your environment with a
list of known repos.

CHANGES FROM 2.0.2:
- URLGetter can handle parsing headers without an explicit `url` in the environment (https://github.com/autopkg/autopkg/pull/605)
- FileCreator now has a unit test (https://github.com/autopkg/autopkg/pull/591)
- AutoPkg warns you more helpfully if you are trying to run it with Python 2 (https://github.com/autopkg/autopkg/pull/610)
- If a recipe generates a Python stacktrace, the traceback output is only provided with verbosity > 2 (https://github.com/autopkg/autopkg/pull/609)
- CodeSignatureVerifier warns you if you attempt to use the deprecated `expected_authorities` argument (https://github.com/autopkg/autopkg/commit/1a3481f1ff9a992ace27dc8d301e1ef3e86c691d)
- Installing packages with AutoPkg .install recipes should no longer generate warnings about failing to close the socket (https://github.com/autopkg/autopkg/commit/09a5f5c2d6f5aaa9dd2963b722ced6f4915b60f1)
- Updated AppDmgVersioner's description to clarify its limitations (https://github.com/autopkg/autopkg/commit/ababfd363171f47840c73409824bb34ee879241e)
- Processors can now be run standalone again by accepting variables from a plist read from stdin (https://github.com/autopkg/autopkg/pull/621)
- FileFinder handles recursive searching correctly (https://github.com/autopkg/autopkg/pull/622)
- URLGetter has better error handling (https://github.com/autopkg/autopkg/pull/629)
- Fetching a filename with URLGetter now works more reliably (https://github.com/autopkg/autopkg/commit/6d2b9410a05e73f52fce8c84834a54c3ae206f20)

### [2.0.2](https://github.com/autopkg/autopkg/compare/v2.0.1...v2.0.2) (February 05, 2020)

CHANGES FROM RC2:
- Fixed an encoding bug in the make_new_release script (https://github.com/autopkg/autopkg/commit/fca40526a3a19f3e208574be775fa7309244c0d5)
- Removed some orphaned dead code (https://github.com/autopkg/autopkg/commit/c90e92b1988f347834ed4957cc9108c2b1eef44b)

### [2.0 RC2](https://github.com/autopkg/autopkg/compare/2.0b3...v2.0.1) (January 31, 2020)

CHANGES FROM RC1:
- Fixed some processor docs (https://github.com/autopkg/autopkg/commit/3812ca12a44531c78c869e67fbbd84d7706b8a93)
- Added in "APLooseVersion", loosely based on Munki's version comparison, to replace previous version comparison semantics. (https://github.com/autopkg/autopkg/commit/7c0676fdfe77f66f261b0df53ec5a792d31c5d3c)
  - This MAY cause a change in behavior for some current version comparisons, but it no longer crashes when comparing
    certain combinations of strings.

### [2.0 RC1](https://github.com/autopkg/autopkg/compare/2.0b3...v2.0.1) (December 03, 2019)

CHANGES FROM BETA 3:
- Some fixes around URLGetter's behavior and callsites
- `URLGetter.execute_curl()` was changed to use `subprocess.run()` instead of `Popen` (https://github.com/autopkg/autopkg/commit/facad8ce48cfb9766578d55823660feb177b3e80)
- Update URLDownloader variable descriptions to show up better on the wiki (https://github.com/autopkg/autopkg/commit/079c606778a3a4795cd52e4f98a77f5479b36ea9)
- URLGetter outputs the entire curl command when used with `-vvvv` verbosity (https://github.com/autopkg/autopkg/commit/7c24a05fd327d77f082875aaa70549f48d156802)
- URLGetter now has a convenient `download_to_file(url, filename)` function, which makes
it simple to download a file in a custom processor (this was backported to 1.4.1) (https://github.com/autopkg/autopkg/commit/2fac6955a124f268c96ff71a7d433da84242e6fb)
- Fixed an extraneous socket close error in InstallFromDmg (hat tip to Allister B) (https://github.com/autopkg/autopkg/commit/c31789f8fe32e2f75167b5790e5a353c24904a76)
- make_new_release.py produces more friendly console output indicating what stage it's on (https://github.com/autopkg/autopkg/commit/1373b31d407b1a2ae023256aa2d65ef165d5956)

### [2.0b3](https://github.com/autopkg/autopkg/compare/12249273c23e9c52675ab947024c2ac505080049...2.0b3) (November 25, 2019)
CHANGES FROM BETA 2:

- Thanks to @MichalMMac's heroic efforts, URLGetter is now much easier for other processors to use. There are now two ways a custom processor can download things without needing to write any urllib logic:
  - `URLGetter.download_with_curl(curl_command, text=True)` takes a curl command as an argument (a list of strings that is passed to subprocess). You can use this along with the other helper functions to arrange your own curl command with custom headers and arguments, and parse the output.
  - `URLGetter.download(url, headers=None, text=False)` takes a URL (and optional headers) and returns the output of the curl command. You can use this to simply retrieve the results of requesting a web page (such as for URLTextSearcher).
- In both cases, you can pass text mode to determine if you get straight text output.
- All custom processors that need to make a web request of any kind in autopkg/recipes have been switched to using URLGetter's methods. No more urllib in processors!
- Some minor formatting changes in the code itself
- DmgMounter now handles APFS disk images (with SLAs/EULAs) (https://github.com/autopkg/autopkg/commit/4b77f6d5948a2f36258f4695f503513ec7671745)

CHANGES FROM BETA 1:

- The new URLGetter base Processor class has been merged in. It provides a new centralized way to handle fetching and downloading things from the web. In the future, more convenience functions will be added to allow any custom processor to easily fetch web resources without having to write their own urllib/web-handling code.
- Failing to import a processor due to a Python syntax error (such as due to py2 vs. py3 imports) now has a more specific and clear error message (e52ae69)
- Many, many, many bytes vs. string issues resolved in core processors
- Copier now has a unit test, and produces some more useful output
- autopkgserver shouldn't complain about socket descriptors anymore
- isort now has a seed config that explicitly lists certain third party modules so that they're sorted at the top or bottom of import blocks correctly
- All custom processors in autopkg-recipes now use certifi to set the base SSL certs so that urllib web requests work; this will be removed in the future once URLGetter's convenience functions are written

CHANGES IN INITIAL 2.0 RELEASE:

- FoundationPlist has been retired. plistlib in Python 3 should be used to handle all plist parsing.
- All Python string interpolation should prefer the use of f-strings (formatted string literals).
- All references to unicode vs. string types have been refactored to use Python 3's native byte strings whenever possible.
- All unit tests were updated to Python 3.
- All Python code now use a hardcoded path to the embedded Python framework. This path may change at a later time to incorporate a symlink, for easier cross-platform compatibility.

KNOWN ISSUES:

- There are likely still edge cases in the autopkg/recipes that slipped through testing, so please file issues if you find recipes that don't work as intended.


### [2.0b1](https://github.com/autopkg/autopkg/compare/AutoPkg_1.x...12249273c23e9c52675ab947024c2ac505080049) (November 06, 2019)

PYTHON 3

This is the first beta release of a Python 3-only version of AutoPkg. It is *no longer
compatible with Python 2*, and will indeed encounter syntax errors and failures if ran
with Python 2.

The release package has an included Python 3 framework that includes all necessary
modules to run everything in AutoPkg core, and all of the recipes in autopkg-recipes.

Aside from being a rewrite of the code, this release is feature-identical with release
1.3.1.

MAJOR HIGHLIGHTS OF THE PYTHON 3 CODE:

- FoundationPlist has been retired. plistlib in Python 3 should be used to handle all
  plist parsing.
- All Python string interpolation should prefer the use of f-strings (formatted string
  literals).
- All references to unicode vs. string types have been refactored to use Python 3's
  native byte strings whenever possible.
- All unit tests were updated to Python 3.
- All Python code now use a hardcoded path to the embedded Python framework. This path
  may change at a later time to incorporate a symlink, for easier cross-platform
  compatibility.

KNOWN ISSUES:

- Due to the change in the embedded Python framework, AutoPkg no longer works on other
  platforms without calling the interpreter directly.
- Using a Python-3 only AutoPkg with Python-2 custom processors in recipes outside of
  the core autopkg-recipes repo are not guaranteed to work, and are most likely going to
  fail hard. There will be a long path to updating all of these.
- The JSS Importer is almost certainly not going to work until it's also updated.

HOW TO USE THIS BETA RELEASE:

Installing the release package will get you everything you need to run AutoPkg 2.0.

However, the autopkg-recipes repo itself also has [a separate branch where all of the
custom processors have been converted to Python 3](https://github.com/autopkg/recipes/tree/py2-to-3).
In order to run any of the core recipes, you will need to switch to this branch.

To do so, use the command line to checkout the correct branch:

```
cd ~/Library/AutoPkg/RecipeRepos/com.github.autopkg.recipes
git checkout py2-to-3
```

Then you should be able to run recipes as normal. You will need to update your trust
info as nearly every custom processor has changed:
```
autopkg update-trust-info Firefox.munki
autopkg update-trust-info MakeCatalogs.munki
autopkg run -vv Firefox.munki MakeCatalogs.munki
```

HOW TO REPORT ISSUES:
Use the "Beta Bug report" GitHub issue template to specifically label the issue as being
beta only. Please make use of the template to convey all information possible in order
to reproduce or diagnose the issue as clearly as possible.

SETTING UP AUTOPKG MANUALLY:
If you do not want to use the AutoPkg release installer, you can manually set up an
AutoPkg 2.0 environment. Setup and place the AutoPkg files as you normally would:

- Create /Library/AutoPkg/
- Copy the contents of Code into /Library/AutoPkg/
- Ensure correct file modes for the autopkgserver components:
  `sudo chmod -R 755 /Library/AutoPkg/autopkgserver/`

Build a relocatable python bundle:
- Use the CONTRIBUTING guide's instructions on building a relocatable python bundle
  that uses the `requirements.txt` file for pip
- Move/copy the bundle into /Library/AutoPkg/Python3/Python.framework

### [1.4.1](https://github.com/autopkg/autopkg/compare/v1.4...v1.4.1) (December 02, 2019)

FIXES:
* URLGetter now has a `download_to_file(url, filename)` function that can be used in
custom processors. It simply downloads a URL to a specific filename, and raises a
ProcessorError if it fails for any reason.

### [1.4](https://github.com/autopkg/autopkg/compare/v1.3.1...v2.0.1) (December 03, 2019)

FIXES:
  * DmgMounter now correctly handles APFS disk images, especially with EULAs/SLAs (https://github.com/autopkg/autopkg/commit/4b77f6d5948a2f36258f4695f503513ec7671745)

ADDITIONS:
* The new URLGetter base Processor class has been merged in. It provides a new centralized way to handle fetching and downloading things from the web. In the future, more convenience functions will be added to allow any custom processor to easily fetch web resources without having to write their own urllib/web-handling code.
* Thanks to @MichalMMac's heroic efforts, URLGetter is now much easier for other processors to use. There are now two ways a custom processor can download things without needing to write any urllib logic:
  * `URLGetter.download_with_curl(curl_command, text=True)` takes a curl command as an argument (a list of strings that is passed to subprocess). You can use this along with the other helper functions to arrange your own curl command with custom headers and arguments, and parse the output.
  * `URLGetter.download(url, headers=None, text=False)` takes a URL (and optional headers) and returns the output of the curl command. You can use this to simply retrieve the results of requesting a web page (such as for URLTextSearcher).
* In both cases, you can pass text mode to determine if you get straight text output.
* All custom processors that need to make a web request of any kind in autopkg/recipes have been switched to using URLGetter's methods. No more urllib in processors!

### [1.3.1](https://github.com/autopkg/autopkg/compare/v1.3...v1.4) (November 06, 2019)

FIXES:

- Nested data structures in preferences, such as with JSS_REPOS, should no longer
  cause AutoPkg to fail (https://github.com/autopkg/autopkg/commit/1aff762d8ea658b3fca8ac693f3bf13e8baf8778)

### [1.3](https://github.com/autopkg/autopkg/compare/v1.2...v1.3) (November 04, 2019)

FIXES:

- `autopkg repo-list` wasn't respecting the `--prefs` option correctly (https://github.com/autopkg/autopkg/commit/ec7222335f7a0a191c8c7664ab81de477292f8b7)
- `autopkg list-recipes` wasn't parsing the arguments correctly when used with `--prefs` (https://github.com/autopkg/autopkg/commit/8b15b7305cf9ef32310c6bc3728bf83fd06a4aee)
- Reading in an integer value from macOS preferences and writing it out to disk was
  using incorrect formatting due to a mismatch between plistlib, FoundationPlist, and
  PyObjc data types, which caused MakeCatalogs.munki to fail. Now uses Python primitive
  types instead (https://github.com/autopkg/autopkg/commit/8b15b7305cf9ef32310c6bc3728bf83fd06a4aee)

### [1.2](https://github.com/autopkg/autopkg/compare/v1.1...1.2) (September 16, 2019)

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
