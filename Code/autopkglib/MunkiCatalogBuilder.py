#!/usr/local/autopkg/python
#
# Copyright 2013 Greg Neagle
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
"""See docstring for MunkiCatalogBuilder class"""

from autopkglib import Processor

__all__ = ["MunkiCatalogBuilder"]


class MunkiCatalogBuilder(Processor):
    """DEPRECATED. This processor now emits a warning and performs no function. Previously it rebuilt Munki catalogs."""

    description = __doc__
    lifecycle = {"introduced": "0.1.0", "deprecated": "2.7.5"}
    input_variables = {}
    output_variables = {}

    def main(self) -> None:
        pass


if __name__ == "__main__":
    PROCESSOR = MunkiCatalogBuilder()
    PROCESSOR.execute_shell()
