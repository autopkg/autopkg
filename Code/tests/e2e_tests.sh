#!/bin/bash
# End-to-end integration tests for AutoPkg CLI verbs. Exercises each verb
# against a real git repo clone in an isolated temp directory. macOS only.

TESTDIR="${TMPDIR%/}/autopkg-e2e-tests"
AUTOPKG=../Code/autopkg

rm -rf "$TESTDIR"
mkdir -p "$TESTDIR/Cache" "$TESTDIR/RecipeRepos" "$TESTDIR/RecipeOverrides" "$TESTDIR/munki_repo"
trap 'rm -rf "$TESTDIR"' EXIT

PREFS_FILE="$TESTDIR/preferences.plist"
cat > "$PREFS_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CACHE_DIR</key>
	<string>$TESTDIR/Cache</string>
	<key>MUNKI_REPO</key>
	<string>$TESTDIR/munki_repo</string>
	<key>RECIPE_MAP_PATH</key>
	<string>$TESTDIR/recipe_map.json</string>
	<key>RECIPE_OVERRIDE_DIRS</key>
	<string>$TESTDIR/RecipeOverrides</string>
	<key>RECIPE_REPOS</key>
	<dict/>
	<key>RECIPE_REPO_DIR</key>
	<string>$TESTDIR/RecipeRepos</string>
	<key>RECIPE_SEARCH_DIRS</key>
	<array>
		<string>.</string>
	</array>
</dict>
</plist>
EOF
PREFS="--prefs $PREFS_FILE"

echo "**Help:"
$AUTOPKG help
echo "**List-processors:"
$AUTOPKG list-processors $PREFS
echo "**Processor-info:"
$AUTOPKG processor-info URLDownloader $PREFS
echo "**Repo-add:"
$AUTOPKG repo-add recipes $PREFS
echo "**Repo-list:"
$AUTOPKG repo-list $PREFS
echo "**Repo-update:"
$AUTOPKG repo-update all $PREFS
echo "**Generate-recipe-map:"
$AUTOPKG generate-recipe-map $PREFS
echo "**Audit:"
$AUTOPKG audit Firefox.munki $PREFS
echo "**Info:"
$AUTOPKG info Firefox.munki $PREFS
echo "**List-recipes:"
$AUTOPKG list-recipes $PREFS
echo "**Make-override:"
$AUTOPKG make-override Firefox.munki --force $PREFS
echo "**New-recipe:"
$AUTOPKG new-recipe "$TESTDIR/TestRecipe.check" $PREFS
echo "**Search:"
$AUTOPKG search Firefox $PREFS
echo "**Verify-trust-info:"
$AUTOPKG verify-trust-info Firefox.munki $PREFS
echo "**Update-trust-info:"
$AUTOPKG update-trust-info Firefox.munki $PREFS
echo "**Version:"
$AUTOPKG version
echo "**Run:"
$AUTOPKG run --check -vv Firefox.munki $PREFS
echo "**Clear-cache (recipe):"
$AUTOPKG clear-cache Firefox.munki $PREFS
echo "**Run many:"
$AUTOPKG run --check -vv Firefox.munki AdobeFlashPlayer.munki MakeCatalogs.munki $PREFS
echo "**Clear-cache (all):"
$AUTOPKG clear-cache all $PREFS
echo "**Install:"
$AUTOPKG install VLC -vv $PREFS
echo "**Repo-delete:"
$AUTOPKG repo-delete recipes $PREFS
