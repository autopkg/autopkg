#!/usr/bin/env python

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
            'description': 'The name of the output variable that is returned by the match. Optional.',
            'required': False,
        },
        'request_headers': {
            'description': 'Optional dictionary of headers to include with the download request.',
            'required': False,
        },
    }
    output_variables = {
        'url': {
            'description': 'First matched sub-pattern from input found on the fetched page'
        }
    }

    description = __doc__

    def get_url_and_search(self, url, re_pattern, headers={}):
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

        return (m.group(0), m.groupdict(), )

    def main(self):
        re_pattern = re.compile(self.env['re_pattern'])

        output_var_name = None

        if 'result_output_var_name' in self.env and self.env['result_output_var_name']:
            output_var_name = self.env['result_output_var_name']
        else:
            output_var_name = 'match'

        headers = {}
        if "request_headers" in self.env:
            headers = self.env["request_headers"]

        group0, groupdict = self.get_url_and_search(self.env['url'], re_pattern, headers)

        if output_var_name not in groupdict.keys():
            groupdict[output_var_name] = group0

        for k in groupdict.keys():
            self.env[k] = groupdict[k]
            self.output('Found matching text (%s): %s' % (k, self.env[k], ))

if __name__ == '__main__':
    processor = URLTextSearcher()
    processor.execute_shell()
