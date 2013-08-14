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
import FoundationPlist
import tempfile
import shutil
import subprocess

from DmgMounter import DmgMounter
from autopkglib import Processor, ProcessorError


__all__ = ["AdobeFlashDmgUnpacker"]


class AdobeFlashDmgUnpacker(DmgMounter):
    description = "Mounts a Flash dmg and extracts the plugin to unpack_dir."
    input_variables = {
        "dmg_path": {
            "required": True,
            "description": "Path to a dmg containing the Flash plugin installer.",
        },
        "unpack_dir": {
            "required": True,
            "description": "Path to where the plugin files will be unpacked.",
        },
    }
    output_variables = {
        "version": {
            "description": "Version of the flash plugin.",
        },
        "unpacked_items": {
            "description": "List of items that were unpacked.",
        },
    }
    
    __doc__ = description
    
    def read_bundle_info(self, path):
        """Read Contents/Info.plist inside a bundle."""
        
        try:
            info = FoundationPlist.readPlist(os.path.join(path, "Contents", "Info.plist"))
        except BaseException as e:
            raise ProcessorError(e)
        
        return info
    
    def main(self):
        # Mount the image.
        mount_point = self.mount(self.env["dmg_path"])
        temp_path = None
        # Wrap all other actions in a try/finally so the image is always
        # unmounted.
        try:
            pkg_path = os.path.join(mount_point,
                "Install Adobe Flash Player.app", "Contents",
                "Resources", "Adobe Flash Player.pkg", "Contents")
            
            # Create temporary directory.
            temp_path = tempfile.mkdtemp(prefix="flashXX", dir="/private/tmp")
            if len(temp_path) != len("/Library/Internet Plug-Ins"):
                raise ProcessorError("temp_path length mismatch.")
            
            # Unpack payload.
            try:
                p = subprocess.Popen(("/usr/bin/ditto",
                                      "-x",
                                      "-z",
                                      pkg_path + "/Archive.pax.gz",
                                      temp_path),
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                (out, err) = p.communicate()
            except OSError as e:
                raise ProcessorError("ditto execution failed with error code %d: %s" % (
                                      e.errno, e.strerror))
            if p.returncode != 0:
                raise ProcessorError("Unpacking Flash payload failed: %s" % err)
            
            # Move payload up out of Internet Plug-Ins if necessary.
            temp_plugins_path = os.path.join(temp_path, "Internet Plug-Ins")
            if os.path.isdir(temp_plugins_path):
                for item in os.listdir(temp_plugins_path):
                    src = os.path.join(temp_plugins_path, item)
                    dst = os.path.join(temp_path, item)
                    try:
                        os.rename(src, dst)
                    except OSError as e:
                        raise ProcessorError("Couldn't move %s to %s" % (src, dst))
                os.rmdir(temp_plugins_path)
            
            # Patch postflight executable.
            with open(pkg_path + "/Resources/postflight", "rb") as f:
                postflight = f.read()
            postflight_path = os.path.join(temp_path, "postflight")
            with open(postflight_path, "wb") as f:
                f.write(postflight.replace("/Library/Internet Plug-Ins", temp_path))
            os.chmod(postflight_path, 0700)
            
            # Run patched postflight to unpack plugin.
            subprocess.check_call(postflight_path)
            
            # Check plugin paths.
            plugin_path = os.path.join(temp_path, "Flash Player.plugin")
            xpt_path = os.path.join(temp_path, "flashplayer.xpt")
            if not os.path.isdir(plugin_path):
                raise ProcessorError("Unpacking Flash plugin failed.")
            
            # Read version.
            info = self.read_bundle_info(plugin_path)
            self.env["version"] = info["CFBundleShortVersionString"]

            # Copy files to destination.
            plugin_destination = os.path.join(self.env["unpack_dir"], "Flash Player.plugin")
            xpt_destination = os.path.join(self.env["unpack_dir"], "flashplayer.xpt")
            shutil.copytree(plugin_path, plugin_destination, symlinks=True)
            shutil.copy2(xpt_path, xpt_destination)
            
            self.env["unpacked_items"] = ["Flash Player.plugin",
                                           "flashplayer.xpt"]
        except BaseException as e:
            raise ProcessorError(e)
        finally:
            if temp_path:
                shutil.rmtree(temp_path)
            self.unmount(self.env["dmg_path"])
    

if __name__ == '__main__':
    processor = AdobeFlashDmgUnpacker()
    processor.execute_shell()
    
