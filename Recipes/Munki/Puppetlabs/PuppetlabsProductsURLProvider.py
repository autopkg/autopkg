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

import urllib2
import re
from distutils.version import LooseVersion

from autopkglib import Processor, ProcessorError

__all__ = ["PuppetlabsProductsURLProvider"]

DL_INDEX = "https://downloads.puppetlabs.com/mac"
DEFAULT_VERSION = "latest"

class PuppetlabsProductsURLProvider(Processor):
    description = "Extracts a ."
    input_variables = {
        "product_name": {
            "required": True,
            "description": 
                "Product to fetch URL for. One of 'puppet', 'facter', 'hiera'.",
        },
        "get_version": {
            "required": False,
            "description": 
                ("Specific version to request. Defaults to '%s', which "
                 "automatically finds the highest available release version." 
                 % (DEFAULT_VERSION)),
        },
    }
    output_variables = {
        "version": {
            "description": "Version of the product.",
        },
        "url": {
            "description": "Download URL.",
        },
    }

    __doc__ = description

    def main(self):

        # look for "product-1.2.3.dmg"
        # skip anything with a '-' following the version no. ('rc', etc.)
        version_re = self.env.get("get_version")
        if not version_re or version_re == DEFAULT_VERSION:
            version_re = "\d+[\.\d]+"
        RE_DOWNLOAD = "href=\"(%s-(%s)+.dmg)\"" % (self.env["product_name"].lower(), version_re)

        try:
            data = urllib2.urlopen(DL_INDEX).read()
        except BaseException as e:
            raise ProcessorError("Unexpected error retrieving download index: '%s'" % e)

        # (dmg, version)
        candidates = re.findall(RE_DOWNLOAD, data)
        if not candidates:
            raise ProcessorError("Unable to parse any products from download index.")

        # sort to get the highest version
        highest = candidates[0]
        if  len(candidates) > 1:
            for prod in candidates:
                if LooseVersion(prod[1]) > LooseVersion(highest[1]):
                    highest = prod

        ver, url = highest[1], "%s/%s" % (DL_INDEX, highest[0])
        self.env["version"] = ver
        self.env["url"] = url
        self.output("Found URL %s" % self.env["url"])

if __name__ == "__main__":
    processor = PuppetlabsProductsURLProvider()
    processor.execute_shell()
