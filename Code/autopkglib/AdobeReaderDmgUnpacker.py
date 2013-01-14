#!/usr/bin/env python
#
# Copyright 2010 Per Olofsson
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


import os
import plistlib
import tempfile
import shutil
import zipfile
from xml.etree import ElementTree

from DmgMounter import DmgMounter
from Processor import Processor, ProcessorError


__all__ = ["AdobeReaderDmgUnpacker"]


class AdobeReaderDmgUnpacker(DmgMounter):
    description = "Mounts an Adobe Reader dmg and extracts the application and plugin to unpack_root."
    input_variables = {
        "dmg_path": {
            "required": True,
            "description": "Path to a dmg containing the Adobe Reader installer.",
        },
        "unpack_root": {
            "required": True,
            "description": "Path to the root where files will be unpacked.",
        },
        "pkgroot": {
            "required": True,
            "description": "Virtual root where the payloads will be extracted",
        }
    }
    output_variables = {
        "app_version": {
            "description": "Version of the Adobe Reader application.",
        },
        "plugin_version": {
            "description": "Version of the Adobe Reader plugin.",
        },
    }
    
    __doc__ = description
    
    def read_info_plist_version(self, path):
        """Read version from Info.plist."""
        
        try:
            info = plistlib.readPlist(path)
            return info["CFBundleShortVersionString"]
        except BaseException as e:
            raise ProcessorError(e)
    
    def unsevenzip(self, app_path, sevenzip_path):
        print "Unsevenzipping"
        for filename in os.listdir(app_path):
            if filename.endswith(".7z"):
                print filename
                archive_path = os.path.join(app_path, filename)
                self.cmdexec((sevenzip_path,
                              "-o%s" % app_path,
                              "-y",
                              "x",
                              archive_path),
                             "Unsevenzipping %s" % filename)
                os.unlink(archive_path)
    
    def setmodes(self, app_path, xfiles):
        print "Setting modes"
        for dirpath, dirnames, filenames in os.walk(app_path):
            for dirname in dirnames:
                os.chmod(os.path.join(dirpath, dirname), 0775)
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                relpath = path.replace(app_path, "", 1)[1:]
                if relpath in xfiles:
                    mode = 0775
                else:
                    mode = 0664
                os.chmod(path, mode)
    
    def unpack_payload(self, path):
        packageinfo_path = os.path.join(path, "PackageInfo")
        try:
            packageinfo = ElementTree.parse(packageinfo_path)
        except BaseException as e:
            raise ProcessorError("Can't read %s: %s" % (packageinfo_path, e))
        
        pkg_info = packageinfo.getroot()
        if pkg_info.tag != "pkg-info":
            raise ProcessorError("%s root isn't pkg-info" % packageinfo_path)
        
        target = pkg_info.get("install-location", "")
        destination_path = self.env['pkgroot'] + target
        
        payload_path = os.path.join(path, "Payload")
        
        self.cmdexec(("/usr/bin/ditto",
                      "-x",
                      "-z",
                      payload_path,
                      destination_path),
                     "Unpacking payload %s to %s" % (payload_path, destination_path))
    
    def main(self):
        # Mount the image.
        mount_point = self.mount(self.env["dmg_path"])
        # Temporary paths that should be deleted afterwards.
        temp_path = None
        sevenzip_path = None
        # Wrap all other actions in a try/finally so the image is always
        # unmounted.
        try:
            pkg_path = os.path.join(mount_point, "Adobe Reader X Installer.pkg")
            
            # Create temporary directory.
            temp_path = tempfile.mkdtemp(prefix="adobereader", dir="/private/tmp")
            expand_path = os.path.join(temp_path, "pkg")
            
            # Expand package.
            self.cmdexec(("/usr/sbin/pkgutil", "--expand",
                          pkg_path, expand_path),
                         "Unpacking Adobe Reader installer")
            
            for name in os.listdir(expand_path):
                if name.endswith(".pkg"):
                    self.unpack_payload(os.path.join(expand_path, name))
            
            app_path = os.path.join(self.env['pkgroot'],
                                    "Applications",
                                    "Adobe Reader.app",
                                    "Contents")
            
            # FIXME: Rewrite this with proper error handling.
            z = zipfile.ZipFile(os.path.join(app_path, "7za.zip"))
            f = z.open("7za")
            fd, sevenzip_path = tempfile.mkstemp()
            print repr(fd), repr(sevenzip_path)
            sevenzip_f = os.fdopen(fd, "wb")
            sevenzip_f.write(f.read())
            f.close()
            sevenzip_f.close()
            os.chmod(sevenzip_path, 0700)
            
            f = z.open("setX.txt")
            xfiles = list()
            for line in f:
                filename = line.partition("#")[0].rstrip()
                if filename:
                    xfiles.append(filename)
            f.close()
            
            self.unsevenzip(app_path, sevenzip_path)
            self.setmodes(app_path, xfiles)
            
            os.unlink(os.path.join(app_path, "7za.zip"))
            os.unlink(os.path.join(app_path, "decompress"))
            
            # Read versions.
            app_info_path = os.path.join(app_path, "Info.plist")
            self.env["app_version"] = self.read_info_plist_version(app_info_path)
            plugin_info_path = os.path.join(self.env['pkgroot'],
                                            "Library",
                                            "Internet Plug-Ins",
                                            "AdobePDFViewer.plugin",
                                            "Contents",
                                            "Info.plist")
            self.env["plugin_version"] = self.read_info_plist_version(plugin_info_path)
            
        except BaseException as e:
            raise ProcessorError(e)
        finally:
            self.unmount(self.env["dmg_path"])
            for path in (temp_path, sevenzip_path):
                if os.path.isdir(path):
                    shutil.rmtree(path)
                elif os.path.isfile(path):
                    os.unlink(path)
    

if __name__ == '__main__':
    processor = AdobeReaderDmgUnpacker()
    processor.execute_shell()
    
