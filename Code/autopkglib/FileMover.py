#!/usr/bin/python

from os import rename
from autopkglib import Processor, ProcessorError

__all__ = ["FileMover"]

class FileMover(Processor):
    '''Moves/renames a file'''

    input_variables = {
        'source': {
            'description': 'Source file',
            'required': True,
        },
        'target': {
            'description': 'Target file',
            'required': True,
        },
    }
    output_variables = {
    }

    description = __doc__

    def main(self):
        rename(self.env['source'], self.env['target'])
        self.output('File %s moved to %s' % (self.env['source'], self.env['target']))

if __name__ == '__main__':
    processor = FileMover()
    processor.execute_shell()
