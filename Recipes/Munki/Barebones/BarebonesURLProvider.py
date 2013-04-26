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
import plistlib
from distutils.version import LooseVersion
from operator import itemgetter

from autopkglib import Processor, ProcessorError

__all__ = ["BarebonesURLProvider"]

URLS = {"textwrangler": "http://versioncheck.barebones.com/TextWrangler.xml",
        "bbedit": "http://versioncheck.barebones.com/BBEdit.xml"
        }

class BarebonesURLProvider(Processor):
    description = "Provides a version and dmg download for the Barebones product given."
    input_variables = {
        "product_name": {
            "required": True,
            "description": "Product to fetch URL for. One of 'textwrangler', 'bbedit'.",
        },
    }
    output_variables = {
        "version": {
            "description": "Version of the product.",
        },
        "url": {
            "description": "Download URL.",
        },
        "minimum_os_version": {
            "description": "Minimum OS version supported according to product metadata."
        }
    }

    __doc__ = description

    def main(self):

        def compare_version(a, b):
            return cmp(LooseVersion(a), LooseVersion(b))

        valid_prods = URLS.keys()
        prod = self.env.get("product_name")
        if prod not in valid_prods:
            raise ProcessorError("product_name %s is invalid; it must be one of: %s" % (
                                prod, valid_prods))
        url = URLS[prod]
        try:
            manifest_str = urllib2.urlopen(url).read()
        except BaseException as e:
            raise ProcessorError("Unexpected error retrieving product manifest: '%s'" % e)

        try:
            plist = plistlib.readPlistFromString(manifest_str)
        except BaseException as e:
            raise ProcessorError("Unexpected error parsing manifest as a plist: '%s'" % e)

        entries = plist.get("SUFeedEntries")
        if not entries:
            raise ProcessorError("Expected 'SUFeedEntries' manifest key wasn't found.")

        sorted_entries = sorted(entries,
                            key=itemgetter("SUFeedEntryShortVersionString"),
                            cmp=compare_version)
        metadata = sorted_entries[-1]
        url = metadata["SUFeedEntryDownloadURL"]
        min_os_version = metadata["SUFeedEntryMinimumSystemVersion"]
        version = metadata["SUFeedEntryShortVersionString"]

        self.env["version"] = version
        self.env["minimum_os_version"] = min_os_version
        self.env["url"] = url
        self.output("Found URL %s" % self.env["url"])

if __name__ == "__main__":
    processor = BarebonesURLProvider()
    processor.execute_shell()
