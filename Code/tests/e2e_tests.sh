#!/bin/bash
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

echo "**Help:"
../Code/autopkg help
echo "**List-processors:"
../Code/autopkg list-processors --prefs tests/preferences.plist
echo "**Processor-info:"
../Code/autopkg processor-info URLDownloader --prefs tests/preferences.plist
echo "**Repo-add:"
../Code/autopkg repo-add recipes --prefs tests/preferences.plist
echo "**Repo-list:"
../Code/autopkg repo-list --prefs tests/preferences.plist
echo "**Repo-update:"
../Code/autopkg repo-update all --prefs tests/preferences.plist
echo "**Audit:"
../Code/autopkg audit Firefox.munki --prefs tests/preferences.plist
echo "**Info:"
../Code/autopkg info Firefox.munki --prefs tests/preferences.plist
echo "**List-recipes:"
../Code/autopkg list-recipes --prefs tests/preferences.plist
echo "**Make-override:"
../Code/autopkg make-override Firefox.munki --force --prefs tests/preferences.plist
echo "**New-recipe:"
../Code/autopkg new-recipe TestRecipe.check --prefs tests/preferences.plist
echo "**Search:"
../Code/autopkg search Firefox --prefs tests/preferences.plist
echo "**Verify-trust-info:"
../Code/autopkg verify-trust-info Firefox.munki --prefs tests/preferences.plist
echo "**Update-trust-info:"
../Code/autopkg update-trust-info Firefox.munki --prefs tests/preferences.plist
echo "**Version:"
../Code/autopkg version
echo "**Run:"
../Code/autopkg run -vv Firefox.munki --prefs tests/preferences.plist
echo "**Run many:"
../Code/autopkg run -vv Firefox.munki AdobeFlashPlayer.munki MakeCatalogs.munki --prefs tests/preferences.plist
echo "**Install:"
../Code/autopkg install Firefox -vv --prefs tests/preferences.plist
echo "**Repo-delete:"
../Code/autopkg repo-delete recipes --prefs tests/preferences.plist
