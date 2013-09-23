#!/usr/bin/env python
#
# Copyright 2013 Jesse Peterson
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



from glob import glob
from autopkglib import Processor, ProcessorError

__all__ = ["FileFinder"]

class FileFinder(Processor):
	'''Finds a filename for use in other Processors.

	Currently only supports	glob filename patterns.
	'''

	input_variables = {
		'glob_pattern': {
			'description': 'Shell glob pattern to match files by',
			'required': True,
		},
	}
	output_variables = {
		'found_filename': {
			'description': 'Found filename',
		}
	}

	description = __doc__

	def globfind(self, pattern):
		'''If multiple files are found the last alphanumerically sorted found file is returned'''

		glob_matches = glob(pattern)

		if len(glob_matches) < 1:
			raise ProcessorError('No matching filename found')

		glob_matches.sort()

		return glob_matches[-1]

	def main(self):
		pattern = self.env.get('glob_pattern')

		self.env['found_filename'] = self.globfind(pattern)

		self.output('Found file match: %s' % self.env['found_filename'])

if __name__ == '__main__':
	processor = FileFinder()
	processor.execute_shell()
