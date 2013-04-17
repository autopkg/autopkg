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


from Processor import Processor, ProcessorError

from Foundation import NSPredicate

__all__ = ["StopProcessingIf"]


class StopProcessingIf(Processor):
    """Sets a variable to tell AutoPackager to stop processing a recipe if a
       predicate comparison evaluates to true."""
    input_variables = {
        "predicate": {
            "required": True,
            "description": 
                ("NSPredicate-style comparison against an environment key. See "
                 "http://developer.apple.com/library/mac/#documentation/"
                 "Cocoa/Conceptual/Predicates/Articles/pSyntax.html"),
        },
    }
    output_variables = {
        "stop_processing_recipe": {
            "description": "Boolean. Should we stop processing the recipe?",
        },
    }
    description = __doc__
    
    def predicateEvaluatesAsTrue(self, predicate_string):
        '''Evaluates predicate against our environment dictionary'''
        try:
            predicate = NSPredicate.predicateWithFormat_(predicate_string)
        except Exception, err:
            raise ProcessorError(
                "Predicate error for '%s': %s" 
                % (predicate_string, err))

        result = predicate.evaluateWithObject_(self.env)
        self.output("(%s) is %s" % (predicate_string, result))
        return result
        
    def main(self):
        self.env["stop_processing_recipe"] = self.predicateEvaluatesAsTrue(
            self.env["predicate"])


if __name__ == '__main__':
    processor = StopProcessingIf()
    processor.execute_shell()