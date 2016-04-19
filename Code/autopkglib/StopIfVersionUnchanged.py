#!/usr/bin/python
#
# Copyright 2016 Francois 'ftiff' Levaux-Tiffreau
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
"""See docstring for StopIfVersionUnchanged class"""

import os.path
import re
import collections

from autopkglib import Processor, ProcessorError


__all__ = ["StopIfVersionUnchanged"]

BundleInfo = collections.namedtuple('BundleInfo', ['bundle_path', 'bundle_id', 'bundle_short_version', 'bundle_version'])

class StopIfVersionUnchanged(Processor):
    # we dynamically set the docstring from the description (DRY), so:
    #pylint: disable=missing-docstring
    description = "Stop Processing if version has already been built."
    input_variables = {
        "version": {
            "required": True,
            "description": "Version to check.",
        },
    }
    output_variables = {
        "stop_processing_recipe": {
            "description": "Boolean. Should we stop processing the recipe?",
        },
    }

    __doc__ = description

    def read_bundle_info(self, path):
        """Read Contents/Info.plist inside a bundle.
        Returns a tuple (bundle_path, bundle_id, bundle_short_version, bundle_version)"""
        #pylint: disable=no-self-use

        p = re.compile(ur'<bundle path="(.*)" id="(.*)" CFBundleShortVersionString="(.*)" CFBundleVersion="(.*)"/>')
        try:
            with open(path, 'r') as file:
                file_content = file.read()
                return BundleInfo._make(re.search(p, file_content).group(1, 2, 3, 4))
        except BaseException as err:
            raise ProcessorError(err)


    def main(self):
        new_version = self.env["version"]
        recipe_cache_dir = self.env["RECIPE_CACHE_DIR"]

        xml_path = os.path.join(recipe_cache_dir, "PackageInfo")

        bundle_info = self.read_bundle_info(xml_path)

        if (new_version == bundle_info.bundle_version):
            self.output("Version: %s has already been built. Aborting." % bundle_info.bundle_version)
            self.env["stop_processing_recipe"] = True
        else:
            self.env["stop_processing_recipe"] = False


if __name__ == '__main__':
    PROCESSOR = AppDmgVersioner()
    PROCESSOR.execute_shell()

