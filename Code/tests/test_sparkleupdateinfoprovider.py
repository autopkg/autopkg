#!/usr/local/autopkg/python
#
# Copyright 2025 Elliot Jordan
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

import unittest
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from autopkglib import ProcessorError
from autopkglib.SparkleUpdateInfoProvider import SparkleUpdateInfoProvider


class TestSparkleUpdateInfoProvider(unittest.TestCase):
    """Test cases for SparkleUpdateInfoProvider processor."""

    def setUp(self):
        """Set up test fixtures."""
        self.tmp_dir = TemporaryDirectory()
        self.processor = SparkleUpdateInfoProvider()
        self.processor.env = {
            "appcast_url": "https://example.com/appcast.xml",
        }

    def tearDown(self):
        """Clean up after tests."""
        self.tmp_dir.cleanup()

    def _create_sample_appcast_xml(
        self,
        include_human_version=True,
        include_min_os=True,
        include_channel=False,
        include_description=False,
    ):
        """Create a sample Sparkle appcast XML for testing."""
        xmlns = "http://www.andymatuschak.org/xml-namespaces/sparkle"

        xml_content = f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:sparkle="{xmlns}">
    <channel>
        <title>App Updates</title>
        <link>https://example.com/</link>
        <description>Most recent changes with links to updates.</description>
        <language>en</language>
        <item>
            <title>Version 2.0.0</title>
            <sparkle:version>2000</sparkle:version>"""

        if include_human_version:
            xml_content += "\n            <sparkle:shortVersionString>2.0.0</sparkle:shortVersionString>"

        if include_min_os:
            xml_content += "\n            <sparkle:minimumSystemVersion>10.13</sparkle:minimumSystemVersion>"

        if include_channel:
            xml_content += "\n            <sparkle:channel>beta</sparkle:channel>"

        if include_description:
            xml_content += "\n            <description>Release notes for version 2.0.0</description>"

        xml_content += """
            <pubDate>Wed, 15 Jan 2025 10:00:00 +0000</pubDate>
            <enclosure url="https://example.com/app-2.0.0.dmg"
                       sparkle:version="2000"
                       length="12345678"
                       type="application/octet-stream" />
        </item>
        <item>
            <title>Version 1.5.0</title>
            <sparkle:version>1500</sparkle:version>"""

        if include_human_version:
            xml_content += "\n            <sparkle:shortVersionString>1.5.0</sparkle:shortVersionString>"

        xml_content += """
            <pubDate>Mon, 01 Dec 2024 10:00:00 +0000</pubDate>
            <enclosure url="https://example.com/app-1.5.0.dmg"
                       sparkle:version="1500"
                       length="11111111"
                       type="application/octet-stream" />
        </item>
    </channel>
</rss>"""
        return xml_content.encode("utf-8")

    # Test basic functionality
    def test_main_basic_functionality(self):
        """Test that main() processes a basic appcast correctly."""
        sample_xml = self._create_sample_appcast_xml()

        with patch.object(self.processor, "get_feed_data", return_value=sample_xml):
            self.processor.main()

        # Should get the latest version (2.0.0)
        self.assertEqual(self.processor.env["version"], "2.0.0")
        self.assertEqual(self.processor.env["url"], "https://example.com/app-2.0.0.dmg")
        self.assertIsInstance(self.processor.env["additional_pkginfo"], dict)

    def test_main_with_local_pkg(self):
        """Test that main() skips download when PKG is provided."""
        self.processor.env["PKG"] = "/path/to/local.pkg"

        with patch.object(self.processor, "output") as mock_output:
            self.processor.main()

        # Should use local PKG path and skip processing
        self.assertEqual(self.processor.env["url"], "/path/to/local.pkg")
        self.assertEqual(
            self.processor.env["version"], "NotSetBySparkleUpdateInfoProvider"
        )
        self.assertEqual(self.processor.env["additional_pkginfo"], {})
        mock_output.assert_any_call("Local PKG provided, no downloaded needed.")

    def test_main_with_update_channel(self):
        """Test that main() filters items by update channel."""
        sample_xml = self._create_sample_appcast_xml(include_channel=True)
        self.processor.env["update_channel"] = "beta"

        with patch.object(self.processor, "get_feed_data", return_value=sample_xml):
            self.processor.main()

        # Should find the beta channel item
        self.assertEqual(self.processor.env["version"], "2.0.0")

    def test_main_no_items_in_channel_raises_error(self):
        """Test that main() raises error when no items found in specified channel."""
        sample_xml = self._create_sample_appcast_xml(include_channel=False)
        self.processor.env["update_channel"] = "nonexistent"

        with patch.object(self.processor, "get_feed_data", return_value=sample_xml):
            with self.assertRaises(ProcessorError) as context:
                self.processor.main()

            self.assertIn(
                "No items were found in nonexistent channel", str(context.exception)
            )

    # Test feed data parsing
    def test_parse_feed_data_basic(self):
        """Test that parse_feed_data extracts basic information correctly."""
        sample_xml = self._create_sample_appcast_xml()
        self.processor.xmlns = "http://www.andymatuschak.org/xml-namespaces/sparkle"

        items = self.processor.parse_feed_data(sample_xml)

        self.assertEqual(len(items), 2)
        latest_item = max(items, key=lambda x: int(x["version"]))
        self.assertEqual(latest_item["version"], "2000")
        self.assertEqual(latest_item["human_version"], "2.0.0")
        self.assertEqual(latest_item["url"], "https://example.com/app-2.0.0.dmg")
        self.assertEqual(latest_item["minimum_os_version"], "10.13")

    def test_parse_feed_data_with_channel(self):
        """Test that parse_feed_data extracts channel information."""
        sample_xml = self._create_sample_appcast_xml(include_channel=True)
        self.processor.xmlns = "http://www.andymatuschak.org/xml-namespaces/sparkle"

        items = self.processor.parse_feed_data(sample_xml)

        latest_item = max(items, key=lambda x: int(x["version"]))
        self.assertEqual(latest_item["channel"], "beta")

    def test_parse_feed_data_with_description(self):
        """Test that parse_feed_data extracts description information."""
        sample_xml = self._create_sample_appcast_xml(include_description=True)
        self.processor.xmlns = "http://www.andymatuschak.org/xml-namespaces/sparkle"

        items = self.processor.parse_feed_data(sample_xml)

        latest_item = max(items, key=lambda x: int(x["version"]))
        self.assertEqual(
            latest_item["description_data"], "Release notes for version 2.0.0"
        )

    def test_parse_feed_data_invalid_xml_raises_error(self):
        """Test that parse_feed_data raises error for invalid XML."""
        invalid_xml = b"<invalid>xml</not_closed>"

        with self.assertRaises(ProcessorError) as context:
            self.processor.parse_feed_data(invalid_xml)

        self.assertIn("Error parsing XML from appcast feed", str(context.exception))

    def test_parse_feed_data_no_items_raises_error(self):
        """Test that parse_feed_data raises error when no items found."""
        empty_xml = b"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
    <channel>
        <title>Empty Feed</title>
    </channel>
</rss>"""

        with self.assertRaises(ProcessorError) as context:
            self.processor.parse_feed_data(empty_xml)

        self.assertIn(
            "No channel items were found in appcast feed", str(context.exception)
        )

    def test_parse_feed_data_skips_items_without_enclosure(self):
        """Test that parse_feed_data skips items without enclosure."""
        xml_with_bad_item = b"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle">
    <channel>
        <item>
            <title>Bad Item</title>
            <sparkle:version>3000</sparkle:version>
            <!-- No enclosure -->
        </item>
        <item>
            <title>Good Item</title>
            <sparkle:version>2000</sparkle:version>
            <enclosure url="https://example.com/app-2.0.0.dmg"
                       sparkle:version="2000"
                       length="12345678"
                       type="application/octet-stream" />
        </item>
    </channel>
</rss>"""
        self.processor.xmlns = "http://www.andymatuschak.org/xml-namespaces/sparkle"

        items = self.processor.parse_feed_data(xml_with_bad_item)

        # Should only get the good item
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["version"], "2000")

    # Test version determination
    def test_determine_version_from_enclosure(self):
        """Test that determine_version gets version from enclosure attribute."""
        xmlns = "http://www.andymatuschak.org/xml-namespaces/sparkle"
        self.processor.xmlns = xmlns

        enclosure = MagicMock()
        enclosure.get.return_value = "1234"

        version = self.processor.determine_version(
            enclosure, "https://example.com/app.dmg"
        )

        self.assertEqual(version, "1234")
        enclosure.get.assert_called_with(f"{{{xmlns}}}version")

    def test_determine_version_from_filename_underscore(self):
        """Test that determine_version extracts version from filename with underscore."""
        self.processor.xmlns = "http://www.andymatuschak.org/xml-namespaces/sparkle"

        enclosure = MagicMock()
        enclosure.get.return_value = None

        version = self.processor.determine_version(
            enclosure, "https://example.com/App_1.2.3.dmg"
        )

        self.assertEqual(version, "1.2.3")

    def test_determine_version_from_filename_dash(self):
        """Test that determine_version extracts version from filename with dash."""
        self.processor.xmlns = "http://www.andymatuschak.org/xml-namespaces/sparkle"

        enclosure = MagicMock()
        enclosure.get.return_value = None

        version = self.processor.determine_version(
            enclosure, "https://example.com/App-1.2.3.zip"
        )

        self.assertEqual(version, "1.2.3")

    def test_determine_version_failure_raises_error(self):
        """Test that determine_version raises error when no version found."""
        self.processor.xmlns = "http://www.andymatuschak.org/xml-namespaces/sparkle"

        enclosure = MagicMock()
        enclosure.get.return_value = None

        with self.assertRaises(ProcessorError) as context:
            self.processor.determine_version(enclosure, "https://example.com/app.dmg")

        self.assertIn(
            "Can't extract version info from item in feed", str(context.exception)
        )

    # Test URL building
    def test_build_url_with_encoding(self):
        """Test that build_url properly encodes path components."""
        self.processor.env["urlencode_path_component"] = True

        enclosure = MagicMock()
        enclosure.get.return_value = "https://example.com/My App 1.0.dmg"

        result = self.processor.build_url(enclosure)

        self.assertEqual(result, "https://example.com/My%20App%201.0.dmg")

    def test_build_url_without_encoding(self):
        """Test that build_url skips encoding when disabled."""
        self.processor.env["urlencode_path_component"] = False

        enclosure = MagicMock()
        enclosure.get.return_value = "https://example.com/My App 1.0.dmg"

        result = self.processor.build_url(enclosure)

        self.assertEqual(result, "https://example.com/My App 1.0.dmg")

    def test_build_url_with_query_params(self):
        """Test that build_url preserves query parameters."""
        self.processor.env["urlencode_path_component"] = True

        enclosure = MagicMock()
        enclosure.get.return_value = "https://example.com/app.dmg?token=abc123"

        result = self.processor.build_url(enclosure)

        self.assertEqual(result, "https://example.com/app.dmg?token=abc123")

    # Test pkginfo handling
    def test_handle_pkginfo_with_description_url(self):
        """Test that handle_pkginfo fetches description from URL."""
        self.processor.env["pkginfo_keys_to_copy_from_sparkle_feed"] = ["description"]

        latest = {"description_url": "https://example.com/notes.html"}
        description_content = b"<p>Release notes content</p>"

        with patch.object(
            self.processor, "fetch_content", return_value=description_content
        ) as mock_fetch:
            pkginfo = self.processor.handle_pkginfo(latest)

        self.assertEqual(pkginfo["description"], "<p>Release notes content</p>")
        mock_fetch.assert_called_once_with("https://example.com/notes.html")

    def test_handle_pkginfo_rejects_file_description_url(self):
        """Test that file description URLs are not fetched."""
        self.processor.env["pkginfo_keys_to_copy_from_sparkle_feed"] = ["description"]

        latest = {"description_url": "file:///etc/passwd"}

        with patch.object(self.processor, "fetch_content") as mock_fetch:
            with self.assertRaises(ProcessorError) as context:
                self.processor.handle_pkginfo(latest)

        self.assertIn("http(s) URL", str(context.exception))
        mock_fetch.assert_not_called()

    def test_handle_pkginfo_rejects_loopback_description_urls(self):
        """Test that loopback description URLs are not fetched."""
        self.processor.env["pkginfo_keys_to_copy_from_sparkle_feed"] = ["description"]

        loopback_urls = [
            "http://localhost/notes.html",
            "http://localhost./notes.html",
            "http://127.0.0.1/notes.html",
            "http://[::1]/notes.html",
        ]

        for url in loopback_urls:
            with self.subTest(url=url):
                latest = {"description_url": url}
                with patch.object(self.processor, "fetch_content") as mock_fetch:
                    with self.assertRaises(ProcessorError):
                        self.processor.handle_pkginfo(latest)

                mock_fetch.assert_not_called()

    def test_handle_pkginfo_rejects_relative_description_url(self):
        """Test that relative description URLs are not fetched."""
        self.processor.env["pkginfo_keys_to_copy_from_sparkle_feed"] = ["description"]

        latest = {"description_url": "/notes.html"}

        with patch.object(self.processor, "fetch_content") as mock_fetch:
            with self.assertRaises(ProcessorError) as context:
                self.processor.handle_pkginfo(latest)

        self.assertIn("http(s) URL", str(context.exception))
        mock_fetch.assert_not_called()

    def test_handle_pkginfo_with_description_data(self):
        """Test that handle_pkginfo formats inline description data."""
        self.processor.env["pkginfo_keys_to_copy_from_sparkle_feed"] = ["description"]

        latest = {"description_data": "Plain text notes"}

        with patch.object(self.processor, "output"):
            pkginfo = self.processor.handle_pkginfo(latest)

        self.assertEqual(
            pkginfo["description"], "<html><body>Plain text notes</body></html>"
        )

    def test_handle_pkginfo_with_minimum_os_version(self):
        """Test that handle_pkginfo copies minimum OS version."""
        self.processor.env["pkginfo_keys_to_copy_from_sparkle_feed"] = [
            "minimum_os_version"
        ]

        latest = {"minimum_os_version": "10.15"}

        pkginfo = self.processor.handle_pkginfo(latest)

        self.assertEqual(pkginfo["minimum_os_version"], "10.15")

    def test_handle_pkginfo_with_unsupported_key(self):
        """Test that handle_pkginfo ignores unsupported keys."""
        self.processor.env["pkginfo_keys_to_copy_from_sparkle_feed"] = [
            "unsupported_key"
        ]

        latest = {}

        with patch.object(self.processor, "output") as mock_output:
            pkginfo = self.processor.handle_pkginfo(latest)

        self.assertEqual(pkginfo, {})
        mock_output.assert_any_call(
            "Key unsupported_key isn't a supported key to copy from the "
            "Sparkle feed, ignoring it."
        )

    def test_handle_pkginfo_empty_when_no_keys_specified(self):
        """Test that handle_pkginfo returns empty dict when no keys specified."""
        latest = {"minimum_os_version": "10.15"}

        pkginfo = self.processor.handle_pkginfo(latest)

        self.assertEqual(pkginfo, {})

    # Test feed data retrieval
    def test_get_feed_data_with_query_pairs(self):
        """Test that get_feed_data adds query parameters."""
        self.processor.env["appcast_query_pairs"] = {"version": "latest", "os": "macos"}

        with patch.object(self.processor, "fetch_content") as mock_fetch:
            mock_fetch.return_value = b"<xml/>"

            self.processor.get_feed_data("https://example.com/appcast.xml")

            # Should have called fetch_content with URL containing query params
            call_args = mock_fetch.call_args[0][0]
            self.assertIn("version=latest", call_args)
            self.assertIn("os=macos", call_args)

    def test_get_feed_data_with_headers(self):
        """Test that get_feed_data passes request headers."""
        self.processor.env["appcast_request_headers"] = {"User-Agent": "AutoPkg"}

        with patch.object(self.processor, "fetch_content") as mock_fetch:
            mock_fetch.return_value = b"<xml/>"

            self.processor.get_feed_data("https://example.com/appcast.xml")

            # Should have called fetch_content with headers
            call_args = mock_fetch.call_args
            self.assertEqual(call_args[1]["headers"], {"User-Agent": "AutoPkg"})

    def test_fetch_content_calls_curl(self):
        """Test that fetch_content calls download_with_curl."""
        with patch.object(
            self.processor, "prepare_curl_cmd", return_value=["curl", "url"]
        ):
            with patch.object(
                self.processor, "download_with_curl", return_value=b"content"
            ) as mock_download:
                result = self.processor.fetch_content("https://example.com")

                self.assertEqual(result, b"content")
                mock_download.assert_called_once_with(["curl", "url"])

    # Test namespace handling
    def test_alternate_xmlns_url(self):
        """Test that alternate namespace URL is used when specified."""
        self.processor.env["alternate_xmlns_url"] = "http://custom.namespace/sparkle"

        # Mock the main method setup
        with patch.object(self.processor, "get_feed_data"):
            with patch.object(self.processor, "parse_feed_data", return_value=[]):
                try:
                    self.processor.main()
                except ProcessorError:
                    pass  # Expected due to empty items

        self.assertEqual(self.processor.xmlns, "http://custom.namespace/sparkle")

    # EdDSA signature metadata tests

    def _make_eddsa_appcast(
        self,
        ed_sig=None,
        dsa_sig=None,
        length="12345678",
        channel=None,
        xmlns="http://www.andymatuschak.org/xml-namespaces/sparkle",
    ):
        """Build an appcast XML with optional Sparkle signature attributes."""
        enc_attrs = 'url="https://example.com/app-2.0.0.dmg" sparkle:version="2000"'
        if length is not None:
            enc_attrs += f' length="{length}"'
        if ed_sig is not None:
            enc_attrs += f' sparkle:edSignature="{ed_sig}"'
        if dsa_sig is not None:
            enc_attrs += f' sparkle:dsaSignature="{dsa_sig}"'
        ch_elem = (
            f"\n            <sparkle:channel>{channel}</sparkle:channel>"
            if channel
            else ""
        )
        xml = f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:sparkle="{xmlns}">
  <channel>
    <item>
      <sparkle:version>2000</sparkle:version>
      <sparkle:shortVersionString>2.0.0</sparkle:shortVersionString>{ch_elem}
      <enclosure {enc_attrs} type="application/octet-stream" />
    </item>
  </channel>
</rss>"""
        return xml.encode("utf-8")

    def test_parse_feed_exposes_eddsa_signature(self):
        """EdDSA signature is captured from the enclosure."""
        xml = self._make_eddsa_appcast(ed_sig="AAAA")
        self.processor.xmlns = "http://www.andymatuschak.org/xml-namespaces/sparkle"
        items = self.processor.parse_feed_data(xml)
        self.assertEqual(items[0]["eddsa_signature"], "AAAA")

    def test_parse_feed_exposes_eddsa_signature_with_https_namespace(self):
        """The default Sparkle namespace lookup also accepts the https spelling."""
        xml = self._make_eddsa_appcast(
            ed_sig="AAAA",
            xmlns="https://www.andymatuschak.org/xml-namespaces/sparkle",
        )
        self.processor.xmlns = "http://www.andymatuschak.org/xml-namespaces/sparkle"
        items = self.processor.parse_feed_data(xml)
        self.assertEqual(items[0]["version"], "2000")
        self.assertEqual(items[0]["eddsa_signature"], "AAAA")

    def test_parse_feed_exposes_length_as_string(self):
        """Length is captured as a raw string, not cast to int."""
        xml = self._make_eddsa_appcast(ed_sig="AAAA", length="99999")
        self.processor.xmlns = "http://www.andymatuschak.org/xml-namespaces/sparkle"
        items = self.processor.parse_feed_data(xml)
        self.assertEqual(items[0]["eddsa_signature_length"], "99999")
        self.assertIsInstance(items[0]["eddsa_signature_length"], str)

    def test_parse_feed_no_eddsa_signature_unset(self):
        """eddsa_signature is absent when the enclosure has no edSignature."""
        xml = self._make_eddsa_appcast()
        self.processor.xmlns = "http://www.andymatuschak.org/xml-namespaces/sparkle"
        items = self.processor.parse_feed_data(xml)
        self.assertNotIn("eddsa_signature", items[0])

    def test_parse_feed_dsa_only_sets_marker(self):
        """DSA-only enclosure sets sparkle_dsa_signature_present boolean."""
        xml = self._make_eddsa_appcast(dsa_sig="DSASIG")
        self.processor.xmlns = "http://www.andymatuschak.org/xml-namespaces/sparkle"
        items = self.processor.parse_feed_data(xml)
        self.assertTrue(items[0].get("sparkle_dsa_signature_present"))
        self.assertNotIn("eddsa_signature", items[0])

    def test_parse_feed_dsa_only_sets_marker_with_https_namespace(self):
        """DSA-only detection also accepts the https Sparkle namespace spelling."""
        xml = self._make_eddsa_appcast(
            dsa_sig="DSASIG",
            xmlns="https://www.andymatuschak.org/xml-namespaces/sparkle",
        )
        self.processor.xmlns = "http://www.andymatuschak.org/xml-namespaces/sparkle"
        items = self.processor.parse_feed_data(xml)
        self.assertTrue(items[0].get("sparkle_dsa_signature_present"))
        self.assertNotIn("eddsa_signature", items[0])

    def test_parse_feed_both_sigs_no_dsa_marker(self):
        """DSA marker is not set when both EdDSA and DSA signatures are present."""
        xml = self._make_eddsa_appcast(ed_sig="EDSIG", dsa_sig="DSASIG")
        self.processor.xmlns = "http://www.andymatuschak.org/xml-namespaces/sparkle"
        items = self.processor.parse_feed_data(xml)
        self.assertNotIn("sparkle_dsa_signature_present", items[0])
        self.assertEqual(items[0]["eddsa_signature"], "EDSIG")

    def test_parse_feed_non_numeric_length_does_not_fail(self):
        """A non-numeric length value is captured as-is without error."""
        xml = self._make_eddsa_appcast(ed_sig="AAAA", length="notanumber")
        self.processor.xmlns = "http://www.andymatuschak.org/xml-namespaces/sparkle"
        items = self.processor.parse_feed_data(xml)
        self.assertEqual(items[0]["eddsa_signature_length"], "notanumber")

    def test_main_exposes_empty_eddsa_signature_when_present(self):
        """A present but empty EdDSA signature is exposed for verifier failure."""
        xml = self._make_eddsa_appcast(ed_sig="")
        with patch.object(self.processor, "get_feed_data", return_value=xml):
            self.processor.main()
        self.assertIn("eddsa_signature", self.processor.env)
        self.assertEqual(self.processor.env["eddsa_signature"], "")

    def test_main_exposes_empty_length_when_present(self):
        """A present but empty length is exposed for verifier failure."""
        xml = self._make_eddsa_appcast(ed_sig="SIGVALUE", length="")
        with patch.object(self.processor, "get_feed_data", return_value=xml):
            self.processor.main()
        self.assertIn("eddsa_signature_length", self.processor.env)
        self.assertEqual(self.processor.env["eddsa_signature_length"], "")

    def test_main_exposes_eddsa_signature_from_selected_item(self):
        """main() sets eddsa_signature in env from the selected (latest) item."""
        xml = self._make_eddsa_appcast(ed_sig="SIGVALUE")
        with patch.object(self.processor, "get_feed_data", return_value=xml):
            self.processor.main()
        self.assertEqual(self.processor.env.get("eddsa_signature"), "SIGVALUE")

    def test_main_dsa_only_sets_env_marker_and_warns(self):
        """main() sets sparkle_dsa_signature_present and emits a warning."""
        xml = self._make_eddsa_appcast(dsa_sig="DSASIG")
        with patch.object(self.processor, "get_feed_data", return_value=xml):
            with patch.object(self.processor, "output") as mock_output:
                self.processor.main()
        self.assertTrue(self.processor.env.get("sparkle_dsa_signature_present"))
        warning_calls = [
            str(c) for c in mock_output.call_args_list if "WARNING" in str(c)
        ]
        self.assertTrue(warning_calls, "Expected a WARNING output for DSA-only item")

    def test_main_eddsa_sig_uses_selected_channel_item(self):
        """EdDSA metadata comes from the item chosen after channel filtering."""
        xmlns = "http://www.andymatuschak.org/xml-namespaces/sparkle"
        xml = f"""<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:sparkle="{xmlns}">
  <channel>
    <item>
      <sparkle:version>2000</sparkle:version>
      <sparkle:channel>beta</sparkle:channel>
      <enclosure url="https://example.com/beta.dmg" sparkle:version="2000"
                 sparkle:edSignature="BETASIG" length="100"
                 type="application/octet-stream" />
    </item>
    <item>
      <sparkle:version>1000</sparkle:version>
      <enclosure url="https://example.com/stable.dmg" sparkle:version="1000"
                 sparkle:edSignature="STABLESIG" length="100"
                 type="application/octet-stream" />
    </item>
  </channel>
</rss>""".encode("utf-8")
        self.processor.env["update_channel"] = "beta"
        with patch.object(self.processor, "get_feed_data", return_value=xml):
            self.processor.main()
        self.assertEqual(self.processor.env.get("eddsa_signature"), "BETASIG")


if __name__ == "__main__":
    unittest.main()
