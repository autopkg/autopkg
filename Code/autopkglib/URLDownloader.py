#!/usr/local/autopkg/python
#
# Refactoring 2018 Michal Moravec
# Copyright 2015 Greg Neagle
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

"""See docstring for URLDownloader class"""

import json
import os.path
import platform
import tempfile
from hashlib import md5, sha1, sha256
from typing import Any, NoReturn

from autopkglib import BUNDLE_ID, ProcessorError, xattr
from autopkglib.URLGetter import URLGetter

__all__ = ["URLDownloader"]


class URLDownloader(URLGetter):
    """Downloads a URL to the specified download_dir using curl."""

    description = __doc__
    lifecycle = {"introduced": "0.1.0"}
    input_variables = {
        "url": {"required": True, "description": "The URL to download."},
        "request_headers": {
            "required": False,
            "description": (
                "Optional dictionary of headers to include with the download request."
            ),
        },
        "curl_opts": {
            "required": False,
            "description": (
                "Optional array of options to include with the download request."
            ),
        },
        "download_dir": {
            "required": False,
            "description": (
                "The directory where the file will be downloaded to. Defaults "
                "to RECIPE_CACHE_DIR/downloads."
            ),
        },
        "filename": {
            "required": False,
            "description": "Filename to override the URL's tail.",
        },
        "prefetch_filename": {
            "required": False,
            "description": (
                "If True, URLDownloader attempts to determine filename from HTTP "
                "headers downloaded before the file itself. 'prefetch_filename' "
                "overrides 'filename' option. Filename is determined from the first "
                "available source of information in this order:\n"
                "\t1. Content-Disposition header\n"
                "\t2. Location header\n"
                "\t3. 'filename' option (if set)\n"
                "\t4. last part of 'url'.  \n"
                "'prefetch_filename' is useful for URLs with redirects."
            ),
            "default": False,
        },
        "CHECK_FILESIZE_ONLY": {
            "required": False,
            "description": (
                "If True, a server's ETag and Last-Modified "
                "headers will not be checked to verify whether "
                "a download is newer than a cached item, and only "
                "Content-Length (filesize) will be used. This "
                "is useful for cases where a download always "
                "redirects to different mirrors, which could "
                "cause items to be needlessly re-downloaded. "
                "Defaults to False."
            ),
            "default": False,
        },
        "PKG": {
            "required": False,
            "description": (
                "Local path to the pkg/dmg we'd otherwise download. "
                "If provided, the download is skipped and we just use "
                "this package or disk image."
            ),
        },
        "COMPUTE_HASHES": {
            "required": False,
            "default": False,
            "description": (
                "Determine whether to compute md5, sha1, and sha256 hashes of "
                "the downloaded file."
            ),
        },
        "HEADERS_TO_TEST": {
            "required": False,
            "description": (
                "List of HTTP headers to compare against the previous download "
                "to detect changes. Their values are persisted in .info.json. "
                "If 'CHECK_FILESIZE_ONLY' is enabled, only Content-Length is used."
            ),
            "default": ["ETag", "Last-Modified", "Content-Length"],
        },
        "download_missing_file": {
            "required": False,
            "description": (
                "If the file is missing but matching metadata is present, "
                "download the file again. Defaults to True as most current "
                "recipes expect the files to be present. This re-fetch does "
                "not mark the item as changed (download_changed stays false); "
                "download_changed reflects the remote resource only. A missing "
                "or null value uses the default; a blank string disables it."
            ),
            "default": True,
        },
    }
    output_variables = {
        "pathname": {"description": "Path to the downloaded file."},
        "last_modified": {
            "description": "last-modified header for the downloaded item."
        },
        "etag": {"description": "etag header for the downloaded item."},
        "download_url": {
            "description": "The final URL the file was downloaded from (after redirects)."
        },
        "download_changed": {
            "description": (
                "Boolean indicating if the download has changed since the "
                "last time it was downloaded."
            )
        },
        "download_info": {"description": "Info from previous or current download."},
        "file_sha1": {"description": "SHA-1 hash of the downloaded file."},
        "file_sha256": {"description": "SHA-256 hash of the downloaded file."},
        "file_md5": {"description": "MD5 hash of the downloaded file."},
        "url_downloader_summary_result": {
            "description": "Description of interesting results."
        },
    }

    def getxattr(self, attr) -> NoReturn:
        """Removed — metadata is now stored in .info.json. Use get_metadata() instead."""
        raise ProcessorError(
            "getxattr() has been removed from URLDownloader. "
            "Use get_metadata() to read cached download metadata."
        )

    def env_bool(self, key: str, default: bool = False) -> bool:
        """Return a boolean for AutoPkg env values that may arrive as strings."""
        if key not in self.env:
            return default

        value = self.env[key]
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalised = value.strip().lower()
            if normalised in ("true", "yes", "on", "1"):
                return True
            if normalised in ("false", "no", "off", "0", ""):
                return False

        message = (
            f"{key} must be a boolean or boolean-like string "
            f"(true/false, yes/no, on/off, 1/0), not {value!r}"
        )
        if key == "prefetch_filename":
            message += "; use filename to override the downloaded filename"
        raise ProcessorError(message)

    def prepare_base_curl_cmd(self) -> list[str]:
        """Assemble base curl command and return it."""
        curl_cmd = [
            self.curl_binary(),
            "--silent",
            "--show-error",
            "--no-buffer",
            "--dump-header",
            "-",
            "--speed-time",
            "30",
            "--location",
            "--url",
            self.env["url"],
        ]

        return curl_cmd

    def clear_zero_file(self, pathname) -> None:
        """If file already exists and the size is 0, discard it to download again."""
        if os.path.exists(pathname) and os.path.getsize(pathname) == 0:
            os.remove(pathname)

    def prepare_download_curl_cmd(self, pathname_temporary) -> list[str]:
        """Assemble file download curl command and return it."""
        curl_cmd = self.prepare_base_curl_cmd()
        curl_cmd.extend(["--fail", "--output", pathname_temporary])
        # Add the common options
        self.add_curl_common_opts(curl_cmd)
        # Clear out a potentially zero-byte file
        self.clear_zero_file(self.env["pathname"])
        self.add_curl_headers(curl_cmd, self.produce_etag_headers())
        return curl_cmd

    def produce_etag_headers(self) -> dict[str, str]:  # type: ignore[override]
        """Produce a dict of curl headers containing etag headers from the download."""
        headers = {}
        # If the download file already exists and CHECK_FILESIZE_ONLY is not
        # set, add etag/last-modified headers so we skip re-downloading
        # unchanged content.
        if os.path.exists(self.env["pathname"]):
            metadata = self.get_metadata()
            if not self.env_bool("CHECK_FILESIZE_ONLY"):
                http_headers: dict[str, Any] = metadata.get("http_headers", {})
                if etag := http_headers.get("ETag"):
                    headers["If-None-Match"] = etag
                if last_modified := http_headers.get("Last-Modified"):
                    headers["If-Modified-Since"] = last_modified
        return headers

    def clear_vars(self) -> None:
        """Clear and initialize variables."""
        # Delete summary result if exists
        if "url_downloader_summary_result" in self.env:
            del self.env["url_downloader_summary_result"]

        # XATTR names for Etag and Last-Modified headers
        if platform.platform().startswith("Linux"):
            self.xattr_etag = f"user.{BUNDLE_ID}.etag"
            self.xattr_last_modified = f"user.{BUNDLE_ID}.last-modified"
        else:
            self.xattr_etag = f"{BUNDLE_ID}.etag"
            self.xattr_last_modified = f"{BUNDLE_ID}.last-modified"

        self.env["file_size"] = 0
        self.env["last_modified"] = ""
        self.env["etag"] = ""
        self.env["download_url"] = ""

    def prefetch_filename(self) -> str | None:
        """Attempt to find filename in HTTP headers."""
        curl_cmd = self.prepare_base_curl_cmd()
        curl_cmd.extend(["--head"])
        # Add the common options
        self.add_curl_common_opts(curl_cmd)

        raw_headers = self.download_with_curl(curl_cmd)
        header = self.parse_headers(raw_headers)
        content_disposition = header.get("content-disposition", "") or ""
        redirected_url = header.get("http_redirected")

        if "filename=" in content_disposition:
            filename = content_disposition.rpartition("filename=")[2].replace('"', "")
            filename = os.path.basename(filename.replace("\\", "/"))
            self.output(
                f"Filename prefetched from the HTTP Content-Disposition header: {filename}",
                verbose_level=2,
            )
        elif redirected_url:
            filename = redirected_url.rpartition("/")[2]
            self.output(
                f"Filename prefetched from the HTTP Location header: {filename}",
                verbose_level=2,
            )
        else:
            self.output(
                "Unable to find filename in the HTTP headers during prefetch",
                verbose_level=2,
            )
            return None

        return filename

    def get_filename(self) -> str | None:
        """Obtain filename from PKG variable or URL."""
        if "PKG" in self.env:
            self.env["pathname"] = os.path.expanduser(self.env["PKG"])
            self.env["download_changed"] = True
            self.output(f"Given {self.env['pathname']}, no download needed.")
            return None

        if self.env_bool("prefetch_filename"):
            filename = self.prefetch_filename()
            if filename:
                return filename

        if "filename" in self.env:
            filename = self.env["filename"]
        else:
            # Generate filename from URL.
            filename = self.env["url"].rpartition("/")[2]

        return filename

    def get_download_dir(self) -> str:
        """Create download dir and return its path."""
        download_dir = self.env.get("download_dir") or os.path.join(
            self.env["RECIPE_CACHE_DIR"], "downloads"
        )
        if not os.path.exists(download_dir):
            try:
                os.makedirs(download_dir)
            except OSError as err:
                raise ProcessorError(f"Can't create {download_dir}: {err.strerror}")
        return download_dir

    def get_metadata(self) -> dict[str, Any]:
        """Retrieve metadata from .info.json, or return empty dict if missing or unreadable."""
        pathname_info_json = self.env["pathname"] + ".info.json"

        try:
            with open(pathname_info_json, "r", encoding="utf-8") as infile:
                metadata = json.load(infile)
            self.output("Reading metadata from Info JSON.", 2)
            self.output(f"Info JSON contents: {metadata}", 2)
            return metadata
        except FileNotFoundError:
            return {}
        except (OSError, json.JSONDecodeError) as err:
            self.output(
                f"WARNING: Could not read {pathname_info_json} "
                f"({type(err).__name__}): {err}. Continuing with empty metadata."
            )
            return {}

    def compute_hashes(self) -> dict[str, str]:
        """Compute and return SHA-1, SHA-256, and MD5 hashes of the downloaded file."""
        sha1_hasher = sha1()
        sha256_hasher = sha256()
        md5_hasher = md5()

        with open(self.env["pathname"], "rb") as infile:
            for chunk in iter(lambda: infile.read(4096 * 100), b""):
                sha1_hasher.update(chunk)
                sha256_hasher.update(chunk)
                md5_hasher.update(chunk)

        return {
            "sha1": sha1_hasher.hexdigest(),
            "sha256": sha256_hasher.hexdigest(),
            "md5": md5_hasher.hexdigest(),
        }

    def store_hashes_in_env(self, hashes: dict[str, str]) -> None:
        """Store computed hashes for downstream processors."""
        self.env["file_sha1"] = hashes["sha1"]
        self.env["file_sha256"] = hashes["sha256"]
        self.env["file_md5"] = hashes["md5"]

    def publish_existing_hashes(self) -> None:
        """Expose hashes on a cache hit without failing on a missing file.

        Computes from the cached file when present; otherwise reuses the hashes
        stored in ``.info.json``. When neither is available it warns and skips,
        so a metadata-only cache hit never crashes on an absent file.
        """
        if not self.env_bool("COMPUTE_HASHES"):
            return
        hash_keys = ("file_sha1", "file_sha256", "file_md5")
        if os.path.isfile(self.env["pathname"]):
            self.store_hashes_in_env(self.compute_hashes())
            return
        metadata = self.env.get("download_info") or {}
        if all(metadata.get(key) for key in hash_keys):
            for key in hash_keys:
                self.env[key] = metadata[key]
            self.output("Reusing hashes from .info.json (cached file absent).", 2)
        else:
            self.output(
                "WARNING: COMPUTE_HASHES is set but the cached file is absent "
                "and no stored hashes were found in .info.json; skipping hashes."
            )

    def create_temp_file(self, download_dir) -> str:
        """Create temporary file and return its path."""
        temporary_file = tempfile.NamedTemporaryFile(dir=download_dir, delete=False)
        pathname_temporary = temporary_file.name
        # Set permissions on the temp file as curl would set for a newly-downloaded
        # file. NamedTemporaryFile uses mkstemp(), which sets a mode of 0600, and
        # this can cause issues if this item is eventually copied to a Munki repo
        # with the same permissions and the file is inaccessible by (for example)
        # the webserver.
        os.chmod(pathname_temporary, 0o644)
        return pathname_temporary

    def publish_download_info(self, metadata: dict[str, Any]) -> None:
        """Expose cached download metadata for downstream processors."""
        if not metadata:
            return

        self.env["download_info"] = metadata
        previous_http_headers = metadata.get("http_headers", {})
        self.env["last_modified"] = previous_http_headers.get("Last-Modified", "")
        self.env["etag"] = previous_http_headers.get("ETag", "")
        self.env["download_url"] = metadata.get("download_url", "")

    @staticmethod
    def header_value(headers, header_name: str) -> Any:
        """Return an HTTP header value without regard to name casing."""
        return next(
            (
                value
                for name, value in headers.items()
                if name.lower() == header_name.lower()
            ),
            None,
        )

    def download_headers(self, header, file_size: int) -> dict[str, Any]:
        """Return the response headers persisted for future change checks."""
        names = list(self.input_variables["HEADERS_TO_TEST"]["default"])
        names.extend(self.env.get("HEADERS_TO_TEST") or [])
        canonical_names = {
            "content-length": "Content-Length",
            "etag": "ETag",
            "last-modified": "Last-Modified",
        }
        return {
            canonical_names.get(name.lower(), name): (
                file_size
                if name.lower() == "content-length"
                else self.header_value(header, name) or ""
            )
            for name in names
        }

    def download_changed(self, header) -> bool:
        """Return True if the remote item differs from the cached metadata.

        This is a pure version check against the stored ``.info.json``: it does
        not depend on whether the cached file is present on disk, and it does
        not force a download for a missing file. Re-fetching a file that has
        gone missing is handled in ``main()`` via ``download_missing_file``.
        """
        metadata = self.get_metadata()
        self.publish_download_info(metadata)

        if self.header_value(header, "http_result_code") == "304":
            # resource not modified
            self.output("Item at URL is unchanged.")
            return False

        headers_to_test = (
            self.env.get("HEADERS_TO_TEST")
            or self.input_variables["HEADERS_TO_TEST"]["default"]
        )
        if self.env_bool("CHECK_FILESIZE_ONLY"):
            headers_to_test = ["Content-Length"]

        previous_download_path = self.env.get("pathname")
        previous_download_exists = bool(
            previous_download_path and os.path.isfile(previous_download_path)
        )
        existing_file_size = (
            os.path.getsize(previous_download_path)
            if previous_download_exists
            else None
        )

        header_matches = 0
        for header_name in headers_to_test:
            previous_header = self.header_value(
                metadata.get("http_headers", {}), header_name
            )
            current_header = self.header_value(header, header_name)
            if header_name.lower() == "content-length":
                if existing_file_size is not None:
                    previous_header = existing_file_size
                try:
                    if int(previous_header) != int(current_header):
                        self.output("Content-Length is different", 2)
                        return True
                    header_matches += 1
                except (TypeError, ValueError) as err:
                    self.output(
                        "WARNING: 'Content-Length' missing. "
                        f"({type(err).__name__}) {err}",
                        1,
                    )
                continue

            if current_header is None and previous_header in ("", None):
                continue
            if previous_header is None:
                self.output(f"WARNING: header missing. (KeyError) {header_name}", 1)
                continue
            if previous_header != current_header:
                self.output(f"{header_name} is different", 2)
                return True
            header_matches += 1

        if header_matches:
            return False

        # If Content-Length header is present and we had a cached
        # file, see if it matches the size of the cached file.
        # Useful for webservers that don't provide Last-Modified
        # and ETag headers.
        if not self.header_value(header, "etag") and not self.header_value(
            header, "last-modified"
        ):
            size_header = self.header_value(header, "content-length")
            try:
                size_matches = (
                    size_header is not None
                    and existing_file_size is not None
                    and int(size_header) == existing_file_size
                )
            except (TypeError, ValueError) as err:
                self.output(
                    f"WARNING: 'Content-Length' invalid. ({type(err).__name__}) {err}",
                    1,
                )
                size_matches = False
            if size_matches:
                self.output(
                    "File size returned by webserver matches that "
                    f"of the cached file: {size_header} bytes"
                )
                self.output(
                    "WARNING: Matching a download by filesize is a "
                    "fallback mechanism that does not guarantee "
                    "that a build is unchanged."
                )
                return False

        return True

    def move_temp_file(self, pathname_temporary) -> None:
        """Move temporary download file to pathname."""
        if os.path.exists(self.env["pathname"]):
            os.remove(self.env["pathname"])
        try:
            os.rename(pathname_temporary, self.env["pathname"])
        except OSError:
            raise ProcessorError(
                f"Can't move {pathname_temporary} to {self.env['pathname']}"
            )

    def store_headers(self, header) -> None:
        """Store last-modified and etag headers in pathname xattr."""
        if header.get("last-modified"):
            xattr.setxattr(
                self.env["pathname"],
                self.xattr_last_modified,
                header.get("last-modified").encode(),
            )
            self.output(
                f"Storing new Last-Modified header: {header.get('last-modified')}"
            )
        if header.get("etag"):
            xattr.setxattr(
                self.env["pathname"], self.xattr_etag, header.get("etag").encode()
            )
            self.output(f"Storing new ETag header: {header.get('etag')}")

    def store_metadata(self, header: dict[str, Any]) -> None:
        """Write download metadata to .info.json and preserve legacy xattr metadata."""
        self.env["file_size"] = os.path.getsize(self.env["pathname"])
        http_headers = self.download_headers(header, self.env["file_size"])
        self.env["etag"] = http_headers["ETag"]
        self.env["last_modified"] = http_headers["Last-Modified"]
        self.env["download_url"] = (
            self.header_value(header, "http_redirected") or self.env["url"]
        )

        metadata_dict: dict[str, Any] = {
            "download_url": self.env["download_url"],
            "file_name": os.path.basename(self.env["pathname"]),
            "file_size": self.env["file_size"],
            "http_headers": http_headers,
        }
        if self.env_bool("COMPUTE_HASHES"):
            self.store_hashes_in_env(self.compute_hashes())
            metadata_dict.update(
                {
                    "file_sha1": self.env["file_sha1"],
                    "file_sha256": self.env["file_sha256"],
                    "file_md5": self.env["file_md5"],
                }
            )

        self.write_metadata(metadata_dict)

        # Preserve legacy xattr metadata for callers that still read it.
        self.store_headers(header)

    def write_metadata(self, metadata: dict[str, Any]) -> None:
        """Write download metadata atomically to the .info.json sidecar."""
        self.env["download_info"] = metadata
        pathname_info_json = self.env["pathname"] + ".info.json"
        metadata_str = json.dumps(metadata, indent=4, sort_keys=True)

        # Write metadata atomically to avoid partial-write corruption
        self.output(f"Storing metadata to {pathname_info_json}")
        self.output(f"Metadata contents:\n{metadata_str}", verbose_level=2)
        dir_name = os.path.dirname(self.env["pathname"])
        with tempfile.NamedTemporaryFile(
            "w", dir=dir_name, delete=False, suffix=".tmp", encoding="utf-8"
        ) as tmp:
            tmp.write(metadata_str)
            tmp_path = tmp.name
        try:
            os.replace(tmp_path, pathname_info_json)
        except OSError:
            os.remove(tmp_path)
            raise

    def report_download(self, version_changed: bool) -> None:
        """Report a new download or the replacement of a missing cached file."""
        if version_changed:
            message = f"Downloaded {self.env['pathname']}"
            summary = "The following new items were downloaded:"
        else:
            message = f"Re-downloaded missing file: {self.env['pathname']}"
            summary = "The following missing items were re-downloaded:"
        self.output(message)
        self.env["url_downloader_summary_result"] = {
            "summary_text": summary,
            "data": {"download_path": self.env["pathname"]},
        }

    def main(self) -> None:
        # Clear and initialize data structures
        self.clear_vars()

        # Ensure existence of necessary files, directories and paths
        filename = self.get_filename()
        if filename is None:
            return
        download_dir = self.get_download_dir()
        self.env["pathname"] = os.path.join(download_dir, filename)
        pathname_temporary = self.create_temp_file(download_dir)

        # Prepare curl command
        curl_cmd = self.prepare_download_curl_cmd(pathname_temporary)

        # Execute curl command and parse headers
        raw_headers = self.download_with_curl(curl_cmd)
        header = self.parse_headers(raw_headers)

        # download_changed reflects the remote resource only (remote vs .info.json).
        version_changed = self.download_changed(header)
        self.env["download_changed"] = version_changed

        # download_missing_file only decides whether to re-fetch a file that
        # has gone missing while the remote resource is unchanged; it never changes
        # download_changed.
        previous_download_exists = os.path.isfile(self.env["pathname"])
        materialize_missing = not previous_download_exists and self.env_bool(
            "download_missing_file", default=True
        )

        if not version_changed and not materialize_missing:
            # Unchanged: keep the cached file, or skip entirely when it is
            # absent and download_missing_file is false.
            os.remove(pathname_temporary)
            self.publish_existing_hashes()
            if previous_download_exists:
                self.output(f"Using existing {self.env['pathname']}")
            return

        # Either the remote changed, or the file was missing and we have been
        # told to re-fetch it. Either way, keep the freshly downloaded bytes.
        self.move_temp_file(pathname_temporary)

        # Save .info.json metadata and legacy last-modified/etag xattrs.
        self.store_metadata(header)

        self.report_download(version_changed)


if __name__ == "__main__":
    PROCESSOR = URLDownloader()
    PROCESSOR.execute_shell()
