#!/usr/local/autopkg/python
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
"""
Regenerates the NuSpec XML schema Python wrapper module from upstream source.

Downloads the latest NuSpec XSD from the GitHub NuGet/NuGet.Client Git repository,
and creates a wrapper library using the `generateDS` utility.
"""
import os
import sys

# isort: off
# Ensure that we can find autopkglib no matter where we run this.
AUTOPKG_TOP: str = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "Code")
)
sys.path.insert(0, AUTOPKG_TOP)
# isort: on

import ssl
import subprocess
from argparse import ArgumentParser
from typing import List
from urllib.request import urlopen

from autopkglib import find_binary

SCHEMA_SOURCE_URL: str = (
    "https://raw.githubusercontent.com/NuGet/NuGet.Client"
    "/dev/src/NuGet.Core/NuGet.Packaging/compiler/resources/nuspec.xsd"
)

# Latest known version of the Nuspec XML schema namespace. Found by running `choco new`.
# Used because the schema source contains placeholders for the namespace.
SCHEMA_XMLNS: bytes = b"http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"


def get_schema_source(url: str, xmlns: bytes = SCHEMA_XMLNS) -> bytes:
    """Fetch the latest XML schema and replace `{0}` with the given XML namespace."""
    context = ssl.SSLContext()
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    context.load_default_certs()

    with urlopen(SCHEMA_SOURCE_URL, context=context) as res:
        return res.read().replace(b"{0}", xmlns)


def run_generateds(generateds_binary: str, output_path: str, schema_source: bytes):
    """Generate python wrapper library around the provided XML schema."""
    call_res = subprocess.run(
        [
            generateds_binary,
            # Enable using Python __slots__ object annotation to improve performance.
            "--member-specs=dict",
            "--enable-slots",
            # Generate methods to write to files and validate objects.
            "--export=write validate",
            # Do not prompt and force overwrite existing files.
            "--no-questions",
            "-f",
            "-o",
            output_path,
            "-",
        ],
        input=schema_source,
    )
    return call_res.returncode


def main(input_args: List[str]) -> int:
    parser = ArgumentParser(
        description="Regenerate the python wrapper library around the nuget xml schema."
    )
    parser.add_argument(
        "--output-path",
        help=(
            "Full path to the output file. "
            "Intermediate directories are created as needed."
        ),
        required=True,
    )
    parser.add_argument(
        "--generateds-binary",
        help="Path to generateDS. If not specified, defaults to looking in $env:PATH",
        default=None,
    )
    args = parser.parse_args(input_args)

    if args.generateds_binary is None:
        args.generateds_binary = find_binary("generateDS")

    if args.generateds_binary is None:
        print("ERROR: Unable to locate generateDS! Try passing --generateds-binary.")
        return 1

    # Create any directories as needed.
    output_dir = os.path.abspath(os.path.dirname(args.output_path))
    print(f"Generated output is being written to: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    return run_generateds(
        args.generateds_binary, args.output_path, get_schema_source(SCHEMA_SOURCE_URL)
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
