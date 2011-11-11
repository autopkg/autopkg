AutoPkg
=======

AutoPkg is a system for automatically preparing software for distribution to
managed clients. Recipes allow you to specify a series of simple actions which
combined together can perform complex tasks, similar to Automator workflows or
Unix pipes.


Installation
------------

    sudo ./install.sh

Set MUNKI_REPO in ~/Library/Preferences/com.googlecode.autopkg.plist to use
munki recipes (XML format only for now).


Usage
-----

    autopkg recipe.plist


Todo:
-----

* Logging and progress display.
* Receipts should include all output messages.
* The recipe directory should be appended to sys.path so Processors can be
  imported from it.
* Implement pkg options.
* Add MunkiInfoInstallsCreator.
* Add --scripts to packagemaker.
* Create an installer package for AutoPkg.
* Chown when creating package roots shouldn't always be recursive.
* Use Foundation to read plists instead of plistlib.

Done:
-----
* Processors should have manifests with:
    * Purpose and basic help.
    * Required and optional variables.
    * Modified variables.
* Config file.
* A receipt should be saved.
* Add PkgRootCreator.
* Change autopkghelper to use unix domain sockets.
* Packaging shouldn't fail if the target pkg exists.
* Packaging shouldn't leave a temporary pkg behind if it fails.
* Create launchd job for autopkgserver.
* Add PkgInfoCreator.
* Add PkgCreator.
* Fix lib/__init__.py.
* Add RECIPE_DIR variable.
* autopkgserver authentication can't use /tmp as the gid is always 0.
* Flat packages end up with tempdir as the title and choice name in
  Distribution.
* Handle relative paths in recipes and variables.
* Copier should allow .dmg in the path and transparently mount them.
* Add Unzipper.
* Add DmgCreator.
* Add VLCURLProvider.
* Add PackageInfo creation for flat packages.


License
-------

Copyright 2010 Per Olofsson

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
