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

import optparse
from typing import List, Tuple

from autopkglib.prefs import globalPreferences


def gen_common_parser() -> optparse.OptionParser:
    """Generate a common optparse parser with default options."""
    parser = optparse.OptionParser()
    parser.add_option("--prefs", dest="file_path")
    return parser


def common_parse(
    parser: optparse.OptionParser, argv: List[str]
) -> Tuple[optparse.Values, List[str]]:
    """Parse an optparse parser with some enhancements and return a tuple."""
    options, arguments = parser.parse_args(argv[2:])
    if options.file_path:
        # Attempt to set the global preferences
        globalPreferences.read_file(options.file_path)
    return (options, arguments)
