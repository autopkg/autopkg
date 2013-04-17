#!/usr/bin/env python
#
# Copyright 2013 Timothy Sutton
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
import subprocess
import xml.etree.ElementTree as ET

from glob import glob
from tempfile import mkdtemp
from shutil import rmtree
from autopkglib.DmgMounter import DmgMounter
from autopkglib.Processor import ProcessorError

__all__ = ["OracleJava7Versioner"]


class OracleJava7Versioner(DmgMounter):
    description = "Extracts a ."
    input_variables = {
        "dmg_path": {
            "required": True,
            "description": "Path to a dmg containing the Oracle Java 7 JRE.",
        },
    }
    output_variables = {
        "plugin_cfbundleversion": {
            "description": "CFBundleVersion used by the web plugin.",
        },
        "plugin_displayname": {
            "description": "Release name, ie. 'Java 7 Update N'.",
        },
    }

    __doc__ = description

    def main(self):
        mount_point = self.mount(self.env["dmg_path"])
        # Wrap all other actions in a try/finally so the image is always
        # unmounted.
        try:
            tmp = mkdtemp(prefix='autopkg')
            pkgpath = glob(os.path.join(mount_point, "*.pkg"))[0]
            xarcmd = ["/usr/bin/xar", "-x", "-C", tmp, "-f", 
                      pkgpath, "--exclude", "Payload"]
            subprocess.call(xarcmd)
            with open(os.path.join(
                tmp, "javaappletplugin.pkg/PackageInfo"), "r") as fd:
                pkginfo = fd.read()
            rmtree(tmp)

            root = ET.fromstring(pkginfo)
            version = root.find(
                "./bundle[@id='com.oracle.java.JavaAppletPlugin']").get(
                "CFBundleVersion")

            self.env["plugin_cfbundleversion"] = version
            self.env["plugin_displayname"] = os.path.basename(
                pkgpath).split(".pkg")[0]
            self.output("CFBundleVersion is %s" % version)
        except BaseException as e:
            raise ProcessorError(e)
        finally:
            self.unmount(self.env["dmg_path"])

if __name__ == "__main__":
    processor = OracleJava7Versioner()
    processor.execute_shell()
