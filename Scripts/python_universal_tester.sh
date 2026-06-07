#!/bin/bash
# This applies to macOS only.
# This is to determine which python packages have binaries that do not work on both x86_64 and ARM64 CPUs.

VERSION="${1:-3.11}"
[[ $VERSION == *"3."* ]] || { echo "Invalid Python version"; exit 1; }
FRAMEWORK="${2:-${HOME}/Library/AutoPkg/Cache/com.github.autopkg.AutoPkgGitMaster/Python.framework}"
echo "Using Python $VERSION"
echo "Framework: $FRAMEWORK"

STATUS=0

# ensure all .so and .dylibs are universal
LIB_COUNT=$(find "$FRAMEWORK" -name "*.so" -or -name "*.dylib" | wc -l)
UNIVERSAL_COUNT=$(find "$FRAMEWORK" -name "*.so" -or -name "*.dylib" | xargs file | grep "2 architectures" | wc -l)
if [ "$LIB_COUNT" != "$UNIVERSAL_COUNT" ] ; then
    echo "$LIB_COUNT libraries (*.so and *.dylib) found in the framework; only $UNIVERSAL_COUNT are universal!"
    echo "The following libraries are not universal:"
    find "$FRAMEWORK" -name "*.so" -or -name "*.dylib" | xargs file | grep -v "2 architectures" | grep -v "(for architecture"
    STATUS=1
fi

# test some more files in the framework
PYVER=$(echo "$VERSION" | cut -d. -f1-2)
MORE_FILES="${FRAMEWORK}/Versions/${PYVER}/Resources/Python.app/Contents/MacOS/Python
${FRAMEWORK}/Versions/Current/Python
${FRAMEWORK}/Versions/Current/bin/python${PYVER}"

for TESTFILE in $MORE_FILES ; do
    ARCH_TEST=$(file "$TESTFILE" | grep "2 architectures")
    if [ "$ARCH_TEST" == "" ]  ; then
        echo "$TESTFILE is not universal!"
        STATUS=1
    fi
done

[[ $STATUS == 0 ]] && echo "All files are universal!" || exit $STATUS
