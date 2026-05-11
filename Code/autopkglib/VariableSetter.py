#!/usr/local/autopkg/python
#
# Copyright 2025 Scott Blake
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

from autopkglib import Processor

__all__ = ["VariableSetter"]


class VariableSetter(Processor):
    """
    Set new variables for later use by AutoPkg processors.

    Define variables that can be used by other processors. This can be useful
    when a recipe needs to download two files but `URLDownloader` outputs to
    the same variable. This processor allows you to set new variables that can
    be used as input for other processors.

    Examples:

    Yaml Recipe:

    ```yaml
    - Processor: URLDownloader
    Arguments:
        url: https://example.com/foo.app
    - Processor: VariableSetter
    Arguments:
        app_path: "%pathname%"
        app_version: "%version%"
    - Processor: URLDownloader
    Arguments:
        url: https://example.com/foo.pkg
    - Processor: VariableSetter
    Arguments:
        pkg_path: "%pathname%"
        pkg_version: "%version%"
    ```

    Plist Recipe:

    ```xml
    <dict>
        <key>Processor</key>
        <string>URLDownloader</string>
        <key>Arguments</key>
        <dict>
            <key>url</key>
            <string>https://example.com/foo.app</string>
        </dict>
    </dict>
    <dict>
        <key>Processor</key>
        <string>VariableSetter</string>
        <key>Arguments</key>
        <dict>
            <key>app_path</key>
            <string>%pathname%</string>
            <key>app_version</key>
            <string>%version%</string>
        </dict>
    </dict>
    <dict>
        <key>Processor</key>
        <string>URLDownloader</string>
        <key>Arguments</key>
        <dict>
            <key>url</key>
            <string>https://example.com/foo.pkg</string>
        </dict>
    </dict>
    <dict>
        <key>Processor</key>
        <string>VariableSetter</string>
        <key>Arguments</key>
        <dict>
            <key>pkg_path</key>
            <string>%pathname%</string>
            <key>pkg_version</key>
            <string>%version%</string>
        </dict>
    </dict>
    ```
    """

    description = __doc__
    lifecycle = {"introduced": "2.9.0"}
    input_variables = {}
    output_variables = {}

    def main(self) -> None:
        return


if __name__ == "__main__":
    PROCESSOR = VariableSetter()
    PROCESSOR.execute_shell()
