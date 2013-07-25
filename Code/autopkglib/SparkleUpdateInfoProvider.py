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

DEFAULT_XMLNS = "http://www.andymatuschak.org/xml-namespaces/sparkle"
SUPPORTED_ADDITIONAL_PKGINFO_KEYS = ["description",
                                     "minimum_os_version"
                                     ]


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
        "alternate_xmlns_url": {
            "required": False,
            "description": ("Alternate URL for the XML namespace, if the appcast is using "
                            "an alternate one. Defaults to that used for 'vanilla' Sparkle "
                            "appcasts."),
        },
        "pkginfo_keys_to_copy_from_sparkle_feed": {
            "required": False,
            "description": ("Array of pkginfo keys that will be derived from any available "
                            "metadata from the Sparkle feed and copied to 'additional_pkginfo'. "
                            "The usefulness of these keys will depend on the admin's environment "
                            "and the nature of the metadata provided by the application vendor. "
                            "Note that the 'description' is usually equivalent to 'release notes' "
                            "for that specific version. Defaults to ['minimum_os_version']. "
                            "Currently supported keys: %s." %
                            ", ".join(SUPPORTED_ADDITIONAL_PKGINFO_KEYS))
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

        # handle custom xmlns and version attributes
        if "alternate_xmlns_url" in self.env:
            xmlns = self.env["alternate_xmlns_url"]
        else:
            xmlns = DEFAULT_XMLNS

        # query string
        if "appcast_query_pairs" in self.env:
            queries = self.env["appcast_query_pairs"]
            new_query = urllib.urlencode([(k, v) for (k, v) in queries.items()])
            scheme, netloc, path, old_query, frag = urlparse.urlsplit(url)
            url = urlparse.urlunsplit((scheme, netloc, path, new_query, frag))

        request = urllib2.Request(url=url)

        # request header code borrowed from URLDownloader
        if "appcast_request_headers" in self.env:
            headers = self.env["appcast_request_headers"]
            for header, value in headers.items():
                request.add_header(header, value)

        try:
            url_handle = urllib2.urlopen(request)
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
                built_url = url_bits.scheme + "://" + url_bits.netloc + encoded_path
                if url_bits.query:
                    built_url += "?" + url_bits.query
                item["url"] = built_url

                item["version"] = enclosure.get("{%s}version" % xmlns)
                if item["version"] is None:
                    # Sparkle tries to guess a version from the download URL for rare cases
                    # where there is no sparkle:version enclosure attribute, for the format:
                    # AppnameOrAnythingReally_1.2.3.zip
                    # https://github.com/andymatuschak/Sparkle/blob/master/SUAppcastItem.m#L153-L167
                    #
                    # We can even support OmniGroup's alternate appcast format by cheating
                    # and using the '-' as a delimiter to derive version info
                    filename = os.path.basename(os.path.splitext(item["url"])[0])
                    for delimiter in ['_', '-']:
                        if delimiter in filename:
                            item["version"] = filename.split(delimiter)[-1]
                            break
                # if we still found nothing, fail
                if item["version"] is None:
                    raise ProcessorError("Can't extract version info from item in feed!")

                human_version = item_elem.find("{%s}shortVersionString")
                if human_version is not None:
                    item["human_version"] = human_version
                min_version = item_elem.find("{%s}minimumSystemVersion" % xmlns)
                if min_version is not None:
                    item["minimum_os_version"] = min_version.text
                description_elem = item_elem.find("{%s}releaseNotesLink" % xmlns)
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
        # Handle any keys we may have defined
        sparkle_pkginfo_keys = self.env.get("pkginfo_keys_to_copy_from_sparkle_feed")
        if sparkle_pkginfo_keys:
            for k in sparkle_pkginfo_keys:
                if k not in SUPPORTED_ADDITIONAL_PKGINFO_KEYS:
                    self.output("Key %s isn't a supported key to copy from the "
                                "Sparkle feed, ignoring it." % k)
            # Format description
            if "description" in sparkle_pkginfo_keys:
                if "description_url" in latest.keys():
                    description = urllib2.urlopen(latest["description_url"]).read()
                elif "description_data" in latest.keys():
                    description = "<html><body>" + latest["description_data"] + "</html></body>"
                else:
                    description = ""
                pkginfo["description"] = description = description.decode("UTF-8")

            if "minimum_os_version" in sparkle_pkginfo_keys:
                if latest.get("minimum_os_version") is not None:
                    pkginfo["minimum_os_version"] = latest.get("minimum_os_version")
            for copied_key in pkginfo.keys():
                self.output("Copied key %s from Sparkle feed to additional pkginfo." %
                            copied_key)

        self.env["url"] = latest["url"]
        self.output("Found URL %s" % self.env["url"])
        self.env["additional_pkginfo"] = pkginfo

if __name__ == "__main__":
    processor = SparkleUpdateInfoProvider()
    processor.execute_shell()
