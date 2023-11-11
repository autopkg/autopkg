#!/bin/bash


find . -name '.DS_Store' -print0 | xargs -0 rm -f
find code -name '*.pyc' -print0 | xargs -0 rm -rf
find Recipes -name '*-receipt-*.plist' -print0 | xargs -0 rm -f
find Recipes -name '*.dmg' -print0 | xargs -0 rm -f
find Recipes -name '*.pkg' -print0 | xargs -0 rm -rf
find Recipes -name 'PackageInfo' -print0 | xargs -0 rm -rf
find Recipes/Munki/TextMate -name '*.zip' -print0 | xargs -0 rm -rf
rm -rf .venv
rm -rf dist
