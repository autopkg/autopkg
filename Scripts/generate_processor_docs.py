#!/usr/bin/python
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
"""A utility to export info from autopkg processors and upload it as processor
documentation for the GitHub autopkg wiki"""

import imp
import os
import optparse
import sys

from tempfile import mkdtemp

#pylint: disable=import-error
# Grabbing some functions from the Code directory
CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../Code"))
sys.path.append(CODE_DIR)
from autopkglib import get_processor, processor_names

# Additional helper function(s) from the CLI tool
# Don't make an "autopkgc" file
sys.dont_write_bytecode = True
imp.load_source("autopkg", os.path.join(CODE_DIR, "autopkg"))
from autopkg import run_git
#pylint: enable=import-error


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
            string += (" " * indent + "- **%s:** %s\n"
                       % (escape(key), escape(value)))
    return string


def clone_wiki_dir(clone_dir=None):
    '''Clone the AutoPkg GitHub repo and return the path to where it was
    cloned. The path can be specified with 'clone_dir', otherwise a
    temporary directory will be used.'''

    if not clone_dir:
        outdir = mkdtemp()
    else:
        outdir = clone_dir
    run_git(["clone", "https://github.com/%s/autopkg.wiki", (publish_user, outdir)])
    return os.path.abspath(outdir)


def indent_length(line_str):
    '''Returns the indent length of a given string as an integer.'''
    return len(line_str) - len(line_str.lstrip())


def main(_):
    """Do it all"""
    usage = """%prog VERSION

..where VERSION is the release version for which docs are being generated."""
    parser = optparse.OptionParser(usage=usage)
    parser.description = (
        "Generate GitHub Wiki documentation from the core processors present "
        "in autopkglib. The autopkg.wiki repo is cloned locally, changes are "
        "committed, a diff shown and the user is interactively given the "
        "option to push to the remote.")
    parser.add_option("-d", "--directory", metavar="CLONEDIRECTORY",
                      help=("Directory path in which to clone the repo. If not "
                            "specified, a temporary directory will be used."))
    parser.add_option('--user-repo', default='autopkg/autopkg',
                      help=("Alternate org/user and repo to use for "
                            "the release, useful for testing. Defaults to "
                            "'autopkg/autopkg'."))

    opts = parser.parse_args()[0]
    if not opts.directory:
        parser.print_usage()
        exit()

    publish_user, publish_repo = opts.user_repo.split('/')
    
    # Grab the version for the commit log.
    version = arguments[0]

    print "Cloning AutoPkg wiki.."
    print

    if opts.directory:
        output_dir = clone_wiki_dir(clone_dir=opts.directory)
    else:
        output_dir = clone_wiki_dir()

    print "Cloned to %s." % output_dir
    print
    print


    # Generate markdown pages for each processor attributes
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

    # Generate the Processors section of the Sidebar
    processor_heading = "  * **Processor Reference**"
    toc_string = ""
    toc_string += processor_heading + "\n"
    for processor_name in processor_names():
        page_name = "Processor-%s" % processor_name
        page_name.replace(" ", "-")
        toc_string += "      * [[%s|%s]]\n" % (processor_name, page_name)


    # Merge in the new stuff!
    # - Scrape through the current _Sidebar.md, look for where the existing
    # processors block starts and ends
    # - Copy the lines up to where the Processors section starts
    # - Copy the new Processors TOC
    # - Copy the lines following the Processors section

    sidebar_path = os.path.join(output_dir, "_Sidebar.md")
    with open(sidebar_path, "r") as fdesc:
        current_sidebar_lines = fdesc.read().splitlines()

    # Determine our indent amount
    section_indent = indent_length(processor_heading)

    past_processors_section = False
    for index, line in enumerate(current_sidebar_lines):
        if line == processor_heading:
            past_processors_section = True
            processors_start = index
        if (indent_length(line) <= section_indent) and \
        past_processors_section:
            processors_end = index

    # Build the new sidebar
    new_sidebar = ""
    new_sidebar += "\n".join(current_sidebar_lines[0:processors_start]) + "\n"
    new_sidebar += toc_string
    new_sidebar += "\n".join(current_sidebar_lines[processors_end:]) + "\n"

    with open(sidebar_path, "w") as fdesc:
        fdesc.write(new_sidebar)

    # Git commit everything
    os.chdir(output_dir)
    run_git(["add", "--all"])
    run_git(["commit", "-m", "Updating Wiki docs for release %s" % version])

    # Show the full diff
    print run_git(["log", "-p", "--color", "-1"])

    # Do we accept?
    print "-------------------------------------------------------------------"
    print
    print (
        "Shown above is the commit log for the changes to the wiki markdown. \n"
        "Type 'push' to accept and push the changes to GitHub. The wiki repo \n"
        "local clone can be also inspected at:\n"
        "%s." % output_dir)

    push_commit = raw_input()
    if push_commit == "push":
        run_git(["push", "origin", "master"])

if __name__ == "__main__":
    sys.exit(main(sys.argv))
