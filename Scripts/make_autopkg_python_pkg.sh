#!/bin/zsh

# This is intended to be run directly from the Scripts directory.

PYVERSION=$(/usr/libexec/PlistBuddy -c "Print:PythonVersion" "../Code/autopkglib/version.plist")
WORKROOT=$(mktemp -d /tmp/AutoPkg-build-root-XXXXXXXXXXX)
git clone https://github.com/gregneagle/relocatable-python.git "$WORKROOT/relocatable-python"
PKGROOT="$WORKROOT/Library/AutoPkg/Python3"
mkdir -p "$PKGROOT"
/usr/bin/python3 "$WORKROOT/relocatable-python/make_relocatable_python_framework.py" \
    --python-version "$PYVERSION" \
    --pip-requirements "../new_requirements.txt" \
    --os-version "11" \
    --destination "$PKGROOT/Python.framework"

pkgbuild --root "$PKGROOT" \
--identifier com.github.autopkg.python \
--install-location "/Library/AutoPkg/Python3" \
--version "$PYVERSION" \
"artifacts/AutoPkg-Python-$PYVERSION.pkg"