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
            'description': 'The name of the output variable that is returned by the match',
            'required': False,
        },
    }
    output_variables = {
        'url': {
            'description': 'First matched sub-pattern from input found on the fetched page'
        }
    }

    description = __doc__

    def get_url(self, url, re_pattern):
        try:
            f = urllib2.urlopen(url)
            content = f.read()
            f.close()
        except BaseException as e:
            raise ProcessorError('Could not retrieve URL: %s' % url)

        m = re_pattern.search(content)

        if m:
            return m.group(1)

        raise ProcessorError('No matched files')

    def main(self):
        re_pattern = re.compile(self.env['re_pattern'])

        if 'result_output_var_name' in self.env and self.env['result_output_var_name']:
            output_var_name = self.env['result_output_var_name']
        else:
            output_var_name = 'url'

        self.env[output_var_name] = self.get_url(self.env['url'], re_pattern)
        self.output('Found matching text (%s): %s' % (output_var_name, self.env[output_var_name], ))

if __name__ == '__main__':
    processor = URLTextSearcher()
    processor.execute_shell()
