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


import urllib
import urllib2
import urlparse
import os
from xml.etree import ElementTree

from autopkglib import Processor, ProcessorError
from distutils.version import LooseVersion
from operator import itemgetter

__all__ = ["SparkleUpdateInfoProvider"]

XMLNS = "http://www.andymatuschak.org/xml-namespaces/sparkle"


class SparkleUpdateInfoProvider(Processor):
    description = "Provides URL to the highest version number or latest update."
    input_variables = {
        "appcast_url": {
            "required": True,
            "description": "URL for a Sparkle Appcast feed xml.",
        },
        "appcast_request_headers": {
            "required": False,
            "description": "Dictionary of additional HTTP headers to include in request.",
        },
        "appcast_query_pairs": {
            "required": False,
            "description": ("Dictionary of additional query pairs to include in request. "
                            "Manual url-encoding isn't necessary."),
        },
        "copy_sparkle_description_to_pkginfo": {
            "required": False,
            "description": ("If this variable is set (to anything), the description from "
                            "the appcast will be copied to the output additional_pkginfo. An admin "
                            "may prefer to forego a changelog-like description and instead "
                            "just give a general and consistent description for the app. "
                            "In some cases, the description is actually a URL for custom use. "
                            "Defaults to unset, ie. a description is _not_ copied to the pkginfo.")
        }
    }
    output_variables = {
        "url": {
            "description": "URL for a download.",
        },
        "additional_pkginfo": {
            "description": ("A pkginfo containing additional keys extracted from the "
                            "appcast feed. Currently this is 'description' and "
                            "'minimum_os_version' if it was defined in the feed.")
        }
    }

    __doc__ = description

    def get_feed_data(self, url):
        """Returns an array of dicts, one per update item, structured like:
        version: 1234
        human_version: 1.2.3.4 (optional)
        url: http://download/url.dmg
        minimum_os_version: 10.7 (optional)
        description_data: HTML description for update (optional)
        description_url: URL given by the sparkle:releaseNotesLink element (optional)

        Note: Descriptions may be either given as a URL (usually the case) or as raw HTML.
        We store one or the other rather than doing many GETs for metadata we're never going to use.
        If it's a URL, this must be handled by whoever calls this function.
        """

        request = urllib2.Request(url=url)

        # request header code borrowed from URLDownloader
        if "appcast_request_headers" in self.env:
            headers = self.env["appcast_request_headers"]
            for header, value in headers.items():
                request.add_header(header, value)
        # query string
        if "appcast_query_pairs" in self.env:
            queries = self.env["appcast_query_pairs"]
            query_string = urllib.urlencode([(k, v) for (k, v) in queries.items()])
        else:
            query_string = None

        try:
            url_handle = urllib2.urlopen(request, data=query_string)
        except:
            raise ProcessorError("Can't open URL %s" % request.get_full_url())

        data = url_handle.read()
        try:
            xmldata = ElementTree.fromstring(data)
        except:
            raise ProcessorError("Error parsing XML from appcast feed.")

        items = xmldata.findall("channel/item")

        versions = []
        for item_elem in items:
            enclosure = item_elem.find("enclosure")
            if enclosure is not None:
                item = {}
                # URL-quote the path component to handle spaces, etc. (Panic apps do this)
                url_bits = urlparse.urlsplit(enclosure.get("url"))
                encoded_path = urllib.quote(url_bits.path)
                item["url"] = url_bits.scheme + "://" + url_bits.netloc + encoded_path

                # item["url"] = urllib.quote(item["url"], safe=":")
                item["version"] = enclosure.get("{%s}version" % XMLNS)
                if item["version"] is None:
                    # Sparkle tries to guess a version from the download URL for rare cases
                    # where there is no sparkle:version enclosure attribute, for the format:
                    # AppnameOrAnythingReally_1.2.3.zip
                    # https://github.com/andymatuschak/Sparkle/blob/master/SUAppcastItem.m#L153-L167
                    item["version"] = os.path.basename(os.path.splitext(url)[0]).split("_")[1]
                human_version = item_elem.find("{%s}shortVersionString")
                if human_version is not None:
                    item["human_version"] = human_version
                min_version = item_elem.find("{%s}minimumSystemVersion" % XMLNS)
                if min_version is not None:
                    item["minimum_os_version"] = min_version.text
                description_elem = item_elem.find("{%s}releaseNotesLink" % XMLNS)
                if description_elem is not None:
                    item["description_url"] = description_elem.text
                if item_elem.find("description") is not None:
                    item["description_data"] = item_elem.find("description").text
                versions.append(item)

        return versions

    def main(self):
        def compare_version(a, b):
            return cmp(LooseVersion(a), LooseVersion(b))

        items = self.get_feed_data(self.env.get("appcast_url"))
        sorted_items = sorted(items,
                              key=itemgetter("version"),
                              cmp=compare_version)
        latest = sorted_items[-1]
        self.output("Version retrieved from appcast: %s" % latest["version"])
        if latest.get("human_version"):
            self.output("User-facing version retrieved from appcast: %s" % latest["human_version"])

        pkginfo = {}
        # All we care is whether this is set to something
        copy_description = self.env.get("copy_sparkle_description_to_pkginfo")
        if copy_description:
            # Format description
            if "description_url" in latest.keys():
                description = urllib2.urlopen(latest["description_url"]).read()
            elif "description_data" in latest.keys():
                description = "<html><body>" + latest["description_data"] + "</html></body>"
            else:
                description = ""
            pkginfo["description"] = description = description.decode("UTF-8")

        if latest.get("minimum_os_version") is not None:
            pkginfo["minimum_os_version"] = latest.get("minimum_os_version")

        self.env["url"] = latest["url"]
        self.output("Found URL %s" % self.env["url"])
        self.env["additional_pkginfo"] = pkginfo

if __name__ == "__main__":
    processor = SparkleUpdateInfoProvider()
    processor.execute_shell()
