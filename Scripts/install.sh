#!/bin/bash

# Manual script-based installation of AutoPkg.
# This is intended for development use only - for regular use, please use
# a release installer package from: https://github.com/autopkg/autopkg/releases

launchd_load()
{
    # most likely it's loaded..
    echo "Attempting to unload $1.."
    /bin/launchctl unload "$1"
    echo "Attempting to load $1.."
    /bin/launchctl load "$1"
}

INSTALL_DIR="/Library/AutoPkg"
LAUNCH_DAEMON_PKGSERVER="/Library/LaunchDaemons/com.github.autopkg.autopkgserver.plist"
LAUNCH_DAEMON_INSTALLD="/Library/LaunchDaemons/com.github.autopkg.autopkginstalld.plist"

if [ `id -u` -ne 0 ]; then
    echo "Installation must be done as root."
    exit 1
fi

# Remove previously installed version
if [ -e "$INSTALL_DIR" ]; then
    echo "Removing existing install"
    rm -rf "$INSTALL_DIR"
fi
for DAEMON in "$LAUNCH_DAEMON_PKGSERVER" "$LAUNCH_DAEMON_INSTALLD"; do
    if [ -e "$DAEMON" ]; then
        echo "Removing Launch Daemon $(basename "$DAEMON").."
        rm -f "$DAEMON"
    fi
done

echo "Installing AutoPkg to $INSTALL_DIR"

echo "Creating directories"
mkdir -m 0755 "$INSTALL_DIR"
mkdir -m 0755 "$INSTALL_DIR/autopkglib"
mkdir -m 0755 "$INSTALL_DIR/autopkglib/github"
mkdir -m 0755 "$INSTALL_DIR/autopkgserver"
mkdir -m 0755 "$INSTALL_DIR/FoundationPlist"

echo "Copying executable"
cp Code/autopkg "$INSTALL_DIR/"
ln -sf "$INSTALL_DIR/autopkg" /usr/local/bin/autopkg

echo "Copying library"
cp Code/autopkglib/*.py "$INSTALL_DIR/autopkglib/"
cp Code/autopkglib/github/*.py "$INSTALL_DIR/autopkglib/github"
cp Code/autopkglib/version.plist "$INSTALL_DIR/autopkglib/"

echo "Copying server"
cp Code/autopkgserver/autopkgserver "$INSTALL_DIR/autopkgserver/"
cp Code/autopkgserver/autopkginstalld "$INSTALL_DIR/autopkgserver/"
cp Code/autopkgserver/*.py "$INSTALL_DIR/autopkgserver/"
cp Code/autopkgserver/autopkgserver.plist "$LAUNCH_DAEMON_PKGSERVER"
cp Code/autopkgserver/autopkginstalld.plist "$LAUNCH_DAEMON_INSTALLD"

echo "Copying FoundationPlist"
cp Code/FoundationPlist/*.py "$INSTALL_DIR/FoundationPlist/"

echo "Setting permissions"
find "$INSTALL_DIR" -type f -exec chmod 755 {} \;
chown -hR root:wheel "$INSTALL_DIR"

echo "Installing Launch Daemons"
launchd_load "$LAUNCH_DAEMON_PKGSERVER"
launchd_load "$LAUNCH_DAEMON_INSTALLD"
