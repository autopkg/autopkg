#!/usr/bin/env python

import os
import shutil
import subprocess

from autopkglib import Processor, ProcessorError
from Foundation import NSData, NSPropertyListSerialization, NSPropertyListMutableContainers

__all__ = ["EnvPrinter"]

class EnvPrinter(Processor):

    input_variables = {
    }
    output_variables = {
    }

    description = "Prints env array"

    def main(self):
        print self.env
        