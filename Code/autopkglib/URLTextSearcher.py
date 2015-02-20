#!/usr/bin/python
#
# Copyright 2014 Jesse Peterson
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
"""See docstring for URLTextSearcher class"""

import re
import urllib
import urllib2

from autopkglib import Processor, ProcessorError

__all__ = ["URLTextSearcher"]

class URLTextSearcher(Processor):
    '''Downloads a URL and performs a regular expression match on the text.'''

    input_variables = {
        're_pattern': {
            'description': 'Regular expression (Python) to match against page.',
            'required': True,
        },
        'url': {
            'description': 'URL to download',
            'required': True,
        },
        'result_output_var_name': {
            'description': ('The name of the output variable that is returned '
                            'by the match. If not specified then a default of '
                            '"match" will be used.'),
            'required': False,
            'default': 'match',
        },
        'request_headers': {
            'description': ('Optional dictionary of headers to include with '
                            'the download request.'),
            'required': False,
        },
        're_flags': {
            'description': ('Optional array of strings of Python regular '
                            'expression flags. E.g. IGNORECASE.'),
            'required': False,
        },
        'url_quote': {
            'description': ('If True, causes the matched string to be '
                            'encoded. Equal to urllib.quote(url)'),
            'required': False,
        },
    }
    output_variables = {
        'result_output_var_name': {
            'description': (
                'First matched sub-pattern from input found on the fetched '
                'URL. Note the actual name of variable depends on the input '
                'variable "result_output_var_name" or is assigned a default of '
                '"match."')
        }
    }

    description = __doc__

    def get_url_and_search(self, url, re_pattern, headers=None, flags=None):
        '''Get data from url and search for re_pattern'''
        #pylint: disable=no-self-use
        flag_accumulator = 0
        if flags:
            for flag in flags:
                if flag in re.__dict__:
                    flag_accumulator += re.__dict__[flag]

        re_pattern = re.compile(re_pattern, flags=flag_accumulator)

        try:
            req = urllib2.Request(url, headers=headers)
            file_ref = urllib2.urlopen(req)
            content = file_ref.read()
            file_ref.close()
        except (urllib2.HTTPError, urllib2.URLError, IOError):
            raise ProcessorError('Could not retrieve URL: %s' % url)

        match = re_pattern.search(content)

        if not match:
            raise ProcessorError('No match found on URL: %s' % url)

        # return the last matched group with the dict of named groups
        return (match.group(match.lastindex or 0), match.groupdict(), )

    def main(self):
        output_var_name = self.env['result_output_var_name']

        headers = self.env.get('request_headers', {})

        flags = self.env.get('re_flags', {})

        groupmatch, groupdict = self.get_url_and_search(
            self.env['url'], self.env['re_pattern'], headers, flags)

        # favor a named group over a normal group match
        if output_var_name not in groupdict.keys():
            groupdict[output_var_name] = groupmatch

        self.output_variables = {}
        for key in groupdict.keys():
            self.env[key] = groupdict[key]
            if self.env.get('url_quote', False):
                self.env[key] = urllib.quote(self.env[key], 'http://')
            self.output('Found matching text (%s): %s' % (key, self.env[key], ))
            self.output_variables[key] = {
                'description': 'Matched regular expression group'}

if __name__ == '__main__':
    PROCESSOR = URLTextSearcher()
    PROCESSOR.execute_shell()
