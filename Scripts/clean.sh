#!/bin/bash
#
# Copyright 2011 Per Olofsson
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


find . -name '.DS_Store' -print0 | xargs -0 rm -f
find Code -name '*.pyc' -print0 | xargs -0 rm -rf
find Recipes -name '*-receipt-*.plist' -print0 | xargs -0 rm -f
find Recipes -name '*.dmg' -print0 | xargs -0 rm -f
find Recipes -name '*.pkg' -print0 | xargs -0 rm -rf
find Recipes -name 'PackageInfo' -print0 | xargs -0 rm -rf
find Recipes/Munki/TextMate -name '*.zip' -print0 | xargs -0 rm -rf
