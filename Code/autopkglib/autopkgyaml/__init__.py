#!/usr/local/autopkg/python
#
# Copyright 2021 Brandon Friess
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
"""Helper to deal with YAML serialization"""


from yaml.composer import Composer
from yaml.constructor import SafeConstructor
from yaml.parser import Parser
from yaml.reader import Reader
from yaml.resolver import Resolver
from yaml.scanner import Scanner


def autopkg_str_representer(dumper, data):
    """Makes every multiline string a block literal"""
    if len(data.splitlines()) > 1:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


# Create custom Constructor class that inherits from SafeConstructor
class AutoPkgConstructor(SafeConstructor):
    pass


# Override YAML type conversion logic in the custom Constructor
for yaml_type in {"bool", "int", "float", "null", "timestamp"}:
    AutoPkgConstructor.add_constructor(
        f"tag:yaml.org,2002:{yaml_type}", AutoPkgConstructor.construct_yaml_str
    )


# Create a custom Loader with the custom Constructor
class AutoPkgLoader(Reader, Scanner, Parser, Composer, AutoPkgConstructor, Resolver):
    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        AutoPkgConstructor.__init__(self)
        Resolver.__init__(self)
