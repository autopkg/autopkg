#!/usr/local/autopkg/python
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
"""Place-holder processor that autopkg uses to mark the end of the check
phase."""

from autopkglib import Processor, ProcessorError, log

try:
    from Foundation import NSPredicate
except ImportError:
    log("WARNING: Failed 'from Foundation import NSPredicate' in " + __name__)

__all__ = ["EndOfCheckPhase"]


class EndOfCheckPhase(Processor):
    """This processor performs no action, but serves as a marker to signal
    where AutoPkg should stop when the -c/--check options are used."""

    input_variables = {}
    output_variables = {"stop_processing_recipe": {}}
    description = __doc__

    def main(self):
        try:
            predicate = NSPredicate.predicateWithFormat_("download_changed == False")
        except Exception as err:
            raise ProcessorError(
                f"Predicate error for '{predicate_string}': {err}"
            ) from err

        self.env["stop_processing_recipe"] = predicate.evaluateWithObject_(self.env)


if __name__ == "__main__":
    PROCESSOR = EndOfCheckPhase()
    PROCESSOR.execute_shell()
