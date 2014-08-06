#!/usr/bin/python

import datetime
import re
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
            'description': 'The name of the output variable that is returned by the match. If not specified then a default of "match" will be used.',
            'required': False,
            'default': 'match',
        },
        'request_headers': {
            'description': 'Optional dictionary of headers to include with the download request.',
            'required': False,
        },
        're_flags': {
            'description': 'Optional array of strings of Python regular expression flags. E.g. IGNORECASE.',
            'required': False,
        },
    }
    output_variables = {
        'result_output_var_name': {
            'description': 'First matched sub-pattern from input found on the fetched URL. Note the actual name of variable depends on the input variable "result_output_var_name" or is assigned a default of "match."'
        }
    }

    description = __doc__

    def get_url_and_search(self, url, re_pattern, headers={}, flags={}):
        flag_accumulator = 0
        for f in flags:
            if f in re.__dict__:
                flag_accumulator += re.__dict__[f]

        re_pattern = re.compile(re_pattern, flags=flag_accumulator)

        try:
            r = urllib2.Request(url, headers=headers)
            f = urllib2.urlopen(r)
            content = f.read()
            f.close()
        except BaseException as e:
            raise ProcessorError('Could not retrieve URL: %s' % url)

        m = re_pattern.search(content)

        if not m:
            raise ProcessorError('No match found on URL: %s' % url)

        # return the last matched group with the dict of named groups
        return (m.group(m.lastindex or 0), m.groupdict(), )

    def main(self):
        output_var_name = self.env['result_output_var_name']

        headers = self.env.get('request_headers', {})

        flags = self.env.get('re_flags', {})

        groupmatch, groupdict = self.get_url_and_search(self.env['url'], self.env['re_pattern'], headers, flags)

        # favor a named group over a normal group match
        if output_var_name not in groupdict.keys():
            groupdict[output_var_name] = groupmatch

        self.output_variables = {}
        for k in groupdict.keys():
            self.env[k] = groupdict[k]
            self.output('Found matching text (%s): %s' % (k, self.env[k], ))
            self.output_variables[k] = {'description': 'Matched regular expression group'}

if __name__ == '__main__':
    processor = URLTextSearcher()
    processor.execute_shell()
