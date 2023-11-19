#!/bin/zsh

# This is intended to be run directly from the Scripts directory.

VERSION=$(/usr/libexec/PlistBuddy -c "Print:Version" "../Code/autopkglib/version.plist")
PKGROOT=$(mktemp -d /tmp/AutoPkg-build-root-XXXXXXXXXXX)
mkdir -p "$PKGROOT/Library/AutoPkg"
# cp -R ../Code/* "$PKGROOT/Library/AutoPkg/"
rsync -a --exclude '*.pyc' --exclude "*__pycache__" --exclude '.DS_Store' ../Code/ "$PKGROOT/Library/AutoPkg/"
mkdir -p "$PKGROOT/Library/LaunchDaemons"
mv "$PKGROOT/Library/AutoPkg/autopkgserver/autopkgserver.plist" "$PKGROOT/Library/LaunchDaemons/com.github.autopkg.autopkgserver.plist"
mv "$PKGROOT/Library/AutoPkg/autopkgserver/autopkginstalld.plist" "$PKGROOT/Library/LaunchDaemons/com.github.autopkg.autopkginstalld.plist"
mkdir -p "$PKGROOT/usr/local/autopkg"
ln -sf "/Library/AutoPkg/Python3/Python.framework/Versions/Current/bin/python3" "$PKGROOT/usr/local/autopkg/python"
mkdir -p "$PKGROOT/usr/local/bin"
ln -sf "//Library/AutoPkg/autopkg" "$PKGROOT/usr/local/bin/autopkg"
mkdir -p pkg-scripts
cp postinstall pkg-scripts/postinstall
mkdir -p artifacts
pkgbuild --root "$PKGROOT" \
--identifier com.github.autopkg.autopkg \
--version "$VERSION" \
--scripts pkg-scripts \
"artifacts/AutoPkg-only-$VERSION.pkg"