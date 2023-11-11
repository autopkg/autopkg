#!/bin/bash


platform=$(python -c "import platform; print(platform.system())")

echo "**Help:"
poetry run autopkg help

set -e

echo "**List-processors:"
poetry run autopkg list-processors --prefs tests/preferences.plist
echo "**Processor-info:"
poetry run autopkg processor-info URLDownloader --prefs tests/preferences.plist
echo "**Repo-add:"
poetry run autopkg repo-add recipes --prefs tests/preferences.plist
echo "**Repo-list:"
poetry run autopkg repo-list --prefs tests/preferences.plist
echo "**Repo-update:"
poetry run autopkg repo-update all --prefs tests/preferences.plist
echo "**Audit:"
poetry run autopkg audit Firefox.munki --prefs tests/preferences.plist
echo "**Info:"
poetry run autopkg info Firefox.munki --prefs tests/preferences.plist
echo "**List-recipes:"
poetry run autopkg list-recipes --prefs tests/preferences.plist
echo "**Make-override:"
poetry run autopkg make-override Firefox.munki --force --prefs tests/preferences.plist
echo "**New-recipe:"
poetry run autopkg new-recipe TestRecipe.check --prefs tests/preferences.plist
echo "**Verify-trust-info:"
poetry run autopkg verify-trust-info Firefox.munki --prefs tests/preferences.plist
echo "**Update-trust-info:"
poetry run autopkg update-trust-info Firefox.munki --prefs tests/preferences.plist
echo "**Version:"
poetry run autopkg version
echo "**Repo-delete:"
poetry run autopkg repo-delete recipes --prefs tests/preferences.plist
echo "**Search:"
poetry run autopkg search Firefox --prefs tests/preferences.plist


if [[ -z "${CI}" && "${platform}" == "Darwin" ]]; then
    echo "**Run:"
    poetry run autopkg run -vv Firefox.munki --prefs tests/preferences.plist
    echo "**Run many:"
    poetry run autopkg run -vv Firefox.munki AdobeFlashPlayer.munki MakeCatalogs.munki --prefs tests/preferences.plist
    echo "**Install:"
    poetry run autopkg install Firefox -vv --prefs tests/preferences.plist
fi
