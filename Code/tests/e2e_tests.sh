#!/bin/bash

echo "**Help:"
../Code/autopkg help
echo "**List-processors:"
../Code/autopkg list-processors --prefs tests/preferences.plist
echo "**Processor-info:"
../Code/autopkg processor-info URLDownloader --prefs tests/preferences.plist
echo "**Repo-add:"
../Code/autopkg repo-add recipes --prefs tests/preferences.plist
echo "**Info:"
../Code/autopkg info Firefox.munki --prefs tests/preferences.plist
echo "**Repo-list:"
../Code/autopkg repo-list --prefs tests/preferences.plist
echo "**Repo-update:"
../Code/autopkg repo-update all --prefs tests/preferences.plist
echo "**Audit:"
../Code/autopkg audit Firefox.munki --prefs tests/preferences.plist
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
