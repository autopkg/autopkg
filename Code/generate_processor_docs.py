#!/usr/bin/env python
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

import os
import optparse
import subprocess
import sys

from autopkglib import get_processor, processor_names


def writefile(stringdata, path):
    '''Writes string data to path.'''
    try:
        fileobject = open(path, mode='w', buffering=1)
        print >> fileobject, stringdata.encode('UTF-8')
        fileobject.close()
    except (OSError, IOError):
        print >> sys.stderr, "Couldn't write to %s" % path


def escape(thing):
    '''Returns string with underscores and asterisks escaped
    for use with Markdown'''
    string = str(thing)
    string = string.replace("_", r"\_")
    string = string.replace("*", r"\*")
    return string


def generate_markdown(dict_data, indent=0):
    '''Returns a string with Markup-style formatting of dict_data'''
    string = ""
    for key, value in dict_data.items():
        if isinstance(value, dict):
            string += " " * indent + "- **%s:**\n" % escape(key)
            string += generate_markdown(value, indent=indent + 4)
        else:
            string += " " * indent + "- **%s:** %s\n" % (
                                                escape(key), escape(value))
    return string
        

def main(argv):
    p = optparse.OptionParser()
    p.add_option("-d", "--directory", metavar="OUTPUTDIRECTORY",
                 default=".",
                 help="Directory path in which to write the output files.")
    options, arguments = p.parse_args()
    
    output_dir = os.path.abspath(os.path.expanduser(options.directory))
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    for processor_name in processor_names():
        processor_class = get_processor(processor_name)
        try:
            description = processor_class.description
        except AttributeError:
            try:
                description = processor_class.__doc__
            except AttributeError:
                description = ""
        try:
            input_vars = processor_class.input_variables
        except AttributeError:
            input_vars = {}
        try:
            output_vars = processor_class.output_variables
        except AttributeError:
            output_vars = {}
        
        filename = "Processor-%s.md" % processor_name
        pathname = os.path.join(output_dir, filename)
        output = "# %s\n" % escape(processor_name)
        output += "\n"
        output += "## Description\n%s\n" % escape(description)
        output += "\n"
        output += "## Input Variables\n"
        output += generate_markdown(input_vars)
        output += "\n"
        output += "## Output Variables\n"
        output += generate_markdown(output_vars)
        output += "\n"
        writefile(output, pathname)
        
    toc_string = "  * Processors\n"
    for processor_name in processor_names():
        page_name = "Processor-%s" % processor_name
        page_name.replace(" ", "-")
        toc_string += "      * [[%s|%s]]\n" % (processor_name, page_name)
    pathname = os.path.join(output_dir, "_processor-toc.md")
    writefile(toc_string, pathname)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
