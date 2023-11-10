#!/usr/local/autopkg/python
#
# Copyright 2016 Greg Neagle
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
"""Stub that allows URLDownloader to be called as 'CURLDownloader' during the
deprecation period."""

from autopkg.autopkglib.URLDownloader import URLDownloader

__all__ = ["CURLDownloader"]

CURLDownloader = URLDownloader

if __name__ == "__main__":
    PROCESSOR = CURLDownloader()
    PROCESSOR.execute_shell()
