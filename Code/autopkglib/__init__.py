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

import os

BUNDLE_ID = "com.googlecode.autopkg"

# get the directory this __init__.py file is in
mydir = os.path.dirname(os.path.abspath(__file__))
mydirname = os.path.basename(mydir)

# find all the .py files (minus this one)
processor_files = [
        os.path.splitext(name)[0] 
        for name in os.listdir(mydir) 
        if name.endswith('.py') and not name == '__init__.py']

# Warning! Fancy dynamic importing ahead!
#
# import the filename as a submodule
# then add the attribute with the same name to the globals()
#
# This is the equivalent of:
#
#    from Bar.Foo import Foo
#
for name in processor_files:
    globals()[name] = getattr(__import__(
        mydirname + '.' + name, fromlist=[name]), name)


# our fancy dynamic importing replaces the need to do all these
# explicit imports. More importantly, we can drop additional modules
# into this package directory and __init__.py will import them
# automagically
#from AdiumURLProvider           import AdiumURLProvider
#from AdobeFlashURLProvider      import AdobeFlashURLProvider
#from AdobeReaderDmgUnpacker     import AdobeReaderDmgUnpacker
#from AdobeReaderURLProvider     import AdobeReaderURLProvider
#from AppDmgVersioner            import AppDmgVersioner
#from Copier                     import Copier
#from CyberduckURLProvider       import CyberduckURLProvider
#from DmgCreator                 import DmgCreator
#from DmgMounter                 import DmgMounter
#from FileCreator                import FileCreator
#from FirefoxURLProvider         import FirefoxURLProvider
#from Firefox36URLProvider       import Firefox36URLProvider
#from AdobeFlashDmgUnpacker      import AdobeFlashDmgUnpacker
#from MunkiInfoCreator           import MunkiInfoCreator
#from PkgCreator                 import PkgCreator
#from PkgInfoCreator             import PkgInfoCreator
#from PkgRootCreator             import PkgRootCreator
#from PraatURLProvider           import PraatURLProvider
#from PraatVersionFixer          import PraatVersionFixer
#from TheUnarchiverURLProvider   import TheUnarchiverURLProvider
#from Unzipper                   import Unzipper
#from URLDownloader              import URLDownloader
#from VLCURLProvider             import VLCURLProvider

def add_processor(processor_name, processor_object):
    globals()[processor_name] = processor_object
    
