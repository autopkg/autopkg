#!/usr/local/autopkg/python
#
# Copyright 2021 Brandon Friess
# Copyright 2026 Rod Christiansen
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
"""Helper to deal with yaml serialization for autopkg and Munki pkginfo.

Provides utilities for reading, writing, and detecting Munki data in both
plist and yaml formats. Key ordering, type normalization, and block scalar
styles are designed to match the Munki yaml fork (yamlutils.swift).
"""

import base64
import os
import plistlib
import re
from collections import OrderedDict
from datetime import datetime

import yaml

# ---------------------------------------------------------------------------
# Loader: strip the float implicit resolver so version-like scalars
# (e.g. `version: 10.10`, `MinimumVersion: 2.3`) are parsed as strings
# directly, preserving trailing zeros and exact textual form.
#
# Same approach as autopkg/autopkg#1023 (@homebysix). Defined here under
# the same name so the two PRs converge on one class definition: whichever
# lands first owns the class, the other PR's diff for this section becomes
# a no-op on rebase.
# ---------------------------------------------------------------------------


class AutoPkgYAMLLoader(yaml.SafeLoader):
    """SafeLoader variant that does not auto-coerce float-looking scalars.

    Recipe inputs and Munki pkginfo fields like `version: 10.10` must
    arrive as strings. Post-parse coercion cannot recover trailing zeros
    that Pyyaml has already stripped, so we intervene at the resolver
    level the way Yams does on the Munki side (yamlutils.swift).
    """

    pass


# Strip the float implicit resolver so float-shaped scalars load as strings.
AutoPkgYAMLLoader.yaml_implicit_resolvers = {
    k: [(tag, regexp) for tag, regexp in v if tag != "tag:yaml.org,2002:float"]
    for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Keys whose values must always be strings even if yaml parses them as
# numeric (matches Munki's stringKeys set in yamlutils.swift).
STRING_KEYS = frozenset(
    {
        "version",
        "minimum_os_version",
        "maximum_os_version",
        "minimum_munki_version",
        "minimum_update_version",
        "installer_item_version",
        "installed_version",
        "product_version",
        "CFBundleShortVersionString",
        "CFBundleVersion",
        "minosversion",
    }
)

# Script keys that should use yaml literal block scalar style (|).
SCRIPT_KEYS = frozenset(
    {
        "preinstall_script",
        "postinstall_script",
        "installcheck_script",
        "uninstallcheck_script",
        "postuninstall_script",
        "uninstall_script",
        "preuninstall_script",
        "version_script",
        "embedded_script",
    }
)

# Prose keys that should use yaml folded block scalar style (>).
PROSE_KEYS = frozenset({"description", "notes"})

# Top-level pkginfo key ordering: these come first in this order,
# then all remaining keys alphabetically, then _metadata last.
_PKGINFO_HEAD_KEYS = ["name", "display_name", "version"]

# Receipt sub-dict key ordering.
_RECEIPT_HEAD_KEYS = [
    "packageid",
    "name",
    "filename",
    "installed_size",
    "version",
    "optional",
]

# Installs sub-dict key ordering.
_INSTALLS_HEAD_KEYS = [
    "path",
    "type",
    "CFBundleIdentifier",
    "CFBundleName",
    "CFBundleShortVersionString",
    "CFBundleVersion",
    "md5checksum",
    "minosversion",
]


# ---------------------------------------------------------------------------
# Existing representer (unchanged from original)
# ---------------------------------------------------------------------------


def autopkg_str_representer(dumper, data):
    """Makes every multiline string a block literal"""
    if len(data.splitlines()) > 1:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


# ---------------------------------------------------------------------------
# Key-ordering helpers
# ---------------------------------------------------------------------------


def _sorted_keys(d, head_keys):
    """Return keys of *d* ordered: head_keys first (if present),
    remaining keys alphabetically, ``_metadata`` last."""
    head = [k for k in head_keys if k in d]
    rest = sorted(k for k in d if k not in head_keys and k != "_metadata")
    tail = ["_metadata"] if "_metadata" in d else []
    return head + rest + tail


def _detect_subdict_type(d):
    """Heuristic to detect whether *d* is a receipt, installs item, or
    generic pkginfo dict.  Returns head-key list for ordering."""
    if "packageid" in d:
        return _RECEIPT_HEAD_KEYS
    if "path" in d and "type" in d:
        return _INSTALLS_HEAD_KEYS
    return _PKGINFO_HEAD_KEYS


# ---------------------------------------------------------------------------
# Type normalization (read path)
# ---------------------------------------------------------------------------


def _is_numeric_string(value):
    """Return True if *value* is a float or int that should be coerced to str."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _clean_float_to_str(value):
    """Convert a numeric value to a clean version string.
    Matches Munki's String(format: '%.10g') behaviour."""
    if isinstance(value, float):
        formatted = f"{value:.10g}"
        return formatted
    return str(value)


def _normalize_yaml_types(data, parent_key=None):
    """Recursively walk parsed yaml data and coerce numeric values back to
    strings for keys in STRING_KEYS.  Operates in-place and returns *data*."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key in STRING_KEYS and _is_numeric_string(value):
                data[key] = _clean_float_to_str(value)
            elif isinstance(value, dict):
                _normalize_yaml_types(value, key)
            elif isinstance(value, list):
                _normalize_yaml_types(value, key)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if parent_key in STRING_KEYS and _is_numeric_string(item):
                data[i] = _clean_float_to_str(item)
            elif isinstance(item, (dict, list)):
                _normalize_yaml_types(item, parent_key)
    return data


# ---------------------------------------------------------------------------
# Custom yaml Dumper for Munki pkginfo
# ---------------------------------------------------------------------------


class _LiteralStr(str):
    """Marker for strings that should use yaml literal block style (|)."""

    pass


class _FoldedStr(str):
    """Marker for strings that should use yaml folded block style (>)."""

    pass


class _QuotedStr(str):
    """Marker for strings that must be quoted (version numbers etc)."""

    pass


def _literal_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


def _folded_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=">")


def _quoted_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="'")


# Regex for values yaml might interpret as non-string (numbers, booleans, etc).
_NEEDS_QUOTING_RE = re.compile(
    r"""^(?:
        # integers / floats / scientific notation
        [-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?
        # yaml booleans
        |true|false|yes|no|on|off
        # yaml null
        |null|~
        # Sexagesimal (60-base) time values like 1:30
        |\d+:\d+(?::\d+)?
    )$""",
    re.VERBOSE | re.IGNORECASE,
)


def _looks_like_script(value):
    """Heuristic: does the string look like a script?"""
    patterns = ["#!", "\nif ", "\nfor ", "\necho ", "\nprint(", "\n  ", "\n\t"]
    return any(p in value for p in patterns)


def _prepare_value(key, value):
    """Wrap a value with the appropriate marker type for yaml serialization."""
    if value is None:
        return None
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, str):
        if key in STRING_KEYS and _NEEDS_QUOTING_RE.match(value):
            return _QuotedStr(value)
        if "\n" in value or value.endswith("\n"):
            if key in SCRIPT_KEYS or _looks_like_script(value):
                return _LiteralStr(value)
            if key in PROSE_KEYS:
                return _FoldedStr(value)
            # Default multiline: literal
            return _LiteralStr(value)
        if _NEEDS_QUOTING_RE.match(value):
            return _QuotedStr(value)
        return value
    return value


def _prepare_dict(d):
    """Recursively prepare a dict for yaml serialization: order keys, tag
    strings, filter None/empty, handle nested structures."""
    head_keys = _detect_subdict_type(d)
    ordered = OrderedDict()
    for key in _sorted_keys(d, head_keys):
        value = d[key]
        # Filter None (match Munki's behaviour). Preserve empty strings as
        # explicitly-quoted empties — matches yamlutils.swift, which emits
        # `key: ''` (single-quoted, str-tagged) so an empty value survives
        # round-trip rather than being silently dropped or read back as null.
        if value is None:
            continue
        if isinstance(value, str) and value == "":
            ordered[key] = _QuotedStr("")
            continue
        if isinstance(value, dict):
            value = _prepare_dict(value)
        elif isinstance(value, list):
            value = _prepare_list(key, value)
        else:
            value = _prepare_value(key, value)
            if value is None:
                continue
        ordered[key] = value
    return ordered


def _prepare_list(parent_key, lst):
    """Recursively prepare a list for yaml serialization."""
    result = []
    for item in lst:
        if item is None:
            continue
        if isinstance(item, dict):
            result.append(_prepare_dict(item))
        elif isinstance(item, list):
            result.append(_prepare_list(parent_key, item))
        else:
            prepared = _prepare_value(parent_key, item)
            if prepared is not None:
                result.append(prepared)
    return result


class MunkiPkginfoDumper(yaml.SafeDumper):
    """yaml dumper configured for Munki pkginfo output."""

    pass


# Register representers on the custom dumper.
MunkiPkginfoDumper.add_representer(_LiteralStr, _literal_representer)
MunkiPkginfoDumper.add_representer(_FoldedStr, _folded_representer)
MunkiPkginfoDumper.add_representer(_QuotedStr, _quoted_representer)
MunkiPkginfoDumper.add_representer(
    OrderedDict,
    lambda dumper, data: dumper.represent_mapping(
        "tag:yaml.org,2002:map", data.items()
    ),
)


# ---------------------------------------------------------------------------
# Public API: write
# ---------------------------------------------------------------------------


def dump_pkginfo_yaml(pkginfo, f):
    """Serialize a Munki pkginfo dict to yaml and write to file handle *f*.

    *f* must be open for writing in text mode; unicode output is enabled
    via ``allow_unicode=True``."""
    prepared = _prepare_dict(pkginfo)
    yaml.dump(
        prepared,
        f,
        Dumper=MunkiPkginfoDumper,
        default_flow_style=False,
        allow_unicode=True,
        width=10000,  # effectively disable line wrapping
        indent=2,
        sort_keys=False,
    )


def dumps_pkginfo_yaml(pkginfo):
    """Serialize a Munki pkginfo dict to a yaml string."""
    prepared = _prepare_dict(pkginfo)
    return yaml.dump(
        prepared,
        Dumper=MunkiPkginfoDumper,
        default_flow_style=False,
        allow_unicode=True,
        width=10000,
        indent=2,
        sort_keys=False,
    )


# ---------------------------------------------------------------------------
# Public API: read
# ---------------------------------------------------------------------------


def load_pkginfo_yaml(f):
    """Load a Munki pkginfo dict from a yaml file handle.

    Uses AutoPkgYAMLLoader to keep float-shaped scalars as strings, then
    runs _normalize_yaml_types as a defence-in-depth pass for any
    integer-shaped scalars that should also be strings."""
    data = yaml.load(f, Loader=AutoPkgYAMLLoader)
    if isinstance(data, (dict, list)):
        _normalize_yaml_types(data)
    return data


def loads_pkginfo_yaml(data):
    """Load a Munki pkginfo dict from yaml bytes or string.

    Uses AutoPkgYAMLLoader to keep float-shaped scalars as strings, then
    runs _normalize_yaml_types as a defence-in-depth pass for any
    integer-shaped scalars that should also be strings."""
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    result = yaml.load(data, Loader=AutoPkgYAMLLoader)
    if isinstance(result, (dict, list)):
        _normalize_yaml_types(result)
    return result


# ---------------------------------------------------------------------------
# Public API: format detection
# ---------------------------------------------------------------------------


def is_yaml_path(path):
    """Return True if *path* has a yaml file extension."""
    _, ext = os.path.splitext(path)
    return ext.lower() in (".yaml", ".yml")


def is_plist_path(path):
    """Return True if *path* has a plist file extension."""
    _, ext = os.path.splitext(path)
    return ext.lower() == ".plist"


def detect_munki_format(file_path):
    """Detect whether a Munki data file is yaml or plist.

    Returns ``"yaml"`` or ``"plist"``.

    Detection order:
    1. File extension (``.yaml``/``.yml`` -> yaml, ``.plist`` -> plist)
    2. Content detection (``<?xml`` / ``<plist>`` -> plist, ``---`` / ``key: value`` -> yaml)
    3. Default: ``"plist"``
    """
    if is_yaml_path(file_path):
        return "yaml"
    if is_plist_path(file_path):
        return "plist"
    # Content-based detection for extensionless files
    try:
        with open(file_path, "rb") as f:
            head = f.read(512)
    except OSError:
        return "plist"
    head_str = head.decode("utf-8", errors="replace").lstrip()
    if head_str.startswith("<?xml") or head_str.startswith("<plist"):
        return "plist"
    if head_str.startswith("---"):
        return "yaml"
    # Count yaml-like vs XML-like lines in the first few lines
    lines = head_str.splitlines()[:10]
    yaml_score = sum(1 for ln in lines if re.match(r"^\w[\w\s]*:", ln))
    xml_score = sum(1 for ln in lines if re.match(r"^\s*<", ln))
    if yaml_score > xml_score:
        return "yaml"
    return "plist"


def load_munki_file(file_path):
    """Load a Munki data file (pkginfo, catalog, manifest) from *file_path*,
    auto-detecting whether it is yaml or plist.

    Returns the parsed dict or list."""
    fmt = detect_munki_format(file_path)
    if fmt == "yaml":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.load(f, Loader=AutoPkgYAMLLoader)
            if isinstance(data, (dict, list)):
                _normalize_yaml_types(data)
            return data
        except Exception:
            # Fall back to plist
            with open(file_path, "rb") as f:
                return plistlib.load(f)
    else:
        try:
            with open(file_path, "rb") as f:
                return plistlib.load(f)
        except Exception:
            # Fall back to yaml
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.load(f, Loader=AutoPkgYAMLLoader)
            if isinstance(data, (dict, list)):
                _normalize_yaml_types(data)
            return data


def save_munki_file(data, file_path):
    """Save a Munki data dict to *file_path* in the format implied by
    the file extension (yaml for ``.yaml``/``.yml``, plist otherwise)."""
    if is_yaml_path(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            dump_pkginfo_yaml(data, f)
    else:
        with open(file_path, "wb") as f:
            plistlib.dump(data, f)


def parse_munki_data(data_bytes):
    """Parse bytes that could be either plist or yaml (e.g. makepkginfo stdout).

    Tries plist first, falls back to yaml.  Returns the parsed dict."""
    try:
        return plistlib.loads(data_bytes)
    except Exception:
        pass
    text = data_bytes.decode("utf-8") if isinstance(data_bytes, bytes) else data_bytes
    result = yaml.load(text, Loader=AutoPkgYAMLLoader)
    if isinstance(result, (dict, list)):
        _normalize_yaml_types(result)
    return result
