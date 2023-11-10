#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Generated Thu Jul  9 19:35:57 2020 by generateDS.py version 2.35.24.
# Python 3.8.3 (tags/v3.8.3:6f8c832, May 13 2020, 22:37:02) [MSC v.1924 64 bit (AMD64)]
#
# Command line options:
#   ('--member-specs', 'dict')
#   ('--enable-slots', '')
#   ('--export', 'write validate')
#   ('--no-questions', '')
#   ('-f', '')
#   ('-o', '.\\Code\\nuget\\generated\\_nuspec.py')
#
# Command line arguments:
#   -
#
# Command line:
#   C:\Users\bcsmith\autopkg\venv-py38\Scripts\generateDS --member-specs="dict" --enable-slots --export="write validate" --no-questions -f -o ".\Code\nuget\generated\_nuspec.py" -
#
# Current working directory (os.getcwd()):
#   autopkg
#

from itertools import islice
import os
import sys
import re as re_
import base64
import datetime as datetime_
import decimal as decimal_

try:
    from lxml import etree as etree_
except ImportError:
    from xml.etree import ElementTree as etree_


Validate_simpletypes_ = True
SaveElementTreeNode = True
if sys.version_info.major == 2:
    BaseStrType_ = basestring
else:
    BaseStrType_ = str


def parsexml_(infile, parser=None, **kwargs):
    if parser is None:
        # Use the lxml ElementTree compatible parser so that, e.g.,
        #   we ignore comments.
        try:
            parser = etree_.ETCompatXMLParser()
        except AttributeError:
            # fallback to xml.etree
            parser = etree_.XMLParser()
    try:
        if isinstance(infile, os.PathLike):
            infile = os.path.join(infile)
    except AttributeError:
        pass
    doc = etree_.parse(infile, parser=parser, **kwargs)
    return doc


def parsexmlstring_(instring, parser=None, **kwargs):
    if parser is None:
        # Use the lxml ElementTree compatible parser so that, e.g.,
        #   we ignore comments.
        try:
            parser = etree_.ETCompatXMLParser()
        except AttributeError:
            # fallback to xml.etree
            parser = etree_.XMLParser()
    element = etree_.fromstring(instring, parser=parser, **kwargs)
    return element


#
# Namespace prefix definition table (and other attributes, too)
#
# The module generatedsnamespaces, if it is importable, must contain
# a dictionary named GeneratedsNamespaceDefs.  This Python dictionary
# should map element type names (strings) to XML schema namespace prefix
# definitions.  The export method for any class for which there is
# a namespace prefix definition, will export that definition in the
# XML representation of that element.  See the export method of
# any generated element type class for an example of the use of this
# table.
# A sample table is:
#
#     # File: generatedsnamespaces.py
#
#     GenerateDSNamespaceDefs = {
#         "ElementtypeA": "http://www.xxx.com/namespaceA",
#         "ElementtypeB": "http://www.xxx.com/namespaceB",
#     }
#
# Additionally, the generatedsnamespaces module can contain a python
# dictionary named GenerateDSNamespaceTypePrefixes that associates element
# types with the namespace prefixes that are to be added to the
# "xsi:type" attribute value.  See the exportAttributes method of
# any generated element type and the generation of "xsi:type" for an
# example of the use of this table.
# An example table:
#
#     # File: generatedsnamespaces.py
#
#     GenerateDSNamespaceTypePrefixes = {
#         "ElementtypeC": "aaa:",
#         "ElementtypeD": "bbb:",
#     }
#

try:
    from generatedsnamespaces import GenerateDSNamespaceDefs as GenerateDSNamespaceDefs_
except ImportError:
    GenerateDSNamespaceDefs_ = {}
try:
    from generatedsnamespaces import (
        GenerateDSNamespaceTypePrefixes as GenerateDSNamespaceTypePrefixes_,
    )
except ImportError:
    GenerateDSNamespaceTypePrefixes_ = {}

#
# You can replace the following class definition by defining an
# importable module named "generatedscollector" containing a class
# named "GdsCollector".  See the default class definition below for
# clues about the possible content of that class.
#
try:
    from generatedscollector import GdsCollector as GdsCollector_
except ImportError:

    class GdsCollector_(object):
        def __init__(self, messages=None):
            if messages is None:
                self.messages = []
            else:
                self.messages = messages

        def add_message(self, msg):
            self.messages.append(msg)

        def get_messages(self):
            return self.messages

        def clear_messages(self):
            self.messages = []

        def print_messages(self):
            for msg in self.messages:
                print("Warning: {}".format(msg))

        def write_messages(self, outstream):
            for msg in self.messages:
                outstream.write("Warning: {}\n".format(msg))


#
# The super-class for enum types
#

try:
    from enum import Enum
except ImportError:
    Enum = object

#
# The root super-class for element type classes
#
# Calls to the methods in these classes are generated by generateDS.py.
# You can replace these methods by re-implementing the following class
#   in a module named generatedssuper.py.

try:
    from generatedssuper import GeneratedsSuper
except ImportError as exp:

    class GeneratedsSuper(object):
        __slots__ = [
            "gds_collector_",
            "gds_elementtree_node_",
            "original_tagname_",
            "parent_object_",
            "ns_prefix_",
        ]
        __hash__ = object.__hash__
        tzoff_pattern = re_.compile(r"(\+|-)((0\d|1[0-3]):[0-5]\d|14:00)$")

        class _FixedOffsetTZ(datetime_.tzinfo):
            def __init__(self, offset, name):
                self.__offset = datetime_.timedelta(minutes=offset)
                self.__name = name

            def utcoffset(self, dt):
                return self.__offset

            def tzname(self, dt):
                return self.__name

            def dst(self, dt):
                return None

        @staticmethod
        def gds_subclass_slots(member_data_items):
            slots = []
            for member in member_data_items:
                slots.append(member)
                slots.append("%s_nsprefix_" % member)
            return slots

        def gds_format_string(self, input_data, input_name=""):
            return input_data

        def gds_parse_string(self, input_data, node=None, input_name=""):
            return input_data

        def gds_validate_string(self, input_data, node=None, input_name=""):
            if not input_data:
                return ""
            else:
                return input_data

        def gds_format_base64(self, input_data, input_name=""):
            return base64.b64encode(input_data)

        def gds_validate_base64(self, input_data, node=None, input_name=""):
            return input_data

        def gds_format_integer(self, input_data, input_name=""):
            return "%d" % input_data

        def gds_parse_integer(self, input_data, node=None, input_name=""):
            try:
                ival = int(input_data)
            except (TypeError, ValueError) as exp:
                raise_parse_error(node, "Requires integer value: %s" % exp)
            return ival

        def gds_validate_integer(self, input_data, node=None, input_name=""):
            try:
                value = int(input_data)
            except (TypeError, ValueError):
                raise_parse_error(node, "Requires integer value")
            return value

        def gds_format_integer_list(self, input_data, input_name=""):
            return "%s" % " ".join(input_data)

        def gds_validate_integer_list(self, input_data, node=None, input_name=""):
            values = input_data.split()
            for value in values:
                try:
                    int(value)
                except (TypeError, ValueError):
                    raise_parse_error(node, "Requires sequence of integer valuess")
            return values

        def gds_format_float(self, input_data, input_name=""):
            return ("%.15f" % input_data).rstrip("0")

        def gds_parse_float(self, input_data, node=None, input_name=""):
            try:
                fval_ = float(input_data)
            except (TypeError, ValueError) as exp:
                raise_parse_error(node, "Requires float or double value: %s" % exp)
            return fval_

        def gds_validate_float(self, input_data, node=None, input_name=""):
            try:
                value = float(input_data)
            except (TypeError, ValueError):
                raise_parse_error(node, "Requires float value")
            return value

        def gds_format_float_list(self, input_data, input_name=""):
            return "%s" % " ".join(input_data)

        def gds_validate_float_list(self, input_data, node=None, input_name=""):
            values = input_data.split()
            for value in values:
                try:
                    float(value)
                except (TypeError, ValueError):
                    raise_parse_error(node, "Requires sequence of float values")
            return values

        def gds_format_decimal(self, input_data, input_name=""):
            return_value = "%s" % input_data
            if "." in return_value:
                return_value = return_value.rstrip("0")
                if return_value.endswith("."):
                    return_value = return_value.rstrip(".")
            return return_value

        def gds_parse_decimal(self, input_data, node=None, input_name=""):
            try:
                decimal_value = decimal_.Decimal(input_data)
            except (TypeError, ValueError):
                raise_parse_error(node, "Requires decimal value")
            return decimal_value

        def gds_validate_decimal(self, input_data, node=None, input_name=""):
            try:
                value = decimal_.Decimal(input_data)
            except (TypeError, ValueError):
                raise_parse_error(node, "Requires decimal value")
            return value

        def gds_format_decimal_list(self, input_data, input_name=""):
            return " ".join([self.gds_format_decimal(item) for item in input_data])

        def gds_validate_decimal_list(self, input_data, node=None, input_name=""):
            values = input_data.split()
            for value in values:
                try:
                    decimal_.Decimal(value)
                except (TypeError, ValueError):
                    raise_parse_error(node, "Requires sequence of decimal values")
            return values

        def gds_format_double(self, input_data, input_name=""):
            return "%e" % input_data

        def gds_parse_double(self, input_data, node=None, input_name=""):
            try:
                fval_ = float(input_data)
            except (TypeError, ValueError) as exp:
                raise_parse_error(node, "Requires double or float value: %s" % exp)
            return fval_

        def gds_validate_double(self, input_data, node=None, input_name=""):
            try:
                value = float(input_data)
            except (TypeError, ValueError):
                raise_parse_error(node, "Requires double or float value")
            return value

        def gds_format_double_list(self, input_data, input_name=""):
            return "%s" % " ".join(input_data)

        def gds_validate_double_list(self, input_data, node=None, input_name=""):
            values = input_data.split()
            for value in values:
                try:
                    float(value)
                except (TypeError, ValueError):
                    raise_parse_error(
                        node, "Requires sequence of double or float values"
                    )
            return values

        def gds_format_boolean(self, input_data, input_name=""):
            return ("%s" % input_data).lower()

        def gds_parse_boolean(self, input_data, node=None, input_name=""):
            if input_data in ("true", "1"):
                bval = True
            elif input_data in ("false", "0"):
                bval = False
            else:
                raise_parse_error(node, "Requires boolean value")
            return bval

        def gds_validate_boolean(self, input_data, node=None, input_name=""):
            if input_data not in (
                True,
                1,
                False,
                0,
            ):
                raise_parse_error(
                    node, "Requires boolean value " "(one of True, 1, False, 0)"
                )
            return input_data

        def gds_format_boolean_list(self, input_data, input_name=""):
            return "%s" % " ".join(input_data)

        def gds_validate_boolean_list(self, input_data, node=None, input_name=""):
            values = input_data.split()
            for value in values:
                if value not in (
                    True,
                    1,
                    False,
                    0,
                ):
                    raise_parse_error(
                        node,
                        "Requires sequence of boolean values "
                        "(one of True, 1, False, 0)",
                    )
            return values

        def gds_validate_datetime(self, input_data, node=None, input_name=""):
            return input_data

        def gds_format_datetime(self, input_data, input_name=""):
            if input_data.microsecond == 0:
                _svalue = "%04d-%02d-%02dT%02d:%02d:%02d" % (
                    input_data.year,
                    input_data.month,
                    input_data.day,
                    input_data.hour,
                    input_data.minute,
                    input_data.second,
                )
            else:
                _svalue = "%04d-%02d-%02dT%02d:%02d:%02d.%s" % (
                    input_data.year,
                    input_data.month,
                    input_data.day,
                    input_data.hour,
                    input_data.minute,
                    input_data.second,
                    ("%f" % (float(input_data.microsecond) / 1000000))[2:],
                )
            if input_data.tzinfo is not None:
                tzoff = input_data.tzinfo.utcoffset(input_data)
                if tzoff is not None:
                    total_seconds = tzoff.seconds + (86400 * tzoff.days)
                    if total_seconds == 0:
                        _svalue += "Z"
                    else:
                        if total_seconds < 0:
                            _svalue += "-"
                            total_seconds *= -1
                        else:
                            _svalue += "+"
                        hours = total_seconds // 3600
                        minutes = (total_seconds - (hours * 3600)) // 60
                        _svalue += "{0:02d}:{1:02d}".format(hours, minutes)
            return _svalue

        @classmethod
        def gds_parse_datetime(cls, input_data):
            tz = None
            if input_data[-1] == "Z":
                tz = GeneratedsSuper._FixedOffsetTZ(0, "UTC")
                input_data = input_data[:-1]
            else:
                results = GeneratedsSuper.tzoff_pattern.search(input_data)
                if results is not None:
                    tzoff_parts = results.group(2).split(":")
                    tzoff = int(tzoff_parts[0]) * 60 + int(tzoff_parts[1])
                    if results.group(1) == "-":
                        tzoff *= -1
                    tz = GeneratedsSuper._FixedOffsetTZ(tzoff, results.group(0))
                    input_data = input_data[:-6]
            time_parts = input_data.split(".")
            if len(time_parts) > 1:
                micro_seconds = int(float("0." + time_parts[1]) * 1000000)
                input_data = "%s.%s" % (
                    time_parts[0],
                    "{}".format(micro_seconds).rjust(6, "0"),
                )
                dt = datetime_.datetime.strptime(input_data, "%Y-%m-%dT%H:%M:%S.%f")
            else:
                dt = datetime_.datetime.strptime(input_data, "%Y-%m-%dT%H:%M:%S")
            dt = dt.replace(tzinfo=tz)
            return dt

        def gds_validate_date(self, input_data, node=None, input_name=""):
            return input_data

        def gds_format_date(self, input_data, input_name=""):
            _svalue = "%04d-%02d-%02d" % (
                input_data.year,
                input_data.month,
                input_data.day,
            )
            try:
                if input_data.tzinfo is not None:
                    tzoff = input_data.tzinfo.utcoffset(input_data)
                    if tzoff is not None:
                        total_seconds = tzoff.seconds + (86400 * tzoff.days)
                        if total_seconds == 0:
                            _svalue += "Z"
                        else:
                            if total_seconds < 0:
                                _svalue += "-"
                                total_seconds *= -1
                            else:
                                _svalue += "+"
                            hours = total_seconds // 3600
                            minutes = (total_seconds - (hours * 3600)) // 60
                            _svalue += "{0:02d}:{1:02d}".format(hours, minutes)
            except AttributeError:
                pass
            return _svalue

        @classmethod
        def gds_parse_date(cls, input_data):
            tz = None
            if input_data[-1] == "Z":
                tz = GeneratedsSuper._FixedOffsetTZ(0, "UTC")
                input_data = input_data[:-1]
            else:
                results = GeneratedsSuper.tzoff_pattern.search(input_data)
                if results is not None:
                    tzoff_parts = results.group(2).split(":")
                    tzoff = int(tzoff_parts[0]) * 60 + int(tzoff_parts[1])
                    if results.group(1) == "-":
                        tzoff *= -1
                    tz = GeneratedsSuper._FixedOffsetTZ(tzoff, results.group(0))
                    input_data = input_data[:-6]
            dt = datetime_.datetime.strptime(input_data, "%Y-%m-%d")
            dt = dt.replace(tzinfo=tz)
            return dt.date()

        def gds_validate_time(self, input_data, node=None, input_name=""):
            return input_data

        def gds_format_time(self, input_data, input_name=""):
            if input_data.microsecond == 0:
                _svalue = "%02d:%02d:%02d" % (
                    input_data.hour,
                    input_data.minute,
                    input_data.second,
                )
            else:
                _svalue = "%02d:%02d:%02d.%s" % (
                    input_data.hour,
                    input_data.minute,
                    input_data.second,
                    ("%f" % (float(input_data.microsecond) / 1000000))[2:],
                )
            if input_data.tzinfo is not None:
                tzoff = input_data.tzinfo.utcoffset(input_data)
                if tzoff is not None:
                    total_seconds = tzoff.seconds + (86400 * tzoff.days)
                    if total_seconds == 0:
                        _svalue += "Z"
                    else:
                        if total_seconds < 0:
                            _svalue += "-"
                            total_seconds *= -1
                        else:
                            _svalue += "+"
                        hours = total_seconds // 3600
                        minutes = (total_seconds - (hours * 3600)) // 60
                        _svalue += "{0:02d}:{1:02d}".format(hours, minutes)
            return _svalue

        def gds_validate_simple_patterns(self, patterns, target):
            # pat is a list of lists of strings/patterns.
            # The target value must match at least one of the patterns
            # in order for the test to succeed.
            found1 = True
            for patterns1 in patterns:
                found2 = False
                for patterns2 in patterns1:
                    mo = re_.search(patterns2, target)
                    if mo is not None and len(mo.group(0)) == len(target):
                        found2 = True
                        break
                if not found2:
                    found1 = False
                    break
            return found1

        @classmethod
        def gds_parse_time(cls, input_data):
            tz = None
            if input_data[-1] == "Z":
                tz = GeneratedsSuper._FixedOffsetTZ(0, "UTC")
                input_data = input_data[:-1]
            else:
                results = GeneratedsSuper.tzoff_pattern.search(input_data)
                if results is not None:
                    tzoff_parts = results.group(2).split(":")
                    tzoff = int(tzoff_parts[0]) * 60 + int(tzoff_parts[1])
                    if results.group(1) == "-":
                        tzoff *= -1
                    tz = GeneratedsSuper._FixedOffsetTZ(tzoff, results.group(0))
                    input_data = input_data[:-6]
            if len(input_data.split(".")) > 1:
                dt = datetime_.datetime.strptime(input_data, "%H:%M:%S.%f")
            else:
                dt = datetime_.datetime.strptime(input_data, "%H:%M:%S")
            dt = dt.replace(tzinfo=tz)
            return dt.time()

        def gds_check_cardinality_(
            self, value, input_name, min_occurs=0, max_occurs=1, required=None
        ):
            if value is None:
                length = 0
            elif isinstance(value, list):
                length = len(value)
            else:
                length = 1
            if required is not None:
                if required and length < 1:
                    self.gds_collector_.add_message(
                        "Required value {}{} is missing".format(
                            input_name, self.gds_get_node_lineno_()
                        )
                    )
            if length < min_occurs:
                self.gds_collector_.add_message(
                    "Number of values for {}{} is below "
                    "the minimum allowed, "
                    "expected at least {}, found {}".format(
                        input_name, self.gds_get_node_lineno_(), min_occurs, length
                    )
                )
            elif length > max_occurs:
                self.gds_collector_.add_message(
                    "Number of values for {}{} is above "
                    "the maximum allowed, "
                    "expected at most {}, found {}".format(
                        input_name, self.gds_get_node_lineno_(), max_occurs, length
                    )
                )

        def gds_validate_builtin_ST_(
            self,
            validator,
            value,
            input_name,
            min_occurs=None,
            max_occurs=None,
            required=None,
        ):
            if value is not None:
                try:
                    validator(value, input_name=input_name)
                except GDSParseError as parse_error:
                    self.gds_collector_.add_message(str(parse_error))

        def gds_validate_defined_ST_(
            self,
            validator,
            value,
            input_name,
            min_occurs=None,
            max_occurs=None,
            required=None,
        ):
            if value is not None:
                try:
                    validator(value)
                except GDSParseError as parse_error:
                    self.gds_collector_.add_message(str(parse_error))

        def gds_str_lower(self, instring):
            return instring.lower()

        def get_path_(self, node):
            path_list = []
            self.get_path_list_(node, path_list)
            path_list.reverse()
            path = "/".join(path_list)
            return path

        Tag_strip_pattern_ = re_.compile(r"\{.*\}")

        def get_path_list_(self, node, path_list):
            if node is None:
                return
            tag = GeneratedsSuper.Tag_strip_pattern_.sub("", node.tag)
            if tag:
                path_list.append(tag)
            self.get_path_list_(node.getparent(), path_list)

        def get_class_obj_(self, node, default_class=None):
            class_obj1 = default_class
            if "xsi" in node.nsmap:
                classname = node.get("{%s}type" % node.nsmap["xsi"])
                if classname is not None:
                    names = classname.split(":")
                    if len(names) == 2:
                        classname = names[1]
                    class_obj2 = globals().get(classname)
                    if class_obj2 is not None:
                        class_obj1 = class_obj2
            return class_obj1

        def gds_build_any(self, node, type_name=None):
            # provide default value in case option --disable-xml is used.
            content = ""
            content = etree_.tostring(node, encoding="unicode")
            return content

        @classmethod
        def gds_reverse_node_mapping(cls, mapping):
            return dict(((v, k) for k, v in mapping.items()))

        @staticmethod
        def gds_encode(instring):
            if sys.version_info.major == 2:
                if ExternalEncoding:
                    encoding = ExternalEncoding
                else:
                    encoding = "utf-8"
                return instring.encode(encoding)
            else:
                return instring

        @staticmethod
        def convert_unicode(instring):
            if isinstance(instring, str):
                result = quote_xml(instring)
            elif sys.version_info.major == 2 and isinstance(instring, unicode):
                result = quote_xml(instring).encode("utf8")
            else:
                result = GeneratedsSuper.gds_encode(str(instring))
            return result

        def __eq__(self, other):
            if type(self) != type(other):
                return False
            mro = self.__class__.__mro__
            return all(
                getattr(self, attribute) == getattr(other, attribute)
                for cls in islice(mro, 0, len(mro) - 2)
                for attribute in cls.member_data_items_
            )

        def __ne__(self, other):
            return not self.__eq__(other)

        # Django ETL transform hooks.
        def gds_djo_etl_transform(self):
            pass

        def gds_djo_etl_transform_db_obj(self, dbobj):
            pass

        # SQLAlchemy ETL transform hooks.
        def gds_sqa_etl_transform(self):
            return 0, None

        def gds_sqa_etl_transform_db_obj(self, dbobj):
            pass

        def gds_get_node_lineno_(self):
            if (
                hasattr(self, "gds_elementtree_node_")
                and self.gds_elementtree_node_ is not None
            ):
                return " near line {}".format(self.gds_elementtree_node_.sourceline)
            else:
                return ""

    def getSubclassFromModule_(module, class_):
        """Get the subclass of a class from a specific module."""
        name = class_.__name__ + "Sub"
        if hasattr(module, name):
            return getattr(module, name)
        else:
            return None


#
# If you have installed IPython you can uncomment and use the following.
# IPython is available from http://ipython.scipy.org/.
#

## from IPython.Shell import IPShellEmbed
## args = ''
## ipshell = IPShellEmbed(args,
##     banner = 'Dropping into IPython',
##     exit_msg = 'Leaving Interpreter, back to program.')

# Then use the following line where and when you want to drop into the
# IPython shell:
#    ipshell('<some message> -- Entering ipshell.\nHit Ctrl-D to exit')

#
# Globals
#

ExternalEncoding = ""
# Set this to false in order to deactivate during export, the use of
# name space prefixes captured from the input document.
UseCapturedNS_ = True
CapturedNsmap_ = {}
Tag_pattern_ = re_.compile(r"({.*})?(.*)")
String_cleanup_pat_ = re_.compile(r"[\n\r\s]+")
Namespace_extract_pat_ = re_.compile(r"{(.*)}(.*)")
CDATA_pattern_ = re_.compile(r"<!\[CDATA\[.*?\]\]>", re_.DOTALL)

# Change this to redirect the generated superclass module to use a
# specific subclass module.
CurrentSubclassModule_ = None

#
# Support/utility functions.
#


def showIndent(outfile, level, pretty_print=True):
    if pretty_print:
        for idx in range(level):
            outfile.write("    ")


def quote_xml(inStr):
    "Escape markup chars, but do not modify CDATA sections."
    if not inStr:
        return ""
    s1 = isinstance(inStr, BaseStrType_) and inStr or "%s" % inStr
    s2 = ""
    pos = 0
    matchobjects = CDATA_pattern_.finditer(s1)
    for mo in matchobjects:
        s3 = s1[pos : mo.start()]
        s2 += quote_xml_aux(s3)
        s2 += s1[mo.start() : mo.end()]
        pos = mo.end()
    s3 = s1[pos:]
    s2 += quote_xml_aux(s3)
    return s2


def quote_xml_aux(inStr):
    s1 = inStr.replace("&", "&amp;")
    s1 = s1.replace("<", "&lt;")
    s1 = s1.replace(">", "&gt;")
    return s1


def quote_attrib(inStr):
    s1 = isinstance(inStr, BaseStrType_) and inStr or "%s" % inStr
    s1 = s1.replace("&", "&amp;")
    s1 = s1.replace("<", "&lt;")
    s1 = s1.replace(">", "&gt;")
    if '"' in s1:
        if "'" in s1:
            s1 = '"%s"' % s1.replace('"', "&quot;")
        else:
            s1 = "'%s'" % s1
    else:
        s1 = '"%s"' % s1
    return s1


def quote_python(inStr):
    s1 = inStr
    if s1.find("'") == -1:
        if s1.find("\n") == -1:
            return "'%s'" % s1
        else:
            return "'''%s'''" % s1
    else:
        if s1.find('"') != -1:
            s1 = s1.replace('"', '\\"')
        if s1.find("\n") == -1:
            return '"%s"' % s1
        else:
            return '"""%s"""' % s1


def get_all_text_(node):
    if node.text is not None:
        text = node.text
    else:
        text = ""
    for child in node:
        if child.tail is not None:
            text += child.tail
    return text


def find_attr_value_(attr_name, node):
    attrs = node.attrib
    attr_parts = attr_name.split(":")
    value = None
    if len(attr_parts) == 1:
        value = attrs.get(attr_name)
    elif len(attr_parts) == 2:
        prefix, name = attr_parts
        namespace = node.nsmap.get(prefix)
        if namespace is not None:
            value = attrs.get(
                "{%s}%s"
                % (
                    namespace,
                    name,
                )
            )
    return value


def encode_str_2_3(instr):
    return instr


class GDSParseError(Exception):
    pass


def raise_parse_error(node, msg):
    if node is not None:
        msg = "%s (element %s/line %d)" % (
            msg,
            node.tag,
            node.sourceline,
        )
    raise GDSParseError(msg)


class MixedContainer:
    # Constants for category:
    CategoryNone = 0
    CategoryText = 1
    CategorySimple = 2
    CategoryComplex = 3
    # Constants for content_type:
    TypeNone = 0
    TypeText = 1
    TypeString = 2
    TypeInteger = 3
    TypeFloat = 4
    TypeDecimal = 5
    TypeDouble = 6
    TypeBoolean = 7
    TypeBase64 = 8

    def __init__(self, category, content_type, name, value):
        self.category = category
        self.content_type = content_type
        self.name = name
        self.value = value

    def getCategory(self):
        return self.category

    def getContenttype(self, content_type):
        return self.content_type

    def getValue(self):
        return self.value

    def getName(self):
        return self.name

    def export(self, outfile, level, name, namespace, pretty_print=True):
        if self.category == MixedContainer.CategoryText:
            # Prevent exporting empty content as empty lines.
            if self.value.strip():
                outfile.write(self.value)
        elif self.category == MixedContainer.CategorySimple:
            self.exportSimple(outfile, level, name)
        else:  # category == MixedContainer.CategoryComplex
            self.value.export(
                outfile, level, namespace, name_=name, pretty_print=pretty_print
            )

    def exportSimple(self, outfile, level, name):
        if self.content_type == MixedContainer.TypeString:
            outfile.write("<%s>%s</%s>" % (self.name, self.value, self.name))
        elif (
            self.content_type == MixedContainer.TypeInteger
            or self.content_type == MixedContainer.TypeBoolean
        ):
            outfile.write("<%s>%d</%s>" % (self.name, self.value, self.name))
        elif (
            self.content_type == MixedContainer.TypeFloat
            or self.content_type == MixedContainer.TypeDecimal
        ):
            outfile.write("<%s>%f</%s>" % (self.name, self.value, self.name))
        elif self.content_type == MixedContainer.TypeDouble:
            outfile.write("<%s>%g</%s>" % (self.name, self.value, self.name))
        elif self.content_type == MixedContainer.TypeBase64:
            outfile.write(
                "<%s>%s</%s>" % (self.name, base64.b64encode(self.value), self.name)
            )

    def to_etree(self, element, mapping_=None, nsmap_=None):
        if self.category == MixedContainer.CategoryText:
            # Prevent exporting empty content as empty lines.
            if self.value.strip():
                if len(element) > 0:
                    if element[-1].tail is None:
                        element[-1].tail = self.value
                    else:
                        element[-1].tail += self.value
                else:
                    if element.text is None:
                        element.text = self.value
                    else:
                        element.text += self.value
        elif self.category == MixedContainer.CategorySimple:
            subelement = etree_.SubElement(element, "%s" % self.name)
            subelement.text = self.to_etree_simple()
        else:  # category == MixedContainer.CategoryComplex
            self.value.to_etree(element)

    def to_etree_simple(self, mapping_=None, nsmap_=None):
        if self.content_type == MixedContainer.TypeString:
            text = self.value
        elif (
            self.content_type == MixedContainer.TypeInteger
            or self.content_type == MixedContainer.TypeBoolean
        ):
            text = "%d" % self.value
        elif (
            self.content_type == MixedContainer.TypeFloat
            or self.content_type == MixedContainer.TypeDecimal
        ):
            text = "%f" % self.value
        elif self.content_type == MixedContainer.TypeDouble:
            text = "%g" % self.value
        elif self.content_type == MixedContainer.TypeBase64:
            text = "%s" % base64.b64encode(self.value)
        return text

    def exportLiteral(self, outfile, level, name):
        if self.category == MixedContainer.CategoryText:
            showIndent(outfile, level)
            outfile.write(
                'model_.MixedContainer(%d, %d, "%s", "%s"),\n'
                % (self.category, self.content_type, self.name, self.value)
            )
        elif self.category == MixedContainer.CategorySimple:
            showIndent(outfile, level)
            outfile.write(
                'model_.MixedContainer(%d, %d, "%s", "%s"),\n'
                % (self.category, self.content_type, self.name, self.value)
            )
        else:  # category == MixedContainer.CategoryComplex
            showIndent(outfile, level)
            outfile.write(
                'model_.MixedContainer(%d, %d, "%s",\n'
                % (
                    self.category,
                    self.content_type,
                    self.name,
                )
            )
            self.value.exportLiteral(outfile, level + 1)
            showIndent(outfile, level)
            outfile.write(")\n")


class MemberSpec_(object):
    def __init__(
        self,
        name="",
        data_type="",
        container=0,
        optional=0,
        child_attrs=None,
        choice=None,
    ):
        self.name = name
        self.data_type = data_type
        self.container = container
        self.child_attrs = child_attrs
        self.choice = choice
        self.optional = optional

    def set_name(self, name):
        self.name = name

    def get_name(self):
        return self.name

    def set_data_type(self, data_type):
        self.data_type = data_type

    def get_data_type_chain(self):
        return self.data_type

    def get_data_type(self):
        if isinstance(self.data_type, list):
            if len(self.data_type) > 0:
                return self.data_type[-1]
            else:
                return "xs:string"
        else:
            return self.data_type

    def set_container(self, container):
        self.container = container

    def get_container(self):
        return self.container

    def set_child_attrs(self, child_attrs):
        self.child_attrs = child_attrs

    def get_child_attrs(self):
        return self.child_attrs

    def set_choice(self, choice):
        self.choice = choice

    def get_choice(self):
        return self.choice

    def set_optional(self, optional):
        self.optional = optional

    def get_optional(self):
        return self.optional


def _cast(typ, value):
    if typ is None or value is None:
        return value
    return typ(value)


#
# Data representation classes.
#


class dependency(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "id": MemberSpec_("id", "xs:string", 0, 0, {"use": "required"}),
        "version": MemberSpec_("version", "xs:string", 0, 1, {"use": "optional"}),
        "include": MemberSpec_("include", "xs:string", 0, 1, {"use": "optional"}),
        "exclude": MemberSpec_("exclude", "xs:string", 0, 1, {"use": "optional"}),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_)
    subclass = None
    superclass = None

    def __init__(
        self,
        id=None,
        version=None,
        include=None,
        exclude=None,
        gds_collector_=None,
        **kwargs_
    ):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        self.id = _cast(None, id)
        self.id_nsprefix_ = None
        self.version = _cast(None, version)
        self.version_nsprefix_ = None
        self.include = _cast(None, include)
        self.include_nsprefix_ = None
        self.exclude = _cast(None, exclude)
        self.exclude_nsprefix_ = None

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(CurrentSubclassModule_, dependency)
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if dependency.subclass:
            return dependency.subclass(*args_, **kwargs_)
        else:
            return dependency(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_id(self):
        return self.id

    def set_id(self, id):
        self.id = id

    def get_version(self):
        return self.version

    def set_version(self, version):
        self.version = version

    def get_include(self):
        return self.include

    def set_include(self, include):
        self.include = include

    def get_exclude(self):
        return self.exclude

    def set_exclude(self, exclude):
        self.exclude = exclude

    def hasContent_(self):
        if ():
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"',
        name_="dependency",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("dependency")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "dependency":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile, level, already_processed, namespaceprefix_, name_="dependency"
        )
        if self.hasContent_():
            outfile.write(">%s" % (eol_,))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="dependency",
                pretty_print=pretty_print,
            )
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self, outfile, level, already_processed, namespaceprefix_="", name_="dependency"
    ):
        if self.id is not None and "id" not in already_processed:
            already_processed.add("id")
            outfile.write(
                " id=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(quote_attrib(self.id), input_name="id")
                    ),
                )
            )
        if self.version is not None and "version" not in already_processed:
            already_processed.add("version")
            outfile.write(
                " version=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.version), input_name="version"
                        )
                    ),
                )
            )
        if self.include is not None and "include" not in already_processed:
            already_processed.add("include")
            outfile.write(
                " include=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.include), input_name="include"
                        )
                    ),
                )
            )
        if self.exclude is not None and "exclude" not in already_processed:
            already_processed.add("exclude")
            outfile.write(
                " exclude=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.exclude), input_name="exclude"
                        )
                    ),
                )
            )

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"',
        name_="dependency",
        fromsubclass_=False,
        pretty_print=True,
    ):
        pass

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.id, "id")
        self.gds_check_cardinality_(self.id, "id", required=True)
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.version, "version")
        self.gds_check_cardinality_(self.version, "version", required=False)
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.include, "include")
        self.gds_check_cardinality_(self.include, "include", required=False)
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.exclude, "exclude")
        self.gds_check_cardinality_(self.exclude, "exclude", required=False)
        # validate simple type children
        # validate complex type children
        if recursive:
            pass
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        value = find_attr_value_("id", node)
        if value is not None and "id" not in already_processed:
            already_processed.add("id")
            self.id = value
        value = find_attr_value_("version", node)
        if value is not None and "version" not in already_processed:
            already_processed.add("version")
            self.version = value
        value = find_attr_value_("include", node)
        if value is not None and "include" not in already_processed:
            already_processed.add("include")
            self.include = value
        value = find_attr_value_("exclude", node)
        if value is not None and "exclude" not in already_processed:
            already_processed.add("exclude")
            self.exclude = value

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        pass


# end class dependency


class dependencyGroup(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "targetFramework": MemberSpec_(
            "targetFramework", "xs:string", 0, 1, {"use": "optional"}
        ),
        "dependency": MemberSpec_(
            "dependency",
            "dependency",
            1,
            1,
            {
                "maxOccurs": "unbounded",
                "minOccurs": "0",
                "name": "dependency",
                "type": "dependency",
            },
            None,
        ),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_)
    subclass = None
    superclass = None

    def __init__(
        self, targetFramework=None, dependency=None, gds_collector_=None, **kwargs_
    ):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        self.targetFramework = _cast(None, targetFramework)
        self.targetFramework_nsprefix_ = None
        if dependency is None:
            self.dependency = []
        else:
            self.dependency = dependency
        self.dependency_nsprefix_ = None

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(CurrentSubclassModule_, dependencyGroup)
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if dependencyGroup.subclass:
            return dependencyGroup.subclass(*args_, **kwargs_)
        else:
            return dependencyGroup(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_dependency(self):
        return self.dependency

    def set_dependency(self, dependency):
        self.dependency = dependency

    def add_dependency(self, value):
        self.dependency.append(value)

    def insert_dependency_at(self, index, value):
        self.dependency.insert(index, value)

    def replace_dependency_at(self, index, value):
        self.dependency[index] = value

    def get_targetFramework(self):
        return self.targetFramework

    def set_targetFramework(self, targetFramework):
        self.targetFramework = targetFramework

    def hasContent_(self):
        if self.dependency:
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="dependencyGroup",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("dependencyGroup")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "dependencyGroup":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile, level, already_processed, namespaceprefix_, name_="dependencyGroup"
        )
        if self.hasContent_():
            outfile.write(">%s" % (eol_,))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="dependencyGroup",
                pretty_print=pretty_print,
            )
            showIndent(outfile, level, pretty_print)
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self,
        outfile,
        level,
        already_processed,
        namespaceprefix_="",
        name_="dependencyGroup",
    ):
        if (
            self.targetFramework is not None
            and "targetFramework" not in already_processed
        ):
            already_processed.add("targetFramework")
            outfile.write(
                " targetFramework=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.targetFramework),
                            input_name="targetFramework",
                        )
                    ),
                )
            )

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="dependencyGroup",
        fromsubclass_=False,
        pretty_print=True,
    ):
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        for dependency_ in self.dependency:
            namespaceprefix_ = (
                self.dependency_nsprefix_ + ":"
                if (UseCapturedNS_ and self.dependency_nsprefix_)
                else ""
            )
            dependency_.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="dependency",
                pretty_print=pretty_print,
            )

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        self.gds_validate_builtin_ST_(
            self.gds_validate_string, self.targetFramework, "targetFramework"
        )
        self.gds_check_cardinality_(
            self.targetFramework, "targetFramework", required=False
        )
        # validate simple type children
        # validate complex type children
        self.gds_check_cardinality_(
            self.dependency, "dependency", min_occurs=0, max_occurs=9999999
        )
        if recursive:
            for item in self.dependency:
                item.validate_(gds_collector, recursive=True)
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        value = find_attr_value_("targetFramework", node)
        if value is not None and "targetFramework" not in already_processed:
            already_processed.add("targetFramework")
            self.targetFramework = value

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        if nodeName_ == "dependency":
            obj_ = dependency.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.dependency.append(obj_)
            obj_.original_tagname_ = "dependency"


# end class dependencyGroup


class reference(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "file": MemberSpec_("file", "xs:string", 0, 0, {"use": "required"}),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_)
    subclass = None
    superclass = None

    def __init__(self, file=None, gds_collector_=None, **kwargs_):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        self.file = _cast(None, file)
        self.file_nsprefix_ = None

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(CurrentSubclassModule_, reference)
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if reference.subclass:
            return reference.subclass(*args_, **kwargs_)
        else:
            return reference(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_file(self):
        return self.file

    def set_file(self, file):
        self.file = file

    def hasContent_(self):
        if ():
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"',
        name_="reference",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("reference")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "reference":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile, level, already_processed, namespaceprefix_, name_="reference"
        )
        if self.hasContent_():
            outfile.write(">%s" % (eol_,))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="reference",
                pretty_print=pretty_print,
            )
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self, outfile, level, already_processed, namespaceprefix_="", name_="reference"
    ):
        if self.file is not None and "file" not in already_processed:
            already_processed.add("file")
            outfile.write(
                " file=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.file), input_name="file"
                        )
                    ),
                )
            )

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"',
        name_="reference",
        fromsubclass_=False,
        pretty_print=True,
    ):
        pass

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.file, "file")
        self.gds_check_cardinality_(self.file, "file", required=True)
        # validate simple type children
        # validate complex type children
        if recursive:
            pass
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        value = find_attr_value_("file", node)
        if value is not None and "file" not in already_processed:
            already_processed.add("file")
            self.file = value

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        pass


# end class reference


class contentFileEntries(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "include": MemberSpec_("include", "xs:string", 0, 0, {"use": "required"}),
        "exclude": MemberSpec_("exclude", "xs:string", 0, 1, {"use": "optional"}),
        "buildAction": MemberSpec_(
            "buildAction", "xs:string", 0, 1, {"use": "optional"}
        ),
        "copyToOutput": MemberSpec_(
            "copyToOutput", "xs:boolean", 0, 1, {"use": "optional"}
        ),
        "flatten": MemberSpec_("flatten", "xs:boolean", 0, 1, {"use": "optional"}),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_)
    subclass = None
    superclass = None

    def __init__(
        self,
        include=None,
        exclude=None,
        buildAction=None,
        copyToOutput=None,
        flatten=None,
        gds_collector_=None,
        **kwargs_
    ):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        self.include = _cast(None, include)
        self.include_nsprefix_ = None
        self.exclude = _cast(None, exclude)
        self.exclude_nsprefix_ = None
        self.buildAction = _cast(None, buildAction)
        self.buildAction_nsprefix_ = None
        self.copyToOutput = _cast(bool, copyToOutput)
        self.copyToOutput_nsprefix_ = None
        self.flatten = _cast(bool, flatten)
        self.flatten_nsprefix_ = None

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(
                CurrentSubclassModule_, contentFileEntries
            )
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if contentFileEntries.subclass:
            return contentFileEntries.subclass(*args_, **kwargs_)
        else:
            return contentFileEntries(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_include(self):
        return self.include

    def set_include(self, include):
        self.include = include

    def get_exclude(self):
        return self.exclude

    def set_exclude(self, exclude):
        self.exclude = exclude

    def get_buildAction(self):
        return self.buildAction

    def set_buildAction(self, buildAction):
        self.buildAction = buildAction

    def get_copyToOutput(self):
        return self.copyToOutput

    def set_copyToOutput(self, copyToOutput):
        self.copyToOutput = copyToOutput

    def get_flatten(self):
        return self.flatten

    def set_flatten(self, flatten):
        self.flatten = flatten

    def hasContent_(self):
        if ():
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"',
        name_="contentFileEntries",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("contentFileEntries")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "contentFileEntries":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile,
            level,
            already_processed,
            namespaceprefix_,
            name_="contentFileEntries",
        )
        if self.hasContent_():
            outfile.write(">%s" % (eol_,))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="contentFileEntries",
                pretty_print=pretty_print,
            )
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self,
        outfile,
        level,
        already_processed,
        namespaceprefix_="",
        name_="contentFileEntries",
    ):
        if self.include is not None and "include" not in already_processed:
            already_processed.add("include")
            outfile.write(
                " include=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.include), input_name="include"
                        )
                    ),
                )
            )
        if self.exclude is not None and "exclude" not in already_processed:
            already_processed.add("exclude")
            outfile.write(
                " exclude=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.exclude), input_name="exclude"
                        )
                    ),
                )
            )
        if self.buildAction is not None and "buildAction" not in already_processed:
            already_processed.add("buildAction")
            outfile.write(
                " buildAction=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.buildAction), input_name="buildAction"
                        )
                    ),
                )
            )
        if self.copyToOutput is not None and "copyToOutput" not in already_processed:
            already_processed.add("copyToOutput")
            outfile.write(
                ' copyToOutput="%s"'
                % self.gds_format_boolean(self.copyToOutput, input_name="copyToOutput")
            )
        if self.flatten is not None and "flatten" not in already_processed:
            already_processed.add("flatten")
            outfile.write(
                ' flatten="%s"'
                % self.gds_format_boolean(self.flatten, input_name="flatten")
            )

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"',
        name_="contentFileEntries",
        fromsubclass_=False,
        pretty_print=True,
    ):
        pass

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.include, "include")
        self.gds_check_cardinality_(self.include, "include", required=True)
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.exclude, "exclude")
        self.gds_check_cardinality_(self.exclude, "exclude", required=False)
        self.gds_validate_builtin_ST_(
            self.gds_validate_string, self.buildAction, "buildAction"
        )
        self.gds_check_cardinality_(self.buildAction, "buildAction", required=False)
        self.gds_validate_builtin_ST_(
            self.gds_validate_boolean, self.copyToOutput, "copyToOutput"
        )
        self.gds_check_cardinality_(self.copyToOutput, "copyToOutput", required=False)
        self.gds_validate_builtin_ST_(
            self.gds_validate_boolean, self.flatten, "flatten"
        )
        self.gds_check_cardinality_(self.flatten, "flatten", required=False)
        # validate simple type children
        # validate complex type children
        if recursive:
            pass
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        value = find_attr_value_("include", node)
        if value is not None and "include" not in already_processed:
            already_processed.add("include")
            self.include = value
        value = find_attr_value_("exclude", node)
        if value is not None and "exclude" not in already_processed:
            already_processed.add("exclude")
            self.exclude = value
        value = find_attr_value_("buildAction", node)
        if value is not None and "buildAction" not in already_processed:
            already_processed.add("buildAction")
            self.buildAction = value
        value = find_attr_value_("copyToOutput", node)
        if value is not None and "copyToOutput" not in already_processed:
            already_processed.add("copyToOutput")
            if value in ("true", "1"):
                self.copyToOutput = True
            elif value in ("false", "0"):
                self.copyToOutput = False
            else:
                raise_parse_error(node, "Bad boolean attribute")
        value = find_attr_value_("flatten", node)
        if value is not None and "flatten" not in already_processed:
            already_processed.add("flatten")
            if value in ("true", "1"):
                self.flatten = True
            elif value in ("false", "0"):
                self.flatten = False
            else:
                raise_parse_error(node, "Bad boolean attribute")

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        pass


# end class contentFileEntries


class referenceGroup(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "targetFramework": MemberSpec_(
            "targetFramework", "xs:string", 0, 1, {"use": "optional"}
        ),
        "reference": MemberSpec_(
            "reference",
            "reference",
            1,
            0,
            {
                "maxOccurs": "unbounded",
                "minOccurs": "1",
                "name": "reference",
                "type": "reference",
            },
            None,
        ),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_)
    subclass = None
    superclass = None

    def __init__(
        self, targetFramework=None, reference=None, gds_collector_=None, **kwargs_
    ):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        self.targetFramework = _cast(None, targetFramework)
        self.targetFramework_nsprefix_ = None
        if reference is None:
            self.reference = []
        else:
            self.reference = reference
        self.reference_nsprefix_ = None

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(CurrentSubclassModule_, referenceGroup)
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if referenceGroup.subclass:
            return referenceGroup.subclass(*args_, **kwargs_)
        else:
            return referenceGroup(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_reference(self):
        return self.reference

    def set_reference(self, reference):
        self.reference = reference

    def add_reference(self, value):
        self.reference.append(value)

    def insert_reference_at(self, index, value):
        self.reference.insert(index, value)

    def replace_reference_at(self, index, value):
        self.reference[index] = value

    def get_targetFramework(self):
        return self.targetFramework

    def set_targetFramework(self, targetFramework):
        self.targetFramework = targetFramework

    def hasContent_(self):
        if self.reference:
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="referenceGroup",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("referenceGroup")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "referenceGroup":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile, level, already_processed, namespaceprefix_, name_="referenceGroup"
        )
        if self.hasContent_():
            outfile.write(">%s" % (eol_,))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="referenceGroup",
                pretty_print=pretty_print,
            )
            showIndent(outfile, level, pretty_print)
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self,
        outfile,
        level,
        already_processed,
        namespaceprefix_="",
        name_="referenceGroup",
    ):
        if (
            self.targetFramework is not None
            and "targetFramework" not in already_processed
        ):
            already_processed.add("targetFramework")
            outfile.write(
                " targetFramework=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.targetFramework),
                            input_name="targetFramework",
                        )
                    ),
                )
            )

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="referenceGroup",
        fromsubclass_=False,
        pretty_print=True,
    ):
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        for reference_ in self.reference:
            namespaceprefix_ = (
                self.reference_nsprefix_ + ":"
                if (UseCapturedNS_ and self.reference_nsprefix_)
                else ""
            )
            reference_.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="reference",
                pretty_print=pretty_print,
            )

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        self.gds_validate_builtin_ST_(
            self.gds_validate_string, self.targetFramework, "targetFramework"
        )
        self.gds_check_cardinality_(
            self.targetFramework, "targetFramework", required=False
        )
        # validate simple type children
        # validate complex type children
        self.gds_check_cardinality_(
            self.reference, "reference", min_occurs=1, max_occurs=9999999
        )
        if recursive:
            for item in self.reference:
                item.validate_(gds_collector, recursive=True)
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        value = find_attr_value_("targetFramework", node)
        if value is not None and "targetFramework" not in already_processed:
            already_processed.add("targetFramework")
            self.targetFramework = value

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        if nodeName_ == "reference":
            obj_ = reference.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.reference.append(obj_)
            obj_.original_tagname_ = "reference"


# end class referenceGroup


class frameworkReference(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "name": MemberSpec_("name", "xs:string", 0, 0, {"use": "required"}),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_)
    subclass = None
    superclass = None

    def __init__(self, name=None, gds_collector_=None, **kwargs_):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        self.name = _cast(None, name)
        self.name_nsprefix_ = None

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(
                CurrentSubclassModule_, frameworkReference
            )
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if frameworkReference.subclass:
            return frameworkReference.subclass(*args_, **kwargs_)
        else:
            return frameworkReference(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def hasContent_(self):
        if ():
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"',
        name_="frameworkReference",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("frameworkReference")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "frameworkReference":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile,
            level,
            already_processed,
            namespaceprefix_,
            name_="frameworkReference",
        )
        if self.hasContent_():
            outfile.write(">%s" % (eol_,))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="frameworkReference",
                pretty_print=pretty_print,
            )
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self,
        outfile,
        level,
        already_processed,
        namespaceprefix_="",
        name_="frameworkReference",
    ):
        if self.name is not None and "name" not in already_processed:
            already_processed.add("name")
            outfile.write(
                " name=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.name), input_name="name"
                        )
                    ),
                )
            )

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"',
        name_="frameworkReference",
        fromsubclass_=False,
        pretty_print=True,
    ):
        pass

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.name, "name")
        self.gds_check_cardinality_(self.name, "name", required=True)
        # validate simple type children
        # validate complex type children
        if recursive:
            pass
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        value = find_attr_value_("name", node)
        if value is not None and "name" not in already_processed:
            already_processed.add("name")
            self.name = value

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        pass


# end class frameworkReference


class frameworkReferenceGroup(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "targetFramework": MemberSpec_(
            "targetFramework", "xs:string", 0, 0, {"use": "required"}
        ),
        "frameworkReference": MemberSpec_(
            "frameworkReference",
            "frameworkReference",
            1,
            1,
            {
                "maxOccurs": "unbounded",
                "minOccurs": "0",
                "name": "frameworkReference",
                "type": "frameworkReference",
            },
            None,
        ),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_)
    subclass = None
    superclass = None

    def __init__(
        self,
        targetFramework=None,
        frameworkReference=None,
        gds_collector_=None,
        **kwargs_
    ):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        self.targetFramework = _cast(None, targetFramework)
        self.targetFramework_nsprefix_ = None
        if frameworkReference is None:
            self.frameworkReference = []
        else:
            self.frameworkReference = frameworkReference
        self.frameworkReference_nsprefix_ = None

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(
                CurrentSubclassModule_, frameworkReferenceGroup
            )
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if frameworkReferenceGroup.subclass:
            return frameworkReferenceGroup.subclass(*args_, **kwargs_)
        else:
            return frameworkReferenceGroup(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_frameworkReference(self):
        return self.frameworkReference

    def set_frameworkReference(self, frameworkReference):
        self.frameworkReference = frameworkReference

    def add_frameworkReference(self, value):
        self.frameworkReference.append(value)

    def insert_frameworkReference_at(self, index, value):
        self.frameworkReference.insert(index, value)

    def replace_frameworkReference_at(self, index, value):
        self.frameworkReference[index] = value

    def get_targetFramework(self):
        return self.targetFramework

    def set_targetFramework(self, targetFramework):
        self.targetFramework = targetFramework

    def hasContent_(self):
        if self.frameworkReference:
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="frameworkReferenceGroup",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("frameworkReferenceGroup")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "frameworkReferenceGroup":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile,
            level,
            already_processed,
            namespaceprefix_,
            name_="frameworkReferenceGroup",
        )
        if self.hasContent_():
            outfile.write(">%s" % (eol_,))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="frameworkReferenceGroup",
                pretty_print=pretty_print,
            )
            showIndent(outfile, level, pretty_print)
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self,
        outfile,
        level,
        already_processed,
        namespaceprefix_="",
        name_="frameworkReferenceGroup",
    ):
        if (
            self.targetFramework is not None
            and "targetFramework" not in already_processed
        ):
            already_processed.add("targetFramework")
            outfile.write(
                " targetFramework=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.targetFramework),
                            input_name="targetFramework",
                        )
                    ),
                )
            )

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="frameworkReferenceGroup",
        fromsubclass_=False,
        pretty_print=True,
    ):
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        for frameworkReference_ in self.frameworkReference:
            namespaceprefix_ = (
                self.frameworkReference_nsprefix_ + ":"
                if (UseCapturedNS_ and self.frameworkReference_nsprefix_)
                else ""
            )
            frameworkReference_.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="frameworkReference",
                pretty_print=pretty_print,
            )

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        self.gds_validate_builtin_ST_(
            self.gds_validate_string, self.targetFramework, "targetFramework"
        )
        self.gds_check_cardinality_(
            self.targetFramework, "targetFramework", required=True
        )
        # validate simple type children
        # validate complex type children
        self.gds_check_cardinality_(
            self.frameworkReference,
            "frameworkReference",
            min_occurs=0,
            max_occurs=9999999,
        )
        if recursive:
            for item in self.frameworkReference:
                item.validate_(gds_collector, recursive=True)
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        value = find_attr_value_("targetFramework", node)
        if value is not None and "targetFramework" not in already_processed:
            already_processed.add("targetFramework")
            self.targetFramework = value

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        if nodeName_ == "frameworkReference":
            obj_ = frameworkReference.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.frameworkReference.append(obj_)
            obj_.original_tagname_ = "frameworkReference"


# end class frameworkReferenceGroup


class package(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "metadata": MemberSpec_(
            "metadata",
            "metadataType",
            0,
            0,
            {
                "maxOccurs": "1",
                "minOccurs": "1",
                "name": "metadata",
                "type": "metadataType",
            },
            None,
        ),
        "files": MemberSpec_(
            "files",
            "filesType",
            0,
            1,
            {
                "maxOccurs": "1",
                "minOccurs": "0",
                "name": "files",
                "nillable": "true",
                "type": "filesType",
            },
            None,
        ),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_)
    subclass = None
    superclass = None

    def __init__(self, metadata=None, files=None, gds_collector_=None, **kwargs_):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        self.metadata = metadata
        self.metadata_nsprefix_ = None
        self.files = files
        self.files_nsprefix_ = None

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(CurrentSubclassModule_, package)
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if package.subclass:
            return package.subclass(*args_, **kwargs_)
        else:
            return package(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_metadata(self):
        return self.metadata

    def set_metadata(self, metadata):
        self.metadata = metadata

    def get_files(self):
        return self.files

    def set_files(self, files):
        self.files = files

    def hasContent_(self):
        if self.metadata is not None or self.files is not None:
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="package",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("package")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "package":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile, level, already_processed, namespaceprefix_, name_="package"
        )
        if self.hasContent_():
            outfile.write(">%s" % (eol_,))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="package",
                pretty_print=pretty_print,
            )
            showIndent(outfile, level, pretty_print)
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self, outfile, level, already_processed, namespaceprefix_="", name_="package"
    ):
        pass

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="package",
        fromsubclass_=False,
        pretty_print=True,
    ):
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.metadata is not None:
            namespaceprefix_ = (
                self.metadata_nsprefix_ + ":"
                if (UseCapturedNS_ and self.metadata_nsprefix_)
                else ""
            )
            self.metadata.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="metadata",
                pretty_print=pretty_print,
            )
        if self.files is not None:
            namespaceprefix_ = (
                self.files_nsprefix_ + ":"
                if (UseCapturedNS_ and self.files_nsprefix_)
                else ""
            )
            self.files.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="files",
                pretty_print=pretty_print,
            )

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        # validate simple type children
        # validate complex type children
        self.gds_check_cardinality_(
            self.metadata, "metadata", min_occurs=1, max_occurs=1
        )
        self.gds_check_cardinality_(self.files, "files", min_occurs=0, max_occurs=1)
        if recursive:
            if self.metadata is not None:
                self.metadata.validate_(gds_collector, recursive=True)
            if self.files is not None:
                self.files.validate_(gds_collector, recursive=True)
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        pass

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        if nodeName_ == "metadata":
            obj_ = metadataType.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.metadata = obj_
            obj_.original_tagname_ = "metadata"
        elif nodeName_ == "files":
            obj_ = filesType.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.files = obj_
            obj_.original_tagname_ = "files"


# end class package


class metadataType(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "minClientVersion": MemberSpec_(
            "minClientVersion", "xs:string", 0, 1, {"use": "optional"}
        ),
        "id": MemberSpec_(
            "id",
            "xs:string",
            0,
            0,
            {"maxOccurs": "1", "minOccurs": "1", "name": "id", "type": "xs:string"},
            None,
        ),
        "version": MemberSpec_(
            "version",
            "xs:string",
            0,
            0,
            {
                "maxOccurs": "1",
                "minOccurs": "1",
                "name": "version",
                "type": "xs:string",
            },
            None,
        ),
        "title": MemberSpec_(
            "title",
            "xs:string",
            0,
            1,
            {"maxOccurs": "1", "minOccurs": "0", "name": "title", "type": "xs:string"},
            None,
        ),
        "authors": MemberSpec_(
            "authors",
            "xs:string",
            0,
            0,
            {
                "maxOccurs": "1",
                "minOccurs": "1",
                "name": "authors",
                "type": "xs:string",
            },
            None,
        ),
        "owners": MemberSpec_(
            "owners",
            "xs:string",
            0,
            1,
            {"maxOccurs": "1", "minOccurs": "0", "name": "owners", "type": "xs:string"},
            None,
        ),
        "licenseUrl": MemberSpec_(
            "licenseUrl",
            "xs:anyURI",
            0,
            1,
            {
                "maxOccurs": "1",
                "minOccurs": "0",
                "name": "licenseUrl",
                "type": "xs:anyURI",
            },
            None,
        ),
        "projectUrl": MemberSpec_(
            "projectUrl",
            "xs:anyURI",
            0,
            1,
            {
                "maxOccurs": "1",
                "minOccurs": "0",
                "name": "projectUrl",
                "type": "xs:anyURI",
            },
            None,
        ),
        "iconUrl": MemberSpec_(
            "iconUrl",
            "xs:anyURI",
            0,
            1,
            {
                "maxOccurs": "1",
                "minOccurs": "0",
                "name": "iconUrl",
                "type": "xs:anyURI",
            },
            None,
        ),
        "requireLicenseAcceptance": MemberSpec_(
            "requireLicenseAcceptance",
            "xs:boolean",
            0,
            1,
            {
                "maxOccurs": "1",
                "minOccurs": "0",
                "name": "requireLicenseAcceptance",
                "type": "xs:boolean",
            },
            None,
        ),
        "developmentDependency": MemberSpec_(
            "developmentDependency",
            "xs:boolean",
            0,
            1,
            {
                "maxOccurs": "1",
                "minOccurs": "0",
                "name": "developmentDependency",
                "type": "xs:boolean",
            },
            None,
        ),
        "description": MemberSpec_(
            "description",
            "xs:string",
            0,
            0,
            {
                "maxOccurs": "1",
                "minOccurs": "1",
                "name": "description",
                "type": "xs:string",
            },
            None,
        ),
        "summary": MemberSpec_(
            "summary",
            "xs:string",
            0,
            1,
            {
                "maxOccurs": "1",
                "minOccurs": "0",
                "name": "summary",
                "type": "xs:string",
            },
            None,
        ),
        "releaseNotes": MemberSpec_(
            "releaseNotes",
            "xs:string",
            0,
            1,
            {
                "maxOccurs": "1",
                "minOccurs": "0",
                "name": "releaseNotes",
                "type": "xs:string",
            },
            None,
        ),
        "copyright": MemberSpec_(
            "copyright",
            "xs:string",
            0,
            1,
            {
                "maxOccurs": "1",
                "minOccurs": "0",
                "name": "copyright",
                "type": "xs:string",
            },
            None,
        ),
        "language": MemberSpec_(
            "language",
            "xs:string",
            0,
            1,
            {
                "default": "en-US",
                "maxOccurs": "1",
                "minOccurs": "0",
                "name": "language",
                "type": "xs:string",
            },
            None,
        ),
        "tags": MemberSpec_(
            "tags",
            "xs:string",
            0,
            1,
            {"maxOccurs": "1", "minOccurs": "0", "name": "tags", "type": "xs:string"},
            None,
        ),
        "serviceable": MemberSpec_(
            "serviceable",
            "xs:boolean",
            0,
            1,
            {
                "maxOccurs": "1",
                "minOccurs": "0",
                "name": "serviceable",
                "type": "xs:boolean",
            },
            None,
        ),
        "icon": MemberSpec_(
            "icon",
            "xs:string",
            0,
            1,
            {"maxOccurs": "1", "minOccurs": "0", "name": "icon", "type": "xs:string"},
            None,
        ),
        "repository": MemberSpec_(
            "repository",
            "repositoryType",
            0,
            1,
            {
                "maxOccurs": "1",
                "minOccurs": "0",
                "name": "repository",
                "type": "repositoryType",
            },
            None,
        ),
        "license": MemberSpec_(
            "license",
            "licenseType",
            0,
            1,
            {
                "maxOccurs": "1",
                "minOccurs": "0",
                "name": "license",
                "type": "licenseType",
            },
            None,
        ),
        "packageTypes": MemberSpec_(
            "packageTypes",
            "packageTypesType",
            0,
            1,
            {
                "maxOccurs": "1",
                "minOccurs": "0",
                "name": "packageTypes",
                "type": "packageTypesType",
            },
            None,
        ),
        "dependencies": MemberSpec_(
            "dependencies",
            "dependenciesType",
            0,
            1,
            {
                "maxOccurs": "1",
                "minOccurs": "0",
                "name": "dependencies",
                "type": "dependenciesType",
            },
            None,
        ),
        "frameworkAssemblies": MemberSpec_(
            "frameworkAssemblies",
            "frameworkAssembliesType",
            0,
            1,
            {
                "maxOccurs": "1",
                "minOccurs": "0",
                "name": "frameworkAssemblies",
                "type": "frameworkAssembliesType",
            },
            None,
        ),
        "frameworkReferences": MemberSpec_(
            "frameworkReferences",
            "frameworkReferencesType",
            0,
            1,
            {
                "maxOccurs": "1",
                "minOccurs": "0",
                "name": "frameworkReferences",
                "type": "frameworkReferencesType",
            },
            None,
        ),
        "references": MemberSpec_(
            "references",
            "referencesType",
            0,
            1,
            {
                "maxOccurs": "1",
                "minOccurs": "0",
                "name": "references",
                "type": "referencesType",
            },
            None,
        ),
        "contentFiles": MemberSpec_(
            "contentFiles",
            "contentFilesType",
            0,
            1,
            {
                "maxOccurs": "1",
                "minOccurs": "0",
                "name": "contentFiles",
                "type": "contentFilesType",
            },
            None,
        ),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_)
    subclass = None
    superclass = None

    def __init__(
        self,
        minClientVersion=None,
        id=None,
        version=None,
        title=None,
        authors=None,
        owners=None,
        licenseUrl=None,
        projectUrl=None,
        iconUrl=None,
        requireLicenseAcceptance=None,
        developmentDependency=None,
        description=None,
        summary=None,
        releaseNotes=None,
        copyright=None,
        language="en-US",
        tags=None,
        serviceable=None,
        icon=None,
        repository=None,
        license=None,
        packageTypes=None,
        dependencies=None,
        frameworkAssemblies=None,
        frameworkReferences=None,
        references=None,
        contentFiles=None,
        gds_collector_=None,
        **kwargs_
    ):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        self.minClientVersion = _cast(None, minClientVersion)
        self.minClientVersion_nsprefix_ = None
        self.id = id
        self.id_nsprefix_ = None
        self.version = version
        self.version_nsprefix_ = None
        self.title = title
        self.title_nsprefix_ = None
        self.authors = authors
        self.authors_nsprefix_ = None
        self.owners = owners
        self.owners_nsprefix_ = None
        self.licenseUrl = licenseUrl
        self.licenseUrl_nsprefix_ = None
        self.projectUrl = projectUrl
        self.projectUrl_nsprefix_ = None
        self.iconUrl = iconUrl
        self.iconUrl_nsprefix_ = None
        self.requireLicenseAcceptance = requireLicenseAcceptance
        self.requireLicenseAcceptance_nsprefix_ = None
        self.developmentDependency = developmentDependency
        self.developmentDependency_nsprefix_ = None
        self.description = description
        self.description_nsprefix_ = None
        self.summary = summary
        self.summary_nsprefix_ = None
        self.releaseNotes = releaseNotes
        self.releaseNotes_nsprefix_ = None
        self.copyright = copyright
        self.copyright_nsprefix_ = None
        self.language = language
        self.language_nsprefix_ = None
        self.tags = tags
        self.tags_nsprefix_ = None
        self.serviceable = serviceable
        self.serviceable_nsprefix_ = None
        self.icon = icon
        self.icon_nsprefix_ = None
        self.repository = repository
        self.repository_nsprefix_ = None
        self.license = license
        self.license_nsprefix_ = None
        self.packageTypes = packageTypes
        self.packageTypes_nsprefix_ = None
        self.dependencies = dependencies
        self.dependencies_nsprefix_ = None
        self.frameworkAssemblies = frameworkAssemblies
        self.frameworkAssemblies_nsprefix_ = None
        self.frameworkReferences = frameworkReferences
        self.frameworkReferences_nsprefix_ = None
        self.references = references
        self.references_nsprefix_ = None
        self.contentFiles = contentFiles
        self.contentFiles_nsprefix_ = None

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(CurrentSubclassModule_, metadataType)
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if metadataType.subclass:
            return metadataType.subclass(*args_, **kwargs_)
        else:
            return metadataType(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_id(self):
        return self.id

    def set_id(self, id):
        self.id = id

    def get_version(self):
        return self.version

    def set_version(self, version):
        self.version = version

    def get_title(self):
        return self.title

    def set_title(self, title):
        self.title = title

    def get_authors(self):
        return self.authors

    def set_authors(self, authors):
        self.authors = authors

    def get_owners(self):
        return self.owners

    def set_owners(self, owners):
        self.owners = owners

    def get_licenseUrl(self):
        return self.licenseUrl

    def set_licenseUrl(self, licenseUrl):
        self.licenseUrl = licenseUrl

    def get_projectUrl(self):
        return self.projectUrl

    def set_projectUrl(self, projectUrl):
        self.projectUrl = projectUrl

    def get_iconUrl(self):
        return self.iconUrl

    def set_iconUrl(self, iconUrl):
        self.iconUrl = iconUrl

    def get_requireLicenseAcceptance(self):
        return self.requireLicenseAcceptance

    def set_requireLicenseAcceptance(self, requireLicenseAcceptance):
        self.requireLicenseAcceptance = requireLicenseAcceptance

    def get_developmentDependency(self):
        return self.developmentDependency

    def set_developmentDependency(self, developmentDependency):
        self.developmentDependency = developmentDependency

    def get_description(self):
        return self.description

    def set_description(self, description):
        self.description = description

    def get_summary(self):
        return self.summary

    def set_summary(self, summary):
        self.summary = summary

    def get_releaseNotes(self):
        return self.releaseNotes

    def set_releaseNotes(self, releaseNotes):
        self.releaseNotes = releaseNotes

    def get_copyright(self):
        return self.copyright

    def set_copyright(self, copyright):
        self.copyright = copyright

    def get_language(self):
        return self.language

    def set_language(self, language):
        self.language = language

    def get_tags(self):
        return self.tags

    def set_tags(self, tags):
        self.tags = tags

    def get_serviceable(self):
        return self.serviceable

    def set_serviceable(self, serviceable):
        self.serviceable = serviceable

    def get_icon(self):
        return self.icon

    def set_icon(self, icon):
        self.icon = icon

    def get_repository(self):
        return self.repository

    def set_repository(self, repository):
        self.repository = repository

    def get_license(self):
        return self.license

    def set_license(self, license):
        self.license = license

    def get_packageTypes(self):
        return self.packageTypes

    def set_packageTypes(self, packageTypes):
        self.packageTypes = packageTypes

    def get_dependencies(self):
        return self.dependencies

    def set_dependencies(self, dependencies):
        self.dependencies = dependencies

    def get_frameworkAssemblies(self):
        return self.frameworkAssemblies

    def set_frameworkAssemblies(self, frameworkAssemblies):
        self.frameworkAssemblies = frameworkAssemblies

    def get_frameworkReferences(self):
        return self.frameworkReferences

    def set_frameworkReferences(self, frameworkReferences):
        self.frameworkReferences = frameworkReferences

    def get_references(self):
        return self.references

    def set_references(self, references):
        self.references = references

    def get_contentFiles(self):
        return self.contentFiles

    def set_contentFiles(self, contentFiles):
        self.contentFiles = contentFiles

    def get_minClientVersion(self):
        return self.minClientVersion

    def set_minClientVersion(self, minClientVersion):
        self.minClientVersion = minClientVersion

    def hasContent_(self):
        if (
            self.id is not None
            or self.version is not None
            or self.title is not None
            or self.authors is not None
            or self.owners is not None
            or self.licenseUrl is not None
            or self.projectUrl is not None
            or self.iconUrl is not None
            or self.requireLicenseAcceptance is not None
            or self.developmentDependency is not None
            or self.description is not None
            or self.summary is not None
            or self.releaseNotes is not None
            or self.copyright is not None
            or self.language != "en-US"
            or self.tags is not None
            or self.serviceable is not None
            or self.icon is not None
            or self.repository is not None
            or self.license is not None
            or self.packageTypes is not None
            or self.dependencies is not None
            or self.frameworkAssemblies is not None
            or self.frameworkReferences is not None
            or self.references is not None
            or self.contentFiles is not None
        ):
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="metadataType",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("metadataType")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "metadataType":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile, level, already_processed, namespaceprefix_, name_="metadataType"
        )
        if self.hasContent_():
            outfile.write(">%s" % (eol_,))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="metadataType",
                pretty_print=pretty_print,
            )
            showIndent(outfile, level, pretty_print)
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self,
        outfile,
        level,
        already_processed,
        namespaceprefix_="",
        name_="metadataType",
    ):
        if (
            self.minClientVersion is not None
            and "minClientVersion" not in already_processed
        ):
            already_processed.add("minClientVersion")
            outfile.write(
                " minClientVersion=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.minClientVersion),
                            input_name="minClientVersion",
                        )
                    ),
                )
            )

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="metadataType",
        fromsubclass_=False,
        pretty_print=True,
    ):
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.id is not None:
            namespaceprefix_ = (
                self.id_nsprefix_ + ":"
                if (UseCapturedNS_ and self.id_nsprefix_)
                else ""
            )
            showIndent(outfile, level, pretty_print)
            outfile.write(
                "<%sid>%s</%sid>%s"
                % (
                    namespaceprefix_,
                    self.gds_encode(
                        self.gds_format_string(quote_xml(self.id), input_name="id")
                    ),
                    namespaceprefix_,
                    eol_,
                )
            )
        if self.version is not None:
            namespaceprefix_ = (
                self.version_nsprefix_ + ":"
                if (UseCapturedNS_ and self.version_nsprefix_)
                else ""
            )
            showIndent(outfile, level, pretty_print)
            outfile.write(
                "<%sversion>%s</%sversion>%s"
                % (
                    namespaceprefix_,
                    self.gds_encode(
                        self.gds_format_string(
                            quote_xml(self.version), input_name="version"
                        )
                    ),
                    namespaceprefix_,
                    eol_,
                )
            )
        if self.title is not None:
            namespaceprefix_ = (
                self.title_nsprefix_ + ":"
                if (UseCapturedNS_ and self.title_nsprefix_)
                else ""
            )
            showIndent(outfile, level, pretty_print)
            outfile.write(
                "<%stitle>%s</%stitle>%s"
                % (
                    namespaceprefix_,
                    self.gds_encode(
                        self.gds_format_string(
                            quote_xml(self.title), input_name="title"
                        )
                    ),
                    namespaceprefix_,
                    eol_,
                )
            )
        if self.authors is not None:
            namespaceprefix_ = (
                self.authors_nsprefix_ + ":"
                if (UseCapturedNS_ and self.authors_nsprefix_)
                else ""
            )
            showIndent(outfile, level, pretty_print)
            outfile.write(
                "<%sauthors>%s</%sauthors>%s"
                % (
                    namespaceprefix_,
                    self.gds_encode(
                        self.gds_format_string(
                            quote_xml(self.authors), input_name="authors"
                        )
                    ),
                    namespaceprefix_,
                    eol_,
                )
            )
        if self.owners is not None:
            namespaceprefix_ = (
                self.owners_nsprefix_ + ":"
                if (UseCapturedNS_ and self.owners_nsprefix_)
                else ""
            )
            showIndent(outfile, level, pretty_print)
            outfile.write(
                "<%sowners>%s</%sowners>%s"
                % (
                    namespaceprefix_,
                    self.gds_encode(
                        self.gds_format_string(
                            quote_xml(self.owners), input_name="owners"
                        )
                    ),
                    namespaceprefix_,
                    eol_,
                )
            )
        if self.licenseUrl is not None:
            namespaceprefix_ = (
                self.licenseUrl_nsprefix_ + ":"
                if (UseCapturedNS_ and self.licenseUrl_nsprefix_)
                else ""
            )
            showIndent(outfile, level, pretty_print)
            outfile.write(
                "<%slicenseUrl>%s</%slicenseUrl>%s"
                % (
                    namespaceprefix_,
                    self.gds_encode(
                        self.gds_format_string(
                            quote_xml(self.licenseUrl), input_name="licenseUrl"
                        )
                    ),
                    namespaceprefix_,
                    eol_,
                )
            )
        if self.projectUrl is not None:
            namespaceprefix_ = (
                self.projectUrl_nsprefix_ + ":"
                if (UseCapturedNS_ and self.projectUrl_nsprefix_)
                else ""
            )
            showIndent(outfile, level, pretty_print)
            outfile.write(
                "<%sprojectUrl>%s</%sprojectUrl>%s"
                % (
                    namespaceprefix_,
                    self.gds_encode(
                        self.gds_format_string(
                            quote_xml(self.projectUrl), input_name="projectUrl"
                        )
                    ),
                    namespaceprefix_,
                    eol_,
                )
            )
        if self.iconUrl is not None:
            namespaceprefix_ = (
                self.iconUrl_nsprefix_ + ":"
                if (UseCapturedNS_ and self.iconUrl_nsprefix_)
                else ""
            )
            showIndent(outfile, level, pretty_print)
            outfile.write(
                "<%siconUrl>%s</%siconUrl>%s"
                % (
                    namespaceprefix_,
                    self.gds_encode(
                        self.gds_format_string(
                            quote_xml(self.iconUrl), input_name="iconUrl"
                        )
                    ),
                    namespaceprefix_,
                    eol_,
                )
            )
        if self.requireLicenseAcceptance is not None:
            namespaceprefix_ = (
                self.requireLicenseAcceptance_nsprefix_ + ":"
                if (UseCapturedNS_ and self.requireLicenseAcceptance_nsprefix_)
                else ""
            )
            showIndent(outfile, level, pretty_print)
            outfile.write(
                "<%srequireLicenseAcceptance>%s</%srequireLicenseAcceptance>%s"
                % (
                    namespaceprefix_,
                    self.gds_format_boolean(
                        self.requireLicenseAcceptance,
                        input_name="requireLicenseAcceptance",
                    ),
                    namespaceprefix_,
                    eol_,
                )
            )
        if self.developmentDependency is not None:
            namespaceprefix_ = (
                self.developmentDependency_nsprefix_ + ":"
                if (UseCapturedNS_ and self.developmentDependency_nsprefix_)
                else ""
            )
            showIndent(outfile, level, pretty_print)
            outfile.write(
                "<%sdevelopmentDependency>%s</%sdevelopmentDependency>%s"
                % (
                    namespaceprefix_,
                    self.gds_format_boolean(
                        self.developmentDependency, input_name="developmentDependency"
                    ),
                    namespaceprefix_,
                    eol_,
                )
            )
        if self.description is not None:
            namespaceprefix_ = (
                self.description_nsprefix_ + ":"
                if (UseCapturedNS_ and self.description_nsprefix_)
                else ""
            )
            showIndent(outfile, level, pretty_print)
            outfile.write(
                "<%sdescription>%s</%sdescription>%s"
                % (
                    namespaceprefix_,
                    self.gds_encode(
                        self.gds_format_string(
                            quote_xml(self.description), input_name="description"
                        )
                    ),
                    namespaceprefix_,
                    eol_,
                )
            )
        if self.summary is not None:
            namespaceprefix_ = (
                self.summary_nsprefix_ + ":"
                if (UseCapturedNS_ and self.summary_nsprefix_)
                else ""
            )
            showIndent(outfile, level, pretty_print)
            outfile.write(
                "<%ssummary>%s</%ssummary>%s"
                % (
                    namespaceprefix_,
                    self.gds_encode(
                        self.gds_format_string(
                            quote_xml(self.summary), input_name="summary"
                        )
                    ),
                    namespaceprefix_,
                    eol_,
                )
            )
        if self.releaseNotes is not None:
            namespaceprefix_ = (
                self.releaseNotes_nsprefix_ + ":"
                if (UseCapturedNS_ and self.releaseNotes_nsprefix_)
                else ""
            )
            showIndent(outfile, level, pretty_print)
            outfile.write(
                "<%sreleaseNotes>%s</%sreleaseNotes>%s"
                % (
                    namespaceprefix_,
                    self.gds_encode(
                        self.gds_format_string(
                            quote_xml(self.releaseNotes), input_name="releaseNotes"
                        )
                    ),
                    namespaceprefix_,
                    eol_,
                )
            )
        if self.copyright is not None:
            namespaceprefix_ = (
                self.copyright_nsprefix_ + ":"
                if (UseCapturedNS_ and self.copyright_nsprefix_)
                else ""
            )
            showIndent(outfile, level, pretty_print)
            outfile.write(
                "<%scopyright>%s</%scopyright>%s"
                % (
                    namespaceprefix_,
                    self.gds_encode(
                        self.gds_format_string(
                            quote_xml(self.copyright), input_name="copyright"
                        )
                    ),
                    namespaceprefix_,
                    eol_,
                )
            )
        if self.language != "en-US":
            namespaceprefix_ = (
                self.language_nsprefix_ + ":"
                if (UseCapturedNS_ and self.language_nsprefix_)
                else ""
            )
            showIndent(outfile, level, pretty_print)
            outfile.write(
                "<%slanguage>%s</%slanguage>%s"
                % (
                    namespaceprefix_,
                    self.gds_encode(
                        self.gds_format_string(
                            quote_xml(self.language), input_name="language"
                        )
                    ),
                    namespaceprefix_,
                    eol_,
                )
            )
        if self.tags is not None:
            namespaceprefix_ = (
                self.tags_nsprefix_ + ":"
                if (UseCapturedNS_ and self.tags_nsprefix_)
                else ""
            )
            showIndent(outfile, level, pretty_print)
            outfile.write(
                "<%stags>%s</%stags>%s"
                % (
                    namespaceprefix_,
                    self.gds_encode(
                        self.gds_format_string(quote_xml(self.tags), input_name="tags")
                    ),
                    namespaceprefix_,
                    eol_,
                )
            )
        if self.serviceable is not None:
            namespaceprefix_ = (
                self.serviceable_nsprefix_ + ":"
                if (UseCapturedNS_ and self.serviceable_nsprefix_)
                else ""
            )
            showIndent(outfile, level, pretty_print)
            outfile.write(
                "<%sserviceable>%s</%sserviceable>%s"
                % (
                    namespaceprefix_,
                    self.gds_format_boolean(self.serviceable, input_name="serviceable"),
                    namespaceprefix_,
                    eol_,
                )
            )
        if self.icon is not None:
            namespaceprefix_ = (
                self.icon_nsprefix_ + ":"
                if (UseCapturedNS_ and self.icon_nsprefix_)
                else ""
            )
            showIndent(outfile, level, pretty_print)
            outfile.write(
                "<%sicon>%s</%sicon>%s"
                % (
                    namespaceprefix_,
                    self.gds_encode(
                        self.gds_format_string(quote_xml(self.icon), input_name="icon")
                    ),
                    namespaceprefix_,
                    eol_,
                )
            )
        if self.repository is not None:
            namespaceprefix_ = (
                self.repository_nsprefix_ + ":"
                if (UseCapturedNS_ and self.repository_nsprefix_)
                else ""
            )
            self.repository.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="repository",
                pretty_print=pretty_print,
            )
        if self.license is not None:
            namespaceprefix_ = (
                self.license_nsprefix_ + ":"
                if (UseCapturedNS_ and self.license_nsprefix_)
                else ""
            )
            self.license.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="license",
                pretty_print=pretty_print,
            )
        if self.packageTypes is not None:
            namespaceprefix_ = (
                self.packageTypes_nsprefix_ + ":"
                if (UseCapturedNS_ and self.packageTypes_nsprefix_)
                else ""
            )
            self.packageTypes.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="packageTypes",
                pretty_print=pretty_print,
            )
        if self.dependencies is not None:
            namespaceprefix_ = (
                self.dependencies_nsprefix_ + ":"
                if (UseCapturedNS_ and self.dependencies_nsprefix_)
                else ""
            )
            self.dependencies.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="dependencies",
                pretty_print=pretty_print,
            )
        if self.frameworkAssemblies is not None:
            namespaceprefix_ = (
                self.frameworkAssemblies_nsprefix_ + ":"
                if (UseCapturedNS_ and self.frameworkAssemblies_nsprefix_)
                else ""
            )
            self.frameworkAssemblies.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="frameworkAssemblies",
                pretty_print=pretty_print,
            )
        if self.frameworkReferences is not None:
            namespaceprefix_ = (
                self.frameworkReferences_nsprefix_ + ":"
                if (UseCapturedNS_ and self.frameworkReferences_nsprefix_)
                else ""
            )
            self.frameworkReferences.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="frameworkReferences",
                pretty_print=pretty_print,
            )
        if self.references is not None:
            namespaceprefix_ = (
                self.references_nsprefix_ + ":"
                if (UseCapturedNS_ and self.references_nsprefix_)
                else ""
            )
            self.references.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="references",
                pretty_print=pretty_print,
            )
        if self.contentFiles is not None:
            namespaceprefix_ = (
                self.contentFiles_nsprefix_ + ":"
                if (UseCapturedNS_ and self.contentFiles_nsprefix_)
                else ""
            )
            self.contentFiles.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="contentFiles",
                pretty_print=pretty_print,
            )

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        self.gds_validate_builtin_ST_(
            self.gds_validate_string, self.minClientVersion, "minClientVersion"
        )
        self.gds_check_cardinality_(
            self.minClientVersion, "minClientVersion", required=False
        )
        # validate simple type children
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.id, "id")
        self.gds_check_cardinality_(self.id, "id", min_occurs=1, max_occurs=1)
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.version, "version")
        self.gds_check_cardinality_(self.version, "version", min_occurs=1, max_occurs=1)
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.title, "title")
        self.gds_check_cardinality_(self.title, "title", min_occurs=0, max_occurs=1)
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.authors, "authors")
        self.gds_check_cardinality_(self.authors, "authors", min_occurs=1, max_occurs=1)
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.owners, "owners")
        self.gds_check_cardinality_(self.owners, "owners", min_occurs=0, max_occurs=1)
        self.gds_validate_builtin_ST_(
            self.gds_validate_string, self.licenseUrl, "licenseUrl"
        )
        self.gds_check_cardinality_(
            self.licenseUrl, "licenseUrl", min_occurs=0, max_occurs=1
        )
        self.gds_validate_builtin_ST_(
            self.gds_validate_string, self.projectUrl, "projectUrl"
        )
        self.gds_check_cardinality_(
            self.projectUrl, "projectUrl", min_occurs=0, max_occurs=1
        )
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.iconUrl, "iconUrl")
        self.gds_check_cardinality_(self.iconUrl, "iconUrl", min_occurs=0, max_occurs=1)
        self.gds_validate_builtin_ST_(
            self.gds_validate_boolean,
            self.requireLicenseAcceptance,
            "requireLicenseAcceptance",
        )
        self.gds_check_cardinality_(
            self.requireLicenseAcceptance,
            "requireLicenseAcceptance",
            min_occurs=0,
            max_occurs=1,
        )
        self.gds_validate_builtin_ST_(
            self.gds_validate_boolean,
            self.developmentDependency,
            "developmentDependency",
        )
        self.gds_check_cardinality_(
            self.developmentDependency,
            "developmentDependency",
            min_occurs=0,
            max_occurs=1,
        )
        self.gds_validate_builtin_ST_(
            self.gds_validate_string, self.description, "description"
        )
        self.gds_check_cardinality_(
            self.description, "description", min_occurs=1, max_occurs=1
        )
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.summary, "summary")
        self.gds_check_cardinality_(self.summary, "summary", min_occurs=0, max_occurs=1)
        self.gds_validate_builtin_ST_(
            self.gds_validate_string, self.releaseNotes, "releaseNotes"
        )
        self.gds_check_cardinality_(
            self.releaseNotes, "releaseNotes", min_occurs=0, max_occurs=1
        )
        self.gds_validate_builtin_ST_(
            self.gds_validate_string, self.copyright, "copyright"
        )
        self.gds_check_cardinality_(
            self.copyright, "copyright", min_occurs=0, max_occurs=1
        )
        self.gds_validate_builtin_ST_(
            self.gds_validate_string, self.language, "language"
        )
        self.gds_check_cardinality_(
            self.language, "language", min_occurs=0, max_occurs=1
        )
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.tags, "tags")
        self.gds_check_cardinality_(self.tags, "tags", min_occurs=0, max_occurs=1)
        self.gds_validate_builtin_ST_(
            self.gds_validate_boolean, self.serviceable, "serviceable"
        )
        self.gds_check_cardinality_(
            self.serviceable, "serviceable", min_occurs=0, max_occurs=1
        )
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.icon, "icon")
        self.gds_check_cardinality_(self.icon, "icon", min_occurs=0, max_occurs=1)
        # validate complex type children
        self.gds_check_cardinality_(
            self.repository, "repository", min_occurs=0, max_occurs=1
        )
        self.gds_check_cardinality_(self.license, "license", min_occurs=0, max_occurs=1)
        self.gds_check_cardinality_(
            self.packageTypes, "packageTypes", min_occurs=0, max_occurs=1
        )
        self.gds_check_cardinality_(
            self.dependencies, "dependencies", min_occurs=0, max_occurs=1
        )
        self.gds_check_cardinality_(
            self.frameworkAssemblies, "frameworkAssemblies", min_occurs=0, max_occurs=1
        )
        self.gds_check_cardinality_(
            self.frameworkReferences, "frameworkReferences", min_occurs=0, max_occurs=1
        )
        self.gds_check_cardinality_(
            self.references, "references", min_occurs=0, max_occurs=1
        )
        self.gds_check_cardinality_(
            self.contentFiles, "contentFiles", min_occurs=0, max_occurs=1
        )
        if recursive:
            if self.repository is not None:
                self.repository.validate_(gds_collector, recursive=True)
            if self.license is not None:
                self.license.validate_(gds_collector, recursive=True)
            if self.packageTypes is not None:
                self.packageTypes.validate_(gds_collector, recursive=True)
            if self.dependencies is not None:
                self.dependencies.validate_(gds_collector, recursive=True)
            if self.frameworkAssemblies is not None:
                self.frameworkAssemblies.validate_(gds_collector, recursive=True)
            if self.frameworkReferences is not None:
                self.frameworkReferences.validate_(gds_collector, recursive=True)
            if self.references is not None:
                self.references.validate_(gds_collector, recursive=True)
            if self.contentFiles is not None:
                self.contentFiles.validate_(gds_collector, recursive=True)
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        value = find_attr_value_("minClientVersion", node)
        if value is not None and "minClientVersion" not in already_processed:
            already_processed.add("minClientVersion")
            self.minClientVersion = value

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        if nodeName_ == "id":
            value_ = child_.text
            value_ = self.gds_parse_string(value_, node, "id")
            value_ = self.gds_validate_string(value_, node, "id")
            self.id = value_
            self.id_nsprefix_ = child_.prefix
        elif nodeName_ == "version":
            value_ = child_.text
            value_ = self.gds_parse_string(value_, node, "version")
            value_ = self.gds_validate_string(value_, node, "version")
            self.version = value_
            self.version_nsprefix_ = child_.prefix
        elif nodeName_ == "title":
            value_ = child_.text
            value_ = self.gds_parse_string(value_, node, "title")
            value_ = self.gds_validate_string(value_, node, "title")
            self.title = value_
            self.title_nsprefix_ = child_.prefix
        elif nodeName_ == "authors":
            value_ = child_.text
            value_ = self.gds_parse_string(value_, node, "authors")
            value_ = self.gds_validate_string(value_, node, "authors")
            self.authors = value_
            self.authors_nsprefix_ = child_.prefix
        elif nodeName_ == "owners":
            value_ = child_.text
            value_ = self.gds_parse_string(value_, node, "owners")
            value_ = self.gds_validate_string(value_, node, "owners")
            self.owners = value_
            self.owners_nsprefix_ = child_.prefix
        elif nodeName_ == "licenseUrl":
            value_ = child_.text
            value_ = self.gds_parse_string(value_, node, "licenseUrl")
            value_ = self.gds_validate_string(value_, node, "licenseUrl")
            self.licenseUrl = value_
            self.licenseUrl_nsprefix_ = child_.prefix
        elif nodeName_ == "projectUrl":
            value_ = child_.text
            value_ = self.gds_parse_string(value_, node, "projectUrl")
            value_ = self.gds_validate_string(value_, node, "projectUrl")
            self.projectUrl = value_
            self.projectUrl_nsprefix_ = child_.prefix
        elif nodeName_ == "iconUrl":
            value_ = child_.text
            value_ = self.gds_parse_string(value_, node, "iconUrl")
            value_ = self.gds_validate_string(value_, node, "iconUrl")
            self.iconUrl = value_
            self.iconUrl_nsprefix_ = child_.prefix
        elif nodeName_ == "requireLicenseAcceptance":
            sval_ = child_.text
            ival_ = self.gds_parse_boolean(sval_, node, "requireLicenseAcceptance")
            ival_ = self.gds_validate_boolean(ival_, node, "requireLicenseAcceptance")
            self.requireLicenseAcceptance = ival_
            self.requireLicenseAcceptance_nsprefix_ = child_.prefix
        elif nodeName_ == "developmentDependency":
            sval_ = child_.text
            ival_ = self.gds_parse_boolean(sval_, node, "developmentDependency")
            ival_ = self.gds_validate_boolean(ival_, node, "developmentDependency")
            self.developmentDependency = ival_
            self.developmentDependency_nsprefix_ = child_.prefix
        elif nodeName_ == "description":
            value_ = child_.text
            value_ = self.gds_parse_string(value_, node, "description")
            value_ = self.gds_validate_string(value_, node, "description")
            self.description = value_
            self.description_nsprefix_ = child_.prefix
        elif nodeName_ == "summary":
            value_ = child_.text
            value_ = self.gds_parse_string(value_, node, "summary")
            value_ = self.gds_validate_string(value_, node, "summary")
            self.summary = value_
            self.summary_nsprefix_ = child_.prefix
        elif nodeName_ == "releaseNotes":
            value_ = child_.text
            value_ = self.gds_parse_string(value_, node, "releaseNotes")
            value_ = self.gds_validate_string(value_, node, "releaseNotes")
            self.releaseNotes = value_
            self.releaseNotes_nsprefix_ = child_.prefix
        elif nodeName_ == "copyright":
            value_ = child_.text
            value_ = self.gds_parse_string(value_, node, "copyright")
            value_ = self.gds_validate_string(value_, node, "copyright")
            self.copyright = value_
            self.copyright_nsprefix_ = child_.prefix
        elif nodeName_ == "language":
            value_ = child_.text
            value_ = self.gds_parse_string(value_, node, "language")
            value_ = self.gds_validate_string(value_, node, "language")
            self.language = value_
            self.language_nsprefix_ = child_.prefix
        elif nodeName_ == "tags":
            value_ = child_.text
            value_ = self.gds_parse_string(value_, node, "tags")
            value_ = self.gds_validate_string(value_, node, "tags")
            self.tags = value_
            self.tags_nsprefix_ = child_.prefix
        elif nodeName_ == "serviceable":
            sval_ = child_.text
            ival_ = self.gds_parse_boolean(sval_, node, "serviceable")
            ival_ = self.gds_validate_boolean(ival_, node, "serviceable")
            self.serviceable = ival_
            self.serviceable_nsprefix_ = child_.prefix
        elif nodeName_ == "icon":
            value_ = child_.text
            value_ = self.gds_parse_string(value_, node, "icon")
            value_ = self.gds_validate_string(value_, node, "icon")
            self.icon = value_
            self.icon_nsprefix_ = child_.prefix
        elif nodeName_ == "repository":
            obj_ = repositoryType.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.repository = obj_
            obj_.original_tagname_ = "repository"
        elif nodeName_ == "license":
            obj_ = licenseType.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.license = obj_
            obj_.original_tagname_ = "license"
        elif nodeName_ == "packageTypes":
            obj_ = packageTypesType.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.packageTypes = obj_
            obj_.original_tagname_ = "packageTypes"
        elif nodeName_ == "dependencies":
            obj_ = dependenciesType.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.dependencies = obj_
            obj_.original_tagname_ = "dependencies"
        elif nodeName_ == "frameworkAssemblies":
            obj_ = frameworkAssembliesType.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.frameworkAssemblies = obj_
            obj_.original_tagname_ = "frameworkAssemblies"
        elif nodeName_ == "frameworkReferences":
            obj_ = frameworkReferencesType.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.frameworkReferences = obj_
            obj_.original_tagname_ = "frameworkReferences"
        elif nodeName_ == "references":
            obj_ = referencesType.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.references = obj_
            obj_.original_tagname_ = "references"
        elif nodeName_ == "contentFiles":
            obj_ = contentFilesType.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.contentFiles = obj_
            obj_.original_tagname_ = "contentFiles"


# end class metadataType


class repositoryType(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "type_": MemberSpec_("type_", "xs:string", 0, 1, {"use": "optional"}),
        "url": MemberSpec_("url", "xs:anyURI", 0, 1, {"use": "optional"}),
        "branch": MemberSpec_("branch", "xs:string", 0, 1, {"use": "optional"}),
        "commit": MemberSpec_("commit", "xs:string", 0, 1, {"use": "optional"}),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_)
    subclass = None
    superclass = None

    def __init__(
        self,
        type_=None,
        url=None,
        branch=None,
        commit=None,
        gds_collector_=None,
        **kwargs_
    ):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        self.type_ = _cast(None, type_)
        self.type__nsprefix_ = None
        self.url = _cast(None, url)
        self.url_nsprefix_ = None
        self.branch = _cast(None, branch)
        self.branch_nsprefix_ = None
        self.commit = _cast(None, commit)
        self.commit_nsprefix_ = None

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(CurrentSubclassModule_, repositoryType)
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if repositoryType.subclass:
            return repositoryType.subclass(*args_, **kwargs_)
        else:
            return repositoryType(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_type(self):
        return self.type_

    def set_type(self, type_):
        self.type_ = type_

    def get_url(self):
        return self.url

    def set_url(self, url):
        self.url = url

    def get_branch(self):
        return self.branch

    def set_branch(self, branch):
        self.branch = branch

    def get_commit(self):
        return self.commit

    def set_commit(self, commit):
        self.commit = commit

    def hasContent_(self):
        if ():
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"',
        name_="repositoryType",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("repositoryType")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "repositoryType":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile, level, already_processed, namespaceprefix_, name_="repositoryType"
        )
        if self.hasContent_():
            outfile.write(">%s" % (eol_,))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="repositoryType",
                pretty_print=pretty_print,
            )
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self,
        outfile,
        level,
        already_processed,
        namespaceprefix_="",
        name_="repositoryType",
    ):
        if self.type_ is not None and "type_" not in already_processed:
            already_processed.add("type_")
            outfile.write(
                " type=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.type_), input_name="type"
                        )
                    ),
                )
            )
        if self.url is not None and "url" not in already_processed:
            already_processed.add("url")
            outfile.write(
                " url=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(quote_attrib(self.url), input_name="url")
                    ),
                )
            )
        if self.branch is not None and "branch" not in already_processed:
            already_processed.add("branch")
            outfile.write(
                " branch=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.branch), input_name="branch"
                        )
                    ),
                )
            )
        if self.commit is not None and "commit" not in already_processed:
            already_processed.add("commit")
            outfile.write(
                " commit=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.commit), input_name="commit"
                        )
                    ),
                )
            )

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"',
        name_="repositoryType",
        fromsubclass_=False,
        pretty_print=True,
    ):
        pass

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.type_, "type_")
        self.gds_check_cardinality_(self.type_, "type_", required=False)
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.url, "url")
        self.gds_check_cardinality_(self.url, "url", required=False)
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.branch, "branch")
        self.gds_check_cardinality_(self.branch, "branch", required=False)
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.commit, "commit")
        self.gds_check_cardinality_(self.commit, "commit", required=False)
        # validate simple type children
        # validate complex type children
        if recursive:
            pass
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        value = find_attr_value_("type", node)
        if value is not None and "type" not in already_processed:
            already_processed.add("type")
            self.type_ = value
        value = find_attr_value_("url", node)
        if value is not None and "url" not in already_processed:
            already_processed.add("url")
            self.url = value
        value = find_attr_value_("branch", node)
        if value is not None and "branch" not in already_processed:
            already_processed.add("branch")
            self.branch = value
        value = find_attr_value_("commit", node)
        if value is not None and "commit" not in already_processed:
            already_processed.add("commit")
            self.commit = value

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        pass


# end class repositoryType


class licenseType(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "type_": MemberSpec_("type_", "xs:string", 0, 0, {"use": "required"}),
        "version": MemberSpec_("version", "xs:string", 0, 1, {"use": "optional"}),
        "valueOf_": MemberSpec_("valueOf_", "xs:string", 0),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_) + ["valueOf_"]
    subclass = None
    superclass = None

    def __init__(
        self, type_=None, version=None, valueOf_=None, gds_collector_=None, **kwargs_
    ):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        self.type_ = _cast(None, type_)
        self.type__nsprefix_ = None
        self.version = _cast(None, version)
        self.version_nsprefix_ = None
        self.valueOf_ = valueOf_

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(CurrentSubclassModule_, licenseType)
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if licenseType.subclass:
            return licenseType.subclass(*args_, **kwargs_)
        else:
            return licenseType(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_type(self):
        return self.type_

    def set_type(self, type_):
        self.type_ = type_

    def get_version(self):
        return self.version

    def set_version(self, version):
        self.version = version

    def get_valueOf_(self):
        return self.valueOf_

    def set_valueOf_(self, valueOf_):
        self.valueOf_ = valueOf_

    def hasContent_(self):
        if 1 if type(self.valueOf_) in [int, float] else self.valueOf_:
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"',
        name_="licenseType",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("licenseType")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "licenseType":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile, level, already_processed, namespaceprefix_, name_="licenseType"
        )
        if self.hasContent_():
            outfile.write(">")
            outfile.write(self.convert_unicode(self.valueOf_))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="licenseType",
                pretty_print=pretty_print,
            )
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self,
        outfile,
        level,
        already_processed,
        namespaceprefix_="",
        name_="licenseType",
    ):
        if self.type_ is not None and "type_" not in already_processed:
            already_processed.add("type_")
            outfile.write(
                " type=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.type_), input_name="type"
                        )
                    ),
                )
            )
        if self.version is not None and "version" not in already_processed:
            already_processed.add("version")
            outfile.write(
                " version=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.version), input_name="version"
                        )
                    ),
                )
            )

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"',
        name_="licenseType",
        fromsubclass_=False,
        pretty_print=True,
    ):
        pass

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.type_, "type_")
        self.gds_check_cardinality_(self.type_, "type_", required=True)
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.version, "version")
        self.gds_check_cardinality_(self.version, "version", required=False)
        # validate simple type children
        # validate complex type children
        if recursive:
            pass
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        self.valueOf_ = get_all_text_(node)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        value = find_attr_value_("type", node)
        if value is not None and "type" not in already_processed:
            already_processed.add("type")
            self.type_ = value
        value = find_attr_value_("version", node)
        if value is not None and "version" not in already_processed:
            already_processed.add("version")
            self.version = value

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        pass


# end class licenseType


class packageTypesType(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "packageType": MemberSpec_(
            "packageType",
            "packageTypeType",
            1,
            1,
            {
                "maxOccurs": "unbounded",
                "minOccurs": "0",
                "name": "packageType",
                "type": "packageTypeType",
            },
            None,
        ),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_)
    subclass = None
    superclass = None

    def __init__(self, packageType=None, gds_collector_=None, **kwargs_):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        if packageType is None:
            self.packageType = []
        else:
            self.packageType = packageType
        self.packageType_nsprefix_ = None

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(CurrentSubclassModule_, packageTypesType)
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if packageTypesType.subclass:
            return packageTypesType.subclass(*args_, **kwargs_)
        else:
            return packageTypesType(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_packageType(self):
        return self.packageType

    def set_packageType(self, packageType):
        self.packageType = packageType

    def add_packageType(self, value):
        self.packageType.append(value)

    def insert_packageType_at(self, index, value):
        self.packageType.insert(index, value)

    def replace_packageType_at(self, index, value):
        self.packageType[index] = value

    def hasContent_(self):
        if self.packageType:
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="packageTypesType",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("packageTypesType")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "packageTypesType":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile,
            level,
            already_processed,
            namespaceprefix_,
            name_="packageTypesType",
        )
        if self.hasContent_():
            outfile.write(">%s" % (eol_,))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="packageTypesType",
                pretty_print=pretty_print,
            )
            showIndent(outfile, level, pretty_print)
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self,
        outfile,
        level,
        already_processed,
        namespaceprefix_="",
        name_="packageTypesType",
    ):
        pass

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="packageTypesType",
        fromsubclass_=False,
        pretty_print=True,
    ):
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        for packageType_ in self.packageType:
            namespaceprefix_ = (
                self.packageType_nsprefix_ + ":"
                if (UseCapturedNS_ and self.packageType_nsprefix_)
                else ""
            )
            packageType_.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="packageType",
                pretty_print=pretty_print,
            )

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        # validate simple type children
        # validate complex type children
        self.gds_check_cardinality_(
            self.packageType, "packageType", min_occurs=0, max_occurs=9999999
        )
        if recursive:
            for item in self.packageType:
                item.validate_(gds_collector, recursive=True)
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        pass

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        if nodeName_ == "packageType":
            obj_ = packageTypeType.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.packageType.append(obj_)
            obj_.original_tagname_ = "packageType"


# end class packageTypesType


class packageTypeType(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "name": MemberSpec_("name", "xs:string", 0, 0, {"use": "required"}),
        "version": MemberSpec_("version", "xs:string", 0, 1, {"use": "optional"}),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_)
    subclass = None
    superclass = None

    def __init__(self, name=None, version=None, gds_collector_=None, **kwargs_):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        self.name = _cast(None, name)
        self.name_nsprefix_ = None
        self.version = _cast(None, version)
        self.version_nsprefix_ = None

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(CurrentSubclassModule_, packageTypeType)
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if packageTypeType.subclass:
            return packageTypeType.subclass(*args_, **kwargs_)
        else:
            return packageTypeType(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def get_version(self):
        return self.version

    def set_version(self, version):
        self.version = version

    def hasContent_(self):
        if ():
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"',
        name_="packageTypeType",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("packageTypeType")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "packageTypeType":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile, level, already_processed, namespaceprefix_, name_="packageTypeType"
        )
        if self.hasContent_():
            outfile.write(">%s" % (eol_,))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="packageTypeType",
                pretty_print=pretty_print,
            )
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self,
        outfile,
        level,
        already_processed,
        namespaceprefix_="",
        name_="packageTypeType",
    ):
        if self.name is not None and "name" not in already_processed:
            already_processed.add("name")
            outfile.write(
                " name=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.name), input_name="name"
                        )
                    ),
                )
            )
        if self.version is not None and "version" not in already_processed:
            already_processed.add("version")
            outfile.write(
                " version=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.version), input_name="version"
                        )
                    ),
                )
            )

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"',
        name_="packageTypeType",
        fromsubclass_=False,
        pretty_print=True,
    ):
        pass

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.name, "name")
        self.gds_check_cardinality_(self.name, "name", required=True)
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.version, "version")
        self.gds_check_cardinality_(self.version, "version", required=False)
        # validate simple type children
        # validate complex type children
        if recursive:
            pass
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        value = find_attr_value_("name", node)
        if value is not None and "name" not in already_processed:
            already_processed.add("name")
            self.name = value
        value = find_attr_value_("version", node)
        if value is not None and "version" not in already_processed:
            already_processed.add("version")
            self.version = value

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        pass


# end class packageTypeType


class dependenciesType(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "dependency": MemberSpec_(
            "dependency",
            "dependency",
            1,
            1,
            {"name": "dependency", "type": "dependency"},
            1,
        ),
        "group": MemberSpec_(
            "group",
            "dependencyGroup",
            1,
            1,
            {"name": "group", "type": "dependencyGroup"},
            1,
        ),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_)
    subclass = None
    superclass = None

    def __init__(self, dependency=None, group=None, gds_collector_=None, **kwargs_):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        if dependency is None:
            self.dependency = []
        else:
            self.dependency = dependency
        self.dependency_nsprefix_ = None
        if group is None:
            self.group = []
        else:
            self.group = group
        self.group_nsprefix_ = None

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(CurrentSubclassModule_, dependenciesType)
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if dependenciesType.subclass:
            return dependenciesType.subclass(*args_, **kwargs_)
        else:
            return dependenciesType(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_dependency(self):
        return self.dependency

    def set_dependency(self, dependency):
        self.dependency = dependency

    def add_dependency(self, value):
        self.dependency.append(value)

    def insert_dependency_at(self, index, value):
        self.dependency.insert(index, value)

    def replace_dependency_at(self, index, value):
        self.dependency[index] = value

    def get_group(self):
        return self.group

    def set_group(self, group):
        self.group = group

    def add_group(self, value):
        self.group.append(value)

    def insert_group_at(self, index, value):
        self.group.insert(index, value)

    def replace_group_at(self, index, value):
        self.group[index] = value

    def hasContent_(self):
        if self.dependency or self.group:
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="dependenciesType",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("dependenciesType")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "dependenciesType":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile,
            level,
            already_processed,
            namespaceprefix_,
            name_="dependenciesType",
        )
        if self.hasContent_():
            outfile.write(">%s" % (eol_,))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="dependenciesType",
                pretty_print=pretty_print,
            )
            showIndent(outfile, level, pretty_print)
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self,
        outfile,
        level,
        already_processed,
        namespaceprefix_="",
        name_="dependenciesType",
    ):
        pass

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="dependenciesType",
        fromsubclass_=False,
        pretty_print=True,
    ):
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        for dependency_ in self.dependency:
            namespaceprefix_ = (
                self.dependency_nsprefix_ + ":"
                if (UseCapturedNS_ and self.dependency_nsprefix_)
                else ""
            )
            dependency_.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="dependency",
                pretty_print=pretty_print,
            )
        for group_ in self.group:
            namespaceprefix_ = (
                self.group_nsprefix_ + ":"
                if (UseCapturedNS_ and self.group_nsprefix_)
                else ""
            )
            group_.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="group",
                pretty_print=pretty_print,
            )

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        # validate simple type children
        # validate complex type children
        # cardinality check omitted for choice item dependency
        # self.gds_check_cardinality_(self.dependency, 'dependency', min_occurs=0, max_occurs=9999999)
        # cardinality check omitted for choice item group
        # self.gds_check_cardinality_(self.group, 'group', min_occurs=0, max_occurs=9999999)
        if recursive:
            for item in self.dependency:
                item.validate_(gds_collector, recursive=True)
            for item in self.group:
                item.validate_(gds_collector, recursive=True)
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        pass

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        if nodeName_ == "dependency":
            obj_ = dependency.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.dependency.append(obj_)
            obj_.original_tagname_ = "dependency"
        elif nodeName_ == "group":
            obj_ = dependencyGroup.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.group.append(obj_)
            obj_.original_tagname_ = "group"


# end class dependenciesType


class frameworkAssembliesType(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "frameworkAssembly": MemberSpec_(
            "frameworkAssembly",
            "frameworkAssemblyType",
            1,
            1,
            {
                "maxOccurs": "unbounded",
                "minOccurs": "0",
                "name": "frameworkAssembly",
                "type": "frameworkAssemblyType",
            },
            None,
        ),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_)
    subclass = None
    superclass = None

    def __init__(self, frameworkAssembly=None, gds_collector_=None, **kwargs_):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        if frameworkAssembly is None:
            self.frameworkAssembly = []
        else:
            self.frameworkAssembly = frameworkAssembly
        self.frameworkAssembly_nsprefix_ = None

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(
                CurrentSubclassModule_, frameworkAssembliesType
            )
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if frameworkAssembliesType.subclass:
            return frameworkAssembliesType.subclass(*args_, **kwargs_)
        else:
            return frameworkAssembliesType(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_frameworkAssembly(self):
        return self.frameworkAssembly

    def set_frameworkAssembly(self, frameworkAssembly):
        self.frameworkAssembly = frameworkAssembly

    def add_frameworkAssembly(self, value):
        self.frameworkAssembly.append(value)

    def insert_frameworkAssembly_at(self, index, value):
        self.frameworkAssembly.insert(index, value)

    def replace_frameworkAssembly_at(self, index, value):
        self.frameworkAssembly[index] = value

    def hasContent_(self):
        if self.frameworkAssembly:
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="frameworkAssembliesType",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("frameworkAssembliesType")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "frameworkAssembliesType":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile,
            level,
            already_processed,
            namespaceprefix_,
            name_="frameworkAssembliesType",
        )
        if self.hasContent_():
            outfile.write(">%s" % (eol_,))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="frameworkAssembliesType",
                pretty_print=pretty_print,
            )
            showIndent(outfile, level, pretty_print)
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self,
        outfile,
        level,
        already_processed,
        namespaceprefix_="",
        name_="frameworkAssembliesType",
    ):
        pass

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="frameworkAssembliesType",
        fromsubclass_=False,
        pretty_print=True,
    ):
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        for frameworkAssembly_ in self.frameworkAssembly:
            namespaceprefix_ = (
                self.frameworkAssembly_nsprefix_ + ":"
                if (UseCapturedNS_ and self.frameworkAssembly_nsprefix_)
                else ""
            )
            frameworkAssembly_.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="frameworkAssembly",
                pretty_print=pretty_print,
            )

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        # validate simple type children
        # validate complex type children
        self.gds_check_cardinality_(
            self.frameworkAssembly,
            "frameworkAssembly",
            min_occurs=0,
            max_occurs=9999999,
        )
        if recursive:
            for item in self.frameworkAssembly:
                item.validate_(gds_collector, recursive=True)
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        pass

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        if nodeName_ == "frameworkAssembly":
            obj_ = frameworkAssemblyType.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.frameworkAssembly.append(obj_)
            obj_.original_tagname_ = "frameworkAssembly"


# end class frameworkAssembliesType


class frameworkAssemblyType(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "assemblyName": MemberSpec_(
            "assemblyName", "xs:string", 0, 0, {"use": "required"}
        ),
        "targetFramework": MemberSpec_(
            "targetFramework", "xs:string", 0, 1, {"use": "optional"}
        ),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_)
    subclass = None
    superclass = None

    def __init__(
        self, assemblyName=None, targetFramework=None, gds_collector_=None, **kwargs_
    ):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        self.assemblyName = _cast(None, assemblyName)
        self.assemblyName_nsprefix_ = None
        self.targetFramework = _cast(None, targetFramework)
        self.targetFramework_nsprefix_ = None

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(
                CurrentSubclassModule_, frameworkAssemblyType
            )
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if frameworkAssemblyType.subclass:
            return frameworkAssemblyType.subclass(*args_, **kwargs_)
        else:
            return frameworkAssemblyType(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_assemblyName(self):
        return self.assemblyName

    def set_assemblyName(self, assemblyName):
        self.assemblyName = assemblyName

    def get_targetFramework(self):
        return self.targetFramework

    def set_targetFramework(self, targetFramework):
        self.targetFramework = targetFramework

    def hasContent_(self):
        if ():
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"',
        name_="frameworkAssemblyType",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("frameworkAssemblyType")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "frameworkAssemblyType":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile,
            level,
            already_processed,
            namespaceprefix_,
            name_="frameworkAssemblyType",
        )
        if self.hasContent_():
            outfile.write(">%s" % (eol_,))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="frameworkAssemblyType",
                pretty_print=pretty_print,
            )
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self,
        outfile,
        level,
        already_processed,
        namespaceprefix_="",
        name_="frameworkAssemblyType",
    ):
        if self.assemblyName is not None and "assemblyName" not in already_processed:
            already_processed.add("assemblyName")
            outfile.write(
                " assemblyName=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.assemblyName), input_name="assemblyName"
                        )
                    ),
                )
            )
        if (
            self.targetFramework is not None
            and "targetFramework" not in already_processed
        ):
            already_processed.add("targetFramework")
            outfile.write(
                " targetFramework=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.targetFramework),
                            input_name="targetFramework",
                        )
                    ),
                )
            )

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"',
        name_="frameworkAssemblyType",
        fromsubclass_=False,
        pretty_print=True,
    ):
        pass

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        self.gds_validate_builtin_ST_(
            self.gds_validate_string, self.assemblyName, "assemblyName"
        )
        self.gds_check_cardinality_(self.assemblyName, "assemblyName", required=True)
        self.gds_validate_builtin_ST_(
            self.gds_validate_string, self.targetFramework, "targetFramework"
        )
        self.gds_check_cardinality_(
            self.targetFramework, "targetFramework", required=False
        )
        # validate simple type children
        # validate complex type children
        if recursive:
            pass
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        value = find_attr_value_("assemblyName", node)
        if value is not None and "assemblyName" not in already_processed:
            already_processed.add("assemblyName")
            self.assemblyName = value
        value = find_attr_value_("targetFramework", node)
        if value is not None and "targetFramework" not in already_processed:
            already_processed.add("targetFramework")
            self.targetFramework = value

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        pass


# end class frameworkAssemblyType


class frameworkReferencesType(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "group": MemberSpec_(
            "group",
            "frameworkReferenceGroup",
            1,
            1,
            {
                "maxOccurs": "unbounded",
                "minOccurs": "0",
                "name": "group",
                "type": "frameworkReferenceGroup",
            },
            None,
        ),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_)
    subclass = None
    superclass = None

    def __init__(self, group=None, gds_collector_=None, **kwargs_):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        if group is None:
            self.group = []
        else:
            self.group = group
        self.group_nsprefix_ = None

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(
                CurrentSubclassModule_, frameworkReferencesType
            )
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if frameworkReferencesType.subclass:
            return frameworkReferencesType.subclass(*args_, **kwargs_)
        else:
            return frameworkReferencesType(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_group(self):
        return self.group

    def set_group(self, group):
        self.group = group

    def add_group(self, value):
        self.group.append(value)

    def insert_group_at(self, index, value):
        self.group.insert(index, value)

    def replace_group_at(self, index, value):
        self.group[index] = value

    def hasContent_(self):
        if self.group:
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="frameworkReferencesType",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("frameworkReferencesType")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "frameworkReferencesType":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile,
            level,
            already_processed,
            namespaceprefix_,
            name_="frameworkReferencesType",
        )
        if self.hasContent_():
            outfile.write(">%s" % (eol_,))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="frameworkReferencesType",
                pretty_print=pretty_print,
            )
            showIndent(outfile, level, pretty_print)
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self,
        outfile,
        level,
        already_processed,
        namespaceprefix_="",
        name_="frameworkReferencesType",
    ):
        pass

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="frameworkReferencesType",
        fromsubclass_=False,
        pretty_print=True,
    ):
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        for group_ in self.group:
            namespaceprefix_ = (
                self.group_nsprefix_ + ":"
                if (UseCapturedNS_ and self.group_nsprefix_)
                else ""
            )
            group_.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="group",
                pretty_print=pretty_print,
            )

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        # validate simple type children
        # validate complex type children
        self.gds_check_cardinality_(
            self.group, "group", min_occurs=0, max_occurs=9999999
        )
        if recursive:
            for item in self.group:
                item.validate_(gds_collector, recursive=True)
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        pass

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        if nodeName_ == "group":
            obj_ = frameworkReferenceGroup.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.group.append(obj_)
            obj_.original_tagname_ = "group"


# end class frameworkReferencesType


class referencesType(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "reference": MemberSpec_(
            "reference",
            "reference",
            1,
            1,
            {"name": "reference", "type": "reference"},
            2,
        ),
        "group": MemberSpec_(
            "group",
            "referenceGroup",
            1,
            1,
            {"name": "group", "type": "referenceGroup"},
            2,
        ),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_)
    subclass = None
    superclass = None

    def __init__(self, reference=None, group=None, gds_collector_=None, **kwargs_):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        if reference is None:
            self.reference = []
        else:
            self.reference = reference
        self.reference_nsprefix_ = None
        if group is None:
            self.group = []
        else:
            self.group = group
        self.group_nsprefix_ = None

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(CurrentSubclassModule_, referencesType)
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if referencesType.subclass:
            return referencesType.subclass(*args_, **kwargs_)
        else:
            return referencesType(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_reference(self):
        return self.reference

    def set_reference(self, reference):
        self.reference = reference

    def add_reference(self, value):
        self.reference.append(value)

    def insert_reference_at(self, index, value):
        self.reference.insert(index, value)

    def replace_reference_at(self, index, value):
        self.reference[index] = value

    def get_group(self):
        return self.group

    def set_group(self, group):
        self.group = group

    def add_group(self, value):
        self.group.append(value)

    def insert_group_at(self, index, value):
        self.group.insert(index, value)

    def replace_group_at(self, index, value):
        self.group[index] = value

    def hasContent_(self):
        if self.reference or self.group:
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="referencesType",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("referencesType")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "referencesType":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile, level, already_processed, namespaceprefix_, name_="referencesType"
        )
        if self.hasContent_():
            outfile.write(">%s" % (eol_,))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="referencesType",
                pretty_print=pretty_print,
            )
            showIndent(outfile, level, pretty_print)
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self,
        outfile,
        level,
        already_processed,
        namespaceprefix_="",
        name_="referencesType",
    ):
        pass

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="referencesType",
        fromsubclass_=False,
        pretty_print=True,
    ):
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        for reference_ in self.reference:
            namespaceprefix_ = (
                self.reference_nsprefix_ + ":"
                if (UseCapturedNS_ and self.reference_nsprefix_)
                else ""
            )
            reference_.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="reference",
                pretty_print=pretty_print,
            )
        for group_ in self.group:
            namespaceprefix_ = (
                self.group_nsprefix_ + ":"
                if (UseCapturedNS_ and self.group_nsprefix_)
                else ""
            )
            group_.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="group",
                pretty_print=pretty_print,
            )

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        # validate simple type children
        # validate complex type children
        # cardinality check omitted for choice item reference
        # self.gds_check_cardinality_(self.reference, 'reference', min_occurs=0, max_occurs=9999999)
        # cardinality check omitted for choice item group
        # self.gds_check_cardinality_(self.group, 'group', min_occurs=0, max_occurs=9999999)
        if recursive:
            for item in self.reference:
                item.validate_(gds_collector, recursive=True)
            for item in self.group:
                item.validate_(gds_collector, recursive=True)
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        pass

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        if nodeName_ == "reference":
            obj_ = reference.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.reference.append(obj_)
            obj_.original_tagname_ = "reference"
        elif nodeName_ == "group":
            obj_ = referenceGroup.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.group.append(obj_)
            obj_.original_tagname_ = "group"


# end class referencesType


class contentFilesType(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "files": MemberSpec_(
            "files",
            "contentFileEntries",
            1,
            1,
            {"name": "files", "type": "contentFileEntries"},
            3,
        ),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_)
    subclass = None
    superclass = None

    def __init__(self, files=None, gds_collector_=None, **kwargs_):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        if files is None:
            self.files = []
        else:
            self.files = files
        self.files_nsprefix_ = None

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(CurrentSubclassModule_, contentFilesType)
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if contentFilesType.subclass:
            return contentFilesType.subclass(*args_, **kwargs_)
        else:
            return contentFilesType(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_files(self):
        return self.files

    def set_files(self, files):
        self.files = files

    def add_files(self, value):
        self.files.append(value)

    def insert_files_at(self, index, value):
        self.files.insert(index, value)

    def replace_files_at(self, index, value):
        self.files[index] = value

    def hasContent_(self):
        if self.files:
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="contentFilesType",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("contentFilesType")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "contentFilesType":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile,
            level,
            already_processed,
            namespaceprefix_,
            name_="contentFilesType",
        )
        if self.hasContent_():
            outfile.write(">%s" % (eol_,))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="contentFilesType",
                pretty_print=pretty_print,
            )
            showIndent(outfile, level, pretty_print)
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self,
        outfile,
        level,
        already_processed,
        namespaceprefix_="",
        name_="contentFilesType",
    ):
        pass

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="contentFilesType",
        fromsubclass_=False,
        pretty_print=True,
    ):
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        for files_ in self.files:
            namespaceprefix_ = (
                self.files_nsprefix_ + ":"
                if (UseCapturedNS_ and self.files_nsprefix_)
                else ""
            )
            files_.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="files",
                pretty_print=pretty_print,
            )

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        # validate simple type children
        # validate complex type children
        # cardinality check omitted for choice item files
        # self.gds_check_cardinality_(self.files, 'files', min_occurs=0, max_occurs=9999999)
        if recursive:
            for item in self.files:
                item.validate_(gds_collector, recursive=True)
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        pass

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        if nodeName_ == "files":
            obj_ = contentFileEntries.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.files.append(obj_)
            obj_.original_tagname_ = "files"


# end class contentFilesType


class filesType(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "file": MemberSpec_(
            "file",
            "fileType",
            1,
            1,
            {
                "maxOccurs": "unbounded",
                "minOccurs": "0",
                "name": "file",
                "type": "fileType",
            },
            None,
        ),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_)
    subclass = None
    superclass = None

    def __init__(self, file=None, gds_collector_=None, **kwargs_):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        if file is None:
            self.file = []
        else:
            self.file = file
        self.file_nsprefix_ = None

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(CurrentSubclassModule_, filesType)
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if filesType.subclass:
            return filesType.subclass(*args_, **kwargs_)
        else:
            return filesType(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_file(self):
        return self.file

    def set_file(self, file):
        self.file = file

    def add_file(self, value):
        self.file.append(value)

    def insert_file_at(self, index, value):
        self.file.insert(index, value)

    def replace_file_at(self, index, value):
        self.file[index] = value

    def hasContent_(self):
        if self.file:
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="filesType",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("filesType")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "filesType":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile, level, already_processed, namespaceprefix_, name_="filesType"
        )
        if self.hasContent_():
            outfile.write(">%s" % (eol_,))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="filesType",
                pretty_print=pretty_print,
            )
            showIndent(outfile, level, pretty_print)
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self, outfile, level, already_processed, namespaceprefix_="", name_="filesType"
    ):
        pass

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" xmlns:None="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd" ',
        name_="filesType",
        fromsubclass_=False,
        pretty_print=True,
    ):
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        for file_ in self.file:
            namespaceprefix_ = (
                self.file_nsprefix_ + ":"
                if (UseCapturedNS_ and self.file_nsprefix_)
                else ""
            )
            file_.export(
                outfile,
                level,
                namespaceprefix_,
                namespacedef_="",
                name_="file",
                pretty_print=pretty_print,
            )

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        # validate simple type children
        # validate complex type children
        self.gds_check_cardinality_(self.file, "file", min_occurs=0, max_occurs=9999999)
        if recursive:
            for item in self.file:
                item.validate_(gds_collector, recursive=True)
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        pass

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        if nodeName_ == "file":
            obj_ = fileType.factory(parent_object_=self)
            obj_.build(child_, gds_collector_=gds_collector_)
            self.file.append(obj_)
            obj_.original_tagname_ = "file"


# end class filesType


class fileType(GeneratedsSuper):
    __hash__ = GeneratedsSuper.__hash__
    member_data_items_ = {
        "src": MemberSpec_("src", "xs:string", 0, 0, {"use": "required"}),
        "target": MemberSpec_("target", "xs:string", 0, 1, {"use": "optional"}),
        "exclude": MemberSpec_("exclude", "xs:string", 0, 1, {"use": "optional"}),
    }
    __slots__ = GeneratedsSuper.gds_subclass_slots(member_data_items_)
    subclass = None
    superclass = None

    def __init__(
        self, src=None, target=None, exclude=None, gds_collector_=None, **kwargs_
    ):
        self.gds_collector_ = gds_collector_
        self.gds_elementtree_node_ = None
        self.original_tagname_ = None
        self.parent_object_ = kwargs_.get("parent_object_")
        self.ns_prefix_ = None
        self.src = _cast(None, src)
        self.src_nsprefix_ = None
        self.target = _cast(None, target)
        self.target_nsprefix_ = None
        self.exclude = _cast(None, exclude)
        self.exclude_nsprefix_ = None

    def factory(*args_, **kwargs_):
        if CurrentSubclassModule_ is not None:
            subclass = getSubclassFromModule_(CurrentSubclassModule_, fileType)
            if subclass is not None:
                return subclass(*args_, **kwargs_)
        if fileType.subclass:
            return fileType.subclass(*args_, **kwargs_)
        else:
            return fileType(*args_, **kwargs_)

    factory = staticmethod(factory)

    def get_ns_prefix_(self):
        return self.ns_prefix_

    def set_ns_prefix_(self, ns_prefix):
        self.ns_prefix_ = ns_prefix

    def get_src(self):
        return self.src

    def set_src(self, src):
        self.src = src

    def get_target(self):
        return self.target

    def set_target(self, target):
        self.target = target

    def get_exclude(self):
        return self.exclude

    def set_exclude(self, exclude):
        self.exclude = exclude

    def hasContent_(self):
        if ():
            return True
        else:
            return False

    def export(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"',
        name_="fileType",
        pretty_print=True,
    ):
        imported_ns_def_ = GenerateDSNamespaceDefs_.get("fileType")
        if imported_ns_def_ is not None:
            namespacedef_ = imported_ns_def_
        if pretty_print:
            eol_ = "\n"
        else:
            eol_ = ""
        if self.original_tagname_ is not None and name_ == "fileType":
            name_ = self.original_tagname_
        if UseCapturedNS_ and self.ns_prefix_:
            namespaceprefix_ = self.ns_prefix_ + ":"
        showIndent(outfile, level, pretty_print)
        outfile.write(
            "<%s%s%s"
            % (
                namespaceprefix_,
                name_,
                namespacedef_ and " " + namespacedef_ or "",
            )
        )
        already_processed = set()
        self.exportAttributes(
            outfile, level, already_processed, namespaceprefix_, name_="fileType"
        )
        if self.hasContent_():
            outfile.write(">%s" % (eol_,))
            self.exportChildren(
                outfile,
                level + 1,
                namespaceprefix_,
                namespacedef_,
                name_="fileType",
                pretty_print=pretty_print,
            )
            outfile.write("</%s%s>%s" % (namespaceprefix_, name_, eol_))
        else:
            outfile.write("/>%s" % (eol_,))

    def exportAttributes(
        self, outfile, level, already_processed, namespaceprefix_="", name_="fileType"
    ):
        if self.src is not None and "src" not in already_processed:
            already_processed.add("src")
            outfile.write(
                " src=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(quote_attrib(self.src), input_name="src")
                    ),
                )
            )
        if self.target is not None and "target" not in already_processed:
            already_processed.add("target")
            outfile.write(
                " target=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.target), input_name="target"
                        )
                    ),
                )
            )
        if self.exclude is not None and "exclude" not in already_processed:
            already_processed.add("exclude")
            outfile.write(
                " exclude=%s"
                % (
                    self.gds_encode(
                        self.gds_format_string(
                            quote_attrib(self.exclude), input_name="exclude"
                        )
                    ),
                )
            )

    def exportChildren(
        self,
        outfile,
        level,
        namespaceprefix_="",
        namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"',
        name_="fileType",
        fromsubclass_=False,
        pretty_print=True,
    ):
        pass

    def validate_(self, gds_collector, recursive=False):
        self.gds_collector_ = gds_collector
        message_count = len(self.gds_collector_.get_messages())
        # validate simple type attributes
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.src, "src")
        self.gds_check_cardinality_(self.src, "src", required=True)
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.target, "target")
        self.gds_check_cardinality_(self.target, "target", required=False)
        self.gds_validate_builtin_ST_(self.gds_validate_string, self.exclude, "exclude")
        self.gds_check_cardinality_(self.exclude, "exclude", required=False)
        # validate simple type children
        # validate complex type children
        if recursive:
            pass
        return message_count == len(self.gds_collector_.get_messages())

    def build(self, node, gds_collector_=None):
        self.gds_collector_ = gds_collector_
        if SaveElementTreeNode:
            self.gds_elementtree_node_ = node
        already_processed = set()
        self.ns_prefix_ = node.prefix
        self.buildAttributes(node, node.attrib, already_processed)
        for child in node:
            nodeName_ = Tag_pattern_.match(child.tag).groups()[-1]
            self.buildChildren(child, node, nodeName_, gds_collector_=gds_collector_)
        return self

    def buildAttributes(self, node, attrs, already_processed):
        value = find_attr_value_("src", node)
        if value is not None and "src" not in already_processed:
            already_processed.add("src")
            self.src = value
        value = find_attr_value_("target", node)
        if value is not None and "target" not in already_processed:
            already_processed.add("target")
            self.target = value
        value = find_attr_value_("exclude", node)
        if value is not None and "exclude" not in already_processed:
            already_processed.add("exclude")
            self.exclude = value

    def buildChildren(
        self, child_, node, nodeName_, fromsubclass_=False, gds_collector_=None
    ):
        pass


# end class fileType


GDSClassesMapping = {}


USAGE_TEXT = """
Usage: python <Parser>.py [ -s ] <in_xml_file>
"""


def usage():
    print(USAGE_TEXT)
    sys.exit(1)


def get_root_tag(node):
    tag = Tag_pattern_.match(node.tag).groups()[-1]
    rootClass = GDSClassesMapping.get(tag)
    if rootClass is None:
        rootClass = globals().get(tag)
    return tag, rootClass


def get_required_ns_prefix_defs(rootNode):
    """Get all name space prefix definitions required in this XML doc.
    Return a dictionary of definitions and a char string of definitions.
    """
    nsmap = {
        prefix: uri
        for node in rootNode.iter()
        for (prefix, uri) in node.nsmap.items()
        if prefix is not None
    }
    namespacedefs = " ".join(
        ['xmlns:{}="{}"'.format(prefix, uri) for prefix, uri in nsmap.items()]
    )
    return nsmap, namespacedefs


def parse(inFileName, silence=False, print_warnings=True):
    global CapturedNsmap_
    gds_collector = GdsCollector_()
    parser = None
    doc = parsexml_(inFileName, parser)
    rootNode = doc.getroot()
    rootTag, rootClass = get_root_tag(rootNode)
    if rootClass is None:
        rootTag = "dependency"
        rootClass = dependency
    rootObj = rootClass.factory()
    rootObj.build(rootNode, gds_collector_=gds_collector)
    CapturedNsmap_, namespacedefs = get_required_ns_prefix_defs(rootNode)
    if not SaveElementTreeNode:
        doc = None
        rootNode = None
    if not silence:
        sys.stdout.write('<?xml version="1.0" ?>\n')
        rootObj.export(
            sys.stdout, 0, name_=rootTag, namespacedef_=namespacedefs, pretty_print=True
        )
    if print_warnings and len(gds_collector.get_messages()) > 0:
        separator = ("-" * 50) + "\n"
        sys.stderr.write(separator)
        sys.stderr.write(
            "----- Warnings -- count: {} -----\n".format(
                len(gds_collector.get_messages()),
            )
        )
        gds_collector.write_messages(sys.stderr)
        sys.stderr.write(separator)
    return rootObj


def parseEtree(
    inFileName, silence=False, print_warnings=True, mapping=None, nsmap=None
):
    parser = None
    doc = parsexml_(inFileName, parser)
    gds_collector = GdsCollector_()
    rootNode = doc.getroot()
    rootTag, rootClass = get_root_tag(rootNode)
    if rootClass is None:
        rootTag = "dependency"
        rootClass = dependency
    rootObj = rootClass.factory()
    rootObj.build(rootNode, gds_collector_=gds_collector)
    # Enable Python to collect the space used by the DOM.
    if mapping is None:
        mapping = {}
    rootElement = rootObj.to_etree(None, name_=rootTag, mapping_=mapping, nsmap_=nsmap)
    reverse_mapping = rootObj.gds_reverse_node_mapping(mapping)
    if not SaveElementTreeNode:
        doc = None
        rootNode = None
    if not silence:
        content = etree_.tostring(
            rootElement, pretty_print=True, xml_declaration=True, encoding="utf-8"
        )
        sys.stdout.write(str(content))
        sys.stdout.write("\n")
    if print_warnings and len(gds_collector.get_messages()) > 0:
        separator = ("-" * 50) + "\n"
        sys.stderr.write(separator)
        sys.stderr.write(
            "----- Warnings -- count: {} -----\n".format(
                len(gds_collector.get_messages()),
            )
        )
        gds_collector.write_messages(sys.stderr)
        sys.stderr.write(separator)
    return rootObj, rootElement, mapping, reverse_mapping


def parseString(inString, silence=False, print_warnings=True):
    """Parse a string, create the object tree, and export it.

    Arguments:
    - inString -- A string.  This XML fragment should not start
      with an XML declaration containing an encoding.
    - silence -- A boolean.  If False, export the object.
    Returns -- The root object in the tree.
    """
    parser = None
    rootNode = parsexmlstring_(inString, parser)
    gds_collector = GdsCollector_()
    rootTag, rootClass = get_root_tag(rootNode)
    if rootClass is None:
        rootTag = "dependency"
        rootClass = dependency
    rootObj = rootClass.factory()
    rootObj.build(rootNode, gds_collector_=gds_collector)
    if not SaveElementTreeNode:
        rootNode = None
    if not silence:
        sys.stdout.write('<?xml version="1.0" ?>\n')
        rootObj.export(
            sys.stdout,
            0,
            name_=rootTag,
            namespacedef_='xmlns:mstns="http://schemas.microsoft.com/packaging/2015/06/nuspec.xsd"',
        )
    if print_warnings and len(gds_collector.get_messages()) > 0:
        separator = ("-" * 50) + "\n"
        sys.stderr.write(separator)
        sys.stderr.write(
            "----- Warnings -- count: {} -----\n".format(
                len(gds_collector.get_messages()),
            )
        )
        gds_collector.write_messages(sys.stderr)
        sys.stderr.write(separator)
    return rootObj


def parseLiteral(inFileName, silence=False, print_warnings=True):
    parser = None
    doc = parsexml_(inFileName, parser)
    gds_collector = GdsCollector_()
    rootNode = doc.getroot()
    rootTag, rootClass = get_root_tag(rootNode)
    if rootClass is None:
        rootTag = "dependency"
        rootClass = dependency
    rootObj = rootClass.factory()
    rootObj.build(rootNode, gds_collector_=gds_collector)
    # Enable Python to collect the space used by the DOM.
    if not SaveElementTreeNode:
        doc = None
        rootNode = None
    if not silence:
        sys.stdout.write("#from _nuspec import *\n\n")
        sys.stdout.write("import _nuspec as model_\n\n")
        sys.stdout.write("rootObj = model_.rootClass(\n")
        rootObj.exportLiteral(sys.stdout, 0, name_=rootTag)
        sys.stdout.write(")\n")
    if print_warnings and len(gds_collector.get_messages()) > 0:
        separator = ("-" * 50) + "\n"
        sys.stderr.write(separator)
        sys.stderr.write(
            "----- Warnings -- count: {} -----\n".format(
                len(gds_collector.get_messages()),
            )
        )
        gds_collector.write_messages(sys.stderr)
        sys.stderr.write(separator)
    return rootObj


def main():
    args = sys.argv[1:]
    if len(args) == 1:
        parse(args[0])
    else:
        usage()


if __name__ == "__main__":
    # import pdb; pdb.set_trace()
    main()

RenameMappings_ = {}

__all__ = [
    "contentFileEntries",
    "contentFilesType",
    "dependenciesType",
    "dependency",
    "dependencyGroup",
    "fileType",
    "filesType",
    "frameworkAssembliesType",
    "frameworkAssemblyType",
    "frameworkReference",
    "frameworkReferenceGroup",
    "frameworkReferencesType",
    "licenseType",
    "metadataType",
    "package",
    "packageTypeType",
    "packageTypesType",
    "reference",
    "referenceGroup",
    "referencesType",
    "repositoryType",
]
