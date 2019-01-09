#!/usr/bin/env python

from autopkglib import Processor, ProcessorError
import re

__all__ = ["RegexReplace"]


class RegexReplace(Processor):
    '''Replaces all occurrences of a given pattern in the passed string.'''

    input_variables = {
        'replace_pattern': {
            'description': 'Regular expression (Python) to match against string.',
            'required': True,
        },
        'source_string': {
            'description': 'String to use for matching.',
            'required': True,
        },
        'replace_string': {
            'description': 'String to use for replacing matches.',
            'required': True,
        },
        'replace_count': {
            'description': ('Count how many occurrences should be replaced,'
                            'starting from the left most match in "source_string"'),
            'required': False,
            'default': 0
        },
        'result_output_var_name': {
            'description': ('The name of the output variable that is returned '
                            'by the replace. If not specified then a default of '
                            '"replaced_string" will be used.'),
            'required': False,
            'default': 'replaced_string',
        },
    }
    output_variables = {
        'result_output_var_name': {
            'description': (
                'The string with all occurrences of re_pattern replaced with'
                'replace_string. Note the actual name of variable depends on the input '
                'variable "result_output_var_name" or is assigned a default of '
                '"replaced_string."')
        }
    }

    def main(self):
        output_var_name = self.env['result_output_var_name']
        self.output_variables = {}
        self.env[output_var_name] = re.sub(self.env['replace_pattern'], self.env['replace_string'],
                                           self.env['source_string'],
                                           self.env['replace_count'])
        self.output_variables[output_var_name] = {'description': 'String with replacements.'}


if __name__ == '__main__':
    PROCESSOR = RegexReplace()
    PROCESSOR.execute_shell()
