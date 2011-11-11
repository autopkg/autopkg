#!/usr/bin/env python
#
# Copyright 2010 Per Olofsson
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


BUNDLE_ID = "com.googlecode.autopkg"


from AdiumURLProvider           import AdiumURLProvider
from AdobeFlashURLProvider      import AdobeFlashURLProvider
from AdobeReaderDmgUnpacker     import AdobeReaderDmgUnpacker
from AdobeReaderURLProvider     import AdobeReaderURLProvider
from AppDmgVersioner            import AppDmgVersioner
from Copier                     import Copier
from CyberduckURLProvider       import CyberduckURLProvider
from DmgCreator                 import DmgCreator
from DmgMounter                 import DmgMounter
from FileCreator                import FileCreator
from FirefoxURLProvider         import FirefoxURLProvider
from Firefox36URLProvider       import Firefox36URLProvider
from AdobeFlashDmgUnpacker      import AdobeFlashDmgUnpacker
from MunkiInfoCreator           import MunkiInfoCreator
from PkgCreator                 import PkgCreator
from PkgInfoCreator             import PkgInfoCreator
from PkgRootCreator             import PkgRootCreator
from PraatURLProvider           import PraatURLProvider
from PraatVersionFixer          import PraatVersionFixer
from TheUnarchiverURLProvider   import TheUnarchiverURLProvider
from Unzipper                   import Unzipper
from URLDownloader              import URLDownloader
from VLCURLProvider             import VLCURLProvider
