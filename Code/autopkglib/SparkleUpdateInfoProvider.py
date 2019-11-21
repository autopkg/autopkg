#!/usr/bin/python
#
# Refactoring 2018 Michal Moravec
# Copyright 2013-2016 Timothy Sutton
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

"""See docstring for SparkleUpdateInfoProvider class"""

import os
import urllib
import urlparse
from distutils.version import LooseVersion
from operator import itemgetter
from xml.etree import ElementTree

from autopkglib import ProcessorError
from autopkglib.URLGetter import URLGetter

__all__ = ["SparkleUpdateInfoProvider"]

DEFAULT_XMLNS = "http://www.andymatuschak.org/xml-namespaces/sparkle"
SUPPORTED_ADDITIONAL_PKGINFO_KEYS = ["description", "minimum_os_version"]


class SparkleUpdateInfoProvider(URLGetter):
    """Provides URL to the highest version number or latest update."""

    description = __doc__
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
            "description": (
                "Dictionary of additional query pairs to include "
                "in request. Manual url-encoding isn't necessary."
            ),
        },
        "alternate_xmlns_url": {
            "required": False,
            "description": (
                "Alternate URL for the XML namespace, if the "
                "appcast is using an alternate one. Defaults to "
                "that used for 'vanilla' Sparkle appcasts."
            ),
        },
        "curl_opts": {
            "required": False,
            "description": (
                "Optional array of options to include with the download " "request."
            ),
        },
        "pkginfo_keys_to_copy_from_sparkle_feed": {
            "required": False,
            "description": (
                "Array of pkginfo keys that will be derived from "
                "any available metadata from the Sparkle feed and "
                "copied to 'additional_pkginfo'. The usefulness of "
                "these keys will depend on the admin's environment "
                "and the nature of the metadata provided by the "
                "application vendor. Note that the 'description' "
                "is usually equivalent to 'release notes' for that "
                "specific version. Defaults to "
                "['minimum_os_version']. "
                "Currently supported keys: {}.".format(
                    ", ".join(SUPPORTED_ADDITIONAL_PKGINFO_KEYS)
                )
            ),
        },
        "urlencode_path_component": {
            "required": False,
            "description": (
                "Boolean value to specify if the path component"
                "from the sparkle feed needs to be urlencoded. "
                "Defaults to True."
            ),
        },
        "PKG": {
            "required": False,
            "description": (
                "Local path to the pkg/dmg we'd otherwise download. "
                "If provided, the download is skipped and we just use "
                "this package or disk image."
            ),
        },
        "CURL_PATH": {
            "required": False,
            "default": "/usr/bin/curl",
            "description": "Path to curl binary. Defaults to /usr/bin/curl.",
        },
    }
    output_variables = {
        "url": {"description": "URL for a download."},
        "version": {
            "description": (
                "Version for the download extracted from the feed. "
                "This is a human-readable version if the feed has "
                "it (e.g., 2.3.4-pre4), and the basic machine-"
                "readable version (e.g., 823a) otherwise."
            )
        },
        "additional_pkginfo": {
            "description": (
                "A pkginfo containing additional keys extracted "
                "from the appcast feed. Currently this is "
                "'description' and 'minimum_os_version' if it was "
                "defined in the feed."
            )
        },
    }

    def prepare_curl_cmd(self, url, headers=None):
        """Assemble curl command and return it."""

        curl_cmd = super(SparkleUpdateInfoProvider, self).prepare_curl_cmd()
        self.add_curl_common_opts(curl_cmd)
        if headers:
            for header, value in headers.items():
                curl_cmd.extend(["--header", "{}: {}".format(header, value)])
        curl_cmd.append(url)
        return curl_cmd

    def fetch_content(self, url, headers=None):
        """Returns content retrieved by curl, given a url and an optional
        dictionary of header-name/value mappings."""

        curl_cmd = self.prepare_curl_cmd(url, headers)
        content = self.download_with_curl(curl_cmd)
        return content

    def get_feed_data(self, url):
        """Downloads raw feed XML"""

        # query string
        if "appcast_query_pairs" in self.env:
            queries = self.env["appcast_query_pairs"]
            new_query = urllib.urlencode([(k, v) for (k, v) in queries.items()])
            scheme, netloc, path, _, frag = urlparse.urlsplit(url)
            url = urlparse.urlunsplit((scheme, netloc, path, new_query, frag))

        data = self.fetch_content(url, headers=self.env.get("appcast_request_headers"))
        return data

    def build_url(self, enclosure):
        """URL-quote the path component to handle spaces, etc.
        (Panic apps do this)"""

        url_bits = urlparse.urlsplit(enclosure.get("url"))
        if self.env.get("urlencode_path_component", True):
            encoded_path = urllib.quote(url_bits.path)
        else:
            encoded_path = url_bits.path
        built_url = url_bits.scheme + "://" + url_bits.netloc + encoded_path
        if url_bits.query:
            built_url += "?" + url_bits.query
        return built_url

    def determine_version(self, enclosure, url):
        """Gets version from enclosure"""

        version = enclosure.get("{{{}}}version".format(self.xmlns))

        if version is None:
            # Sparkle tries to guess a version from the download URL for
            # rare cases where there is no sparkle:version enclosure
            # attribute, for the format: AppnameOrAnything_1.2.3.zip
            # https://github.com/sparkle-project/Sparkle/blob/
            # 89081ca030c0de218400f7c0f97530df524d687d/Sparkle/
            # SUAppcastItem.m#L69-L76
            #
            # We can even support OmniGroup's alternate appcast format
            # by cheating and using the '-' as a delimiter to derive
            # version info
            filename = os.path.basename(os.path.splitext(url)[0])
            for delimiter in ["_", "-"]:
                if delimiter in filename:
                    version = filename.split(delimiter)[-1]
                    break
        # if we still found nothing, fail
        if version is None:
            raise ProcessorError("Can't extract version info from item in feed!")
        return version

    def parse_feed_data(self, data):
        """Returns an array of dicts, one per update item, structured like:
        version: 1234
        human_version: 1.2.3.4 (optional)
        url: http://download/url.dmg
        minimum_os_version: 10.7 (optional)
        description_data: HTML description for update (optional)
        description_url: URL given by the sparkle:releaseNotesLink element
                         (optional)

        Note: Descriptions may be either given as a URL (usually the case) or as
        raw HTML. We store one or the other rather than doing many GETs for
        metadata we're never going to use. If it's a URL, this must be handled
        by whoever calls this function."""

        try:
            xmldata = ElementTree.fromstring(data)
        except:
            raise ProcessorError("Error parsing XML from appcast feed.")

        items = xmldata.findall("channel/item")
        if not items:
            raise ProcessorError("No channel items were found in appcast feed.")

        versions = []
        for item_elem in items:
            enclosure = item_elem.find("enclosure")
            if enclosure is not None:
                item = {}
                item["url"] = self.build_url(enclosure)
                item["version"] = self.determine_version(enclosure, item["url"])

                human_version = enclosure.get(
                    "{{{}}}shortVersionString".format(self.xmlns)
                )
                if human_version is not None:
                    item["human_version"] = human_version

                min_version = item_elem.find(
                    "{{{}}}minimumSystemVersion".format(self.xmlns)
                )
                if min_version is not None:
                    item["minimum_os_version"] = min_version.text

                description_elem = item_elem.find(
                    "{{{}}}releaseNotesLink".format(self.xmlns)
                )
                # Strip possible surrounding whitespace around description_url
                # element text as we'll be passing this as an argument to a
                # curl process
                if description_elem is not None:
                    item["description_url"] = description_elem.text.strip()

                if item_elem.find("description") is not None:
                    item["description_data"] = item_elem.find("description").text
                versions.append(item)

        return versions

    def handle_pkginfo(self, latest):
        """Handles any keys we may have defined"""

        pkginfo = {}
        sparkle_pkginfo_keys = self.env.get("pkginfo_keys_to_copy_from_sparkle_feed")
        if sparkle_pkginfo_keys:
            for k in sparkle_pkginfo_keys:
                if k not in SUPPORTED_ADDITIONAL_PKGINFO_KEYS:
                    self.output(
                        "Key {} isn't a supported key to copy from the "
                        "Sparkle feed, ignoring it.".format(k)
                    )
            # Format description
            if "description" in sparkle_pkginfo_keys:
                if "description_url" in latest.keys():
                    description = self.fetch_content(latest["description_url"])
                elif "description_data" in latest.keys():
                    description = (
                        "<html><body>" + latest["description_data"] + "</html></body>"
                    )
                else:
                    description = ""
                pkginfo["description"] = description.decode("UTF-8")

            if "minimum_os_version" in sparkle_pkginfo_keys:
                if latest.get("minimum_os_version") is not None:
                    pkginfo["minimum_os_version"] = latest.get("minimum_os_version")
            for copied_key in pkginfo.keys():
                self.output(
                    "Copied key {} from Sparkle feed to additional "
                    "pkginfo.".format(copied_key)
                )
        return pkginfo

    def main(self):
        """Get URL for latest version in update feed"""

        def compare_version(this, that):
            """Compare loose versions"""
            # cmp() doesn't exist in Python3, so this uses the suggested
            # solutions from What's New In Python 3.0:
            # https://docs.python.org/3.0/whatsnew/3.0.html#ordering-comparisons
            # This will be refactored in Python 3.
            this_comparison = LooseVersion(this) > LooseVersion(that)
            that_comparison = LooseVersion(this) < LooseVersion(that)
            return this_comparison - that_comparison

        if "PKG" in self.env:
            self.output("Local PKG provided, no downloaded needed.")
            self.output(
                "WARNING: Skipping this processor means output "
                "variables 'version', 'additional_pkginfo' will "
                "not contain useful info. If these are needed "
                "in other recipe steps, this may give unexpected "
                "results."
            )
            self.env["url"] = self.env.get("PKG")
            self.env["additional_pkginfo"] = {}
            self.env["version"] = "NotSetBySparkleUpdateInfoProvider"
            return

        # handle custom xmlns and version attributes
        self.xmlns = self.env.get("alternate_xmlns_url", DEFAULT_XMLNS)

        data = self.get_feed_data(self.env.get("appcast_url"))
        items = self.parse_feed_data(data)
        sorted_items = sorted(items, key=itemgetter("version"), cmp=compare_version)
        latest = sorted_items[-1]
        self.output("Version retrieved from appcast: {}".format(latest["version"]))
        if latest.get("human_version"):
            self.output(
                "User-facing version retrieved from appcast: {}".format(
                    latest["human_version"]
                )
            )

        pkginfo = self.handle_pkginfo(latest)

        self.env["url"] = latest["url"]
        self.env["version"] = latest.get("human_version", latest["version"])
        self.output("Found URL {}".format(self.env["url"]))
        self.env["additional_pkginfo"] = pkginfo


if __name__ == "__main__":
    PROCESSOR = SparkleUpdateInfoProvider()
    PROCESSOR.execute_shell()
