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


import subprocess
import FoundationPlist

from autopkglib import Processor, ProcessorError


__all__ = ["DmgMounter"]


class DmgMounter(Processor):
    """Base class for Processors that need to mount disk images."""
    
    def __init__(self, data=None, infile=None, outfile=None):
        super(DmgMounter, self).__init__(data, infile, outfile)
        self.mounts = dict()
        
    def getFirstPlist(self, textString):
        """Gets the first plist from a text string that may contain one or
        more text-style plists.
        Returns a tuple - the first plist (if any) and the remaining
        string after the plist"""
        plist_header = '<?xml version'
        plist_footer = '</plist>'
        plist_start_index = textString.find(plist_header)
        if plist_start_index == -1:
            # not found
            return ("", textString)
        plist_end_index = textString.find(
            plist_footer, plist_start_index + len(plist_header))
        if plist_end_index == -1:
            # not found
            return ("", textString)
        # adjust end value
        plist_end_index = plist_end_index + len(plist_footer)
        return (textString[plist_start_index:plist_end_index],
                textString[plist_end_index:])
    
    def DMGhasSLA(self, dmgpath):
        '''Returns true if dmg has a Software License Agreement.
        These dmgs normally cannot be attached without user intervention'''
        hasSLA = False
        proc = subprocess.Popen(
                    ['/usr/bin/hdiutil', 'imageinfo', dmgpath, '-plist'],
                    bufsize=-1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out, err) = proc.communicate()
        if err:
            print >> sys.stderr, (
                'hdiutil error %s with image %s.' % (err, dmgpath))
        (pliststr, out) = self.getFirstPlist(out)
        if pliststr:
            try:
                plist = FoundationPlist.readPlistFromString(pliststr)
                properties = plist.get('Properties')
                if properties:
                    hasSLA = properties.get('Software License Agreement', False)
            except FoundationPlist.NSPropertyListSerializationException:
                pass

        return hasSLA
    
    def mount(self, pathname):
        """Mount image with hdiutil."""
        # Make sure we don't try to mount something twice.
        if pathname in self.mounts:
            raise ProcessorError("%s is already mounted" % pathname)
        
        stdin = ''
        if self.DMGhasSLA(pathname):
            stdin = 'Y\n'
        
        # Call hdiutil.
        try:
            p = subprocess.Popen(("/usr/bin/hdiutil",
                                  "attach",
                                  "-plist",
                                  "-mountrandom", "/private/tmp",
                                  "-nobrowse",
                                  pathname),
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 stdin=subprocess.PIPE)
            (out, err) = p.communicate(stdin)
        except OSError as e:
            raise ProcessorError(
                "hdiutil execution failed with error code %d: %s" 
                % (e.errno, e.strerror))
        if p.returncode != 0:
            raise ProcessorError("mounting %s failed: %s" % (pathname, err))
        
        # Read output plist.
        (pliststr, out) = self.getFirstPlist(out)
        try:
            output = FoundationPlist.readPlistFromString(pliststr)
        except FoundationPlist.NSPropertyListSerializationException:
            raise ProcessorError(
                "mounting %s failed: unexpected output from hdiutil" % pathname)
        
        # Find mount point.
        for part in output.get("system-entities", []):
            if "mount-point" in part:
                # Add to mount list.
                self.mounts[pathname] = part["mount-point"]
                self.output("Mounted disk image %s" % pathname)
                return self.mounts[pathname]
        raise ProcessorError(
            "mounting %s failed: unexpected output from hdiutil" % pathname)

    def unmount(self, pathname):
        """Unmount previously mounted image."""
        
        # Don't try to unmount something we didn't mount.
        if not pathname in self.mounts:
            raise ProcessorError("%s is not mounted" % pathname)
        
        # Call hdiutil.
        try:
            p = subprocess.Popen(("/usr/bin/hdiutil",
                                  "detach",
                                  self.mounts[pathname]),
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (out, err) = p.communicate()
        except OSError as e:
            raise ProcessorError(
                "ditto execution failed with error code %d: %s" 
                % (e.errno, e.strerror))
        if p.returncode != 0:
            raise ProcessorError("unmounting %s failed: %s" % (pathname, err))
        
        # Delete mount from mount list.
        del self.mounts[pathname]
    

if __name__ == '__main__':
    try:
        import sys
        dmgmounter = DmgMounter()
        mountpoint = dmgmounter.mount("Download/Firefox-sv-SE.dmg")
        print "Mounted at %s" % mountpoint
        dmgmounter.unmount("Download/Firefox-sv-SE.dmg")
    except ProcessorError as e:
        print >>sys.stderr, "ProcessorError: %s" % e
        sys.exit(10)
    else:
        sys.exit(0)
    
