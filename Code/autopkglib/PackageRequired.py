#!/usr/bin/python
#
# Copyright 2015 Jesse Peterson
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
"""See docstring for PackageRequired class"""

import os

from autopkglib import Processor, ProcessorError

__all__ = ["PackageRequired"]


class PackageRequired(Processor):
    '''Raises a ProcessorError if the PKG variable doesn't exist.

    Requires version 0.5.1.'''

    input_variables = {
    }
    output_variables = {
    }

    def main(self):
        pkg = self.env.get('PKG', None)

        if not pkg:
            raise ProcessorError('This recipe requires a package or disk '
                'image to be pre-downloaded and supplied to autopkg ("-p" '
                'command-line switch). This is likely due to required login '
                'credentials to download the software.')

        if not os.path.exists(pkg):
            raise ProcessorError('Path to package or disk image does not exist: %s' % pkg)
