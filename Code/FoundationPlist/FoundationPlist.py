#!/usr/bin/python
# encoding: utf-8
#
# Copyright 2009-2014 Greg Neagle.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""FoundationPlist.py -- a tool to generate and parse MacOSX .plist files.

This is intended as a drop-in replacement for Python's included plistlib,
with a few caveats:
    - readPlist() and writePlist() operate only on a filepath,
        not a file object.
    - there is no support for the deprecated functions:
        readPlistFromResource()
        writePlistToResource()
    - there is no support for the deprecated Plist class.

The Property List (.plist) file format is a simple XML pickle supporting
basic object types, like dictionaries, lists, numbers and strings.
Usually the top level object is a dictionary.

To write out a plist file, use the writePlist(rootObject, filepath)
function. 'rootObject' is the top level object, 'filepath' is a
filename.

To parse a plist from a file, use the readPlist(filepath) function,
with a file name. It returns the top level object (again, usually a
dictionary).

To work with plist data in strings, you can use readPlistFromString()
and writePlistToString().
"""

import os

from Foundation import (NSData, NSPropertyListMutableContainersAndLeaves,
                        NSPropertyListSerialization,
                        NSPropertyListXMLFormat_v1_0)


class FoundationPlistException(Exception):
    '''Base error for this module'''
    pass


class NSPropertyListSerializationException(FoundationPlistException):
    '''Read error for this module'''
    pass


class NSPropertyListWriteException(FoundationPlistException):
    '''Write error for this module'''
    pass


# private functions
def _dataToPlist(data):
    '''low-level function that parses a data object into a propertyList object'''
    darwin_vers = int(os.uname()[2].split('.')[0])
    if darwin_vers > 10:
        (plistObject, plistFormat, error) = (
            NSPropertyListSerialization.propertyListWithData_options_format_error_(
                data, NSPropertyListMutableContainersAndLeaves, None, None))
    else:
        # 10.5 doesn't support propertyListWithData:options:format:error:
        # 10.6's PyObjC wrapper for propertyListWithData:options:format:error:
        #        is broken
        # so use the older NSPropertyListSerialization function
        (plistObject, plistFormat, error) = (
            NSPropertyListSerialization.propertyListFromData_mutabilityOption_format_errorDescription_(
                data, NSPropertyListMutableContainersAndLeaves, None, None
            )
        )
    if plistObject is None:
        if error is None:
            error = "Plist data is invalid and could not be deserialized."
        raise NSPropertyListSerializationException(error)
    else:
        return plistObject


def _plistToData(plistObject):
    '''low-level function that creates NSData from a plist object'''
    darwin_vers = int(os.uname()[2].split('.')[0])
    if darwin_vers > 10:
        (data, error) = (
            NSPropertyListSerialization.dataWithPropertyList_format_options_error_(
                plistObject, NSPropertyListXMLFormat_v1_0, 0, None))
    else:
        # use the older NSPropertyListSerialization function on 10.6 and 10.5
        (data, error) = (
            NSPropertyListSerialization.dataFromPropertyList_format_errorDescription_(
                plistObject, NSPropertyListXMLFormat_v1_0, None))
    if data is None:
        if error is None:
            error = "Property list invalid for format."
        raise NSPropertyListSerializationException(error)
    return data


# public functions
def readPlist(filepath):
    '''Read a .plist file from filepath.  Return the unpacked root object
    (which is usually a dictionary).'''
    try:
        data = NSData.dataWithContentsOfFile_(filepath)
    except NSPropertyListSerializationException as error:
        # insert filepath info into error message
        errmsg = (u'%s in %s' % (error, filepath))
        raise NSPropertyListSerializationException(errmsg)
    return _dataToPlist(data)


def readPlistFromString(aString):
    '''Read a plist data from a string. Return the root object.'''
    data = buffer(aString)
    return _dataToPlist(data)


def writePlist(plistObject, filepath):
    '''Write 'plistObject' as a plist to filepath.'''
    plistData = _plistToData(plistObject)
    if plistData.writeToFile_atomically_(filepath, True):
        return
    else:
        raise NSPropertyListWriteException(
            u"Failed to write plist data to %s" % filepath)


def writePlistToString(plistObject):
    '''Create a plist-formatted string from plistObject.'''
    return str(_plistToData(plistObject))
