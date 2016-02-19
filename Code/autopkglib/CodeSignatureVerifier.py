#!/usr/bin/python
#
# Copyright 2014 Hannes Juutilainen
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
"""See docstring for CodeSignatureVerifier class"""

import os.path
import subprocess
import re

from glob import glob
from distutils.version import StrictVersion
from autopkglib import ProcessorError
from autopkglib.DmgMounter import DmgMounter

__all__ = ["CodeSignatureVerifier"]

RE_AUTHORITY_CODESIGN = re.compile(r'Authority=(?P<authority>.*)\n')
RE_AUTHORITY_PKGUTIL = re.compile(r'\s+[1-9]+\. (?P<authority>.*)\n')


class CodeSignatureVerifier(DmgMounter):
    """Verifies application bundle or installer package signature"""
    input_variables = {
        "DISABLE_CODE_SIGNATURE_VERIFICATION": {
            "required": False,
            "description":
                ("Skip this Processor step altogether. Typically this "
                 "would be invoked using AutoPkg's defaults or via '--key' "
                 "CLI options at the time of the run, rather than being "
                 "defined explicitly within a recipe."),
        },
        "input_path": {
            "required": True,
            "description":
                ("File path to an application bundle (.app) or installer "
                 "package (.pkg or .mpkg). Can point to a globbed path inside "
                 "a .dmg which will be mounted."),
        },
        "expected_authority_names": {
            "required": False,
            "description":
                ("An array of strings defining a list of expected certificate "
                 "authority names. Complete list of the certificate name chain "
                 "is required and it needs to be in the correct order. These "
                 "can be determined by running: "
                 "\n\t$ codesign --display -vvvv <path_to_app>"
                 "\n\tor"
                 "\n\t$ pkgutil --check-signature <path_to_pkg>"),
        },
        "requirement": {
            "required": False,
            "description":
                ("A requirement string to pass to codesign. "
                 "This should always be set to the original designated "
                 "requirement of the application and can be determined "
                 "by running:"
                 "\n\t$ codesign --display -r- <path_to_app>"),
        },
    }
    output_variables = {
    }

    description = __doc__

    def codesign_get_authority_names(self, path):
        """
        Runs 'codesign --display -vvvv <path>' and returns a list of
        found certificate authority names.
        """
        #pylint: disable=no-self-use
        process = ["/usr/bin/codesign",
                   "--display",
                   "-vvvv",
                   path]

        proc = subprocess.Popen(process,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        codesign_details = proc.communicate()[1]

        authority_name_chain = []
        for match in re.finditer(RE_AUTHORITY_CODESIGN, codesign_details):
            authority_name_chain.append(match.group('authority'))
        return authority_name_chain

    def codesign_verify(self, path, test_requirement=None):
        """
        Runs 'codesign --verify --verbose <path>'. Returns True if
        codesign exited with 0 and False otherwise.
        """

        process = ["/usr/bin/codesign",
                   "--verify",
                   "--verbose=1"]

        # Only use --deep option in OS X 10.9.5 or later
        darwin_version = os.uname()[2]
        if StrictVersion(darwin_version) >= StrictVersion('13.4.0'):
            process.append("--deep")

        if test_requirement:
            process.append("-R=%s" % test_requirement)

        process.append(path)

        proc = subprocess.Popen(process,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (output, error) = proc.communicate()

        # Log all output. codesign seems to output only
        # to stderr but check the stdout too
        if error:
            for line in error.splitlines():
                self.output("%s" % line)
        if output:
            for line in output.splitlines():
                self.output("%s" % line)

        # Return True if codesign exited with 0
        return proc.returncode == 0

    def pkgutil_check_signature(self, path):
        """
        Runs 'pkgutil --check-signature <path>'. Returns a tuple with boolean
        pkgutil exit status and a list of found certificate authority names
        """
        process = ["/usr/sbin/pkgutil",
                   "--check-signature",
                   path]
        proc = subprocess.Popen(process,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (output, error) = proc.communicate()

        # Log everything
        if output:
            for line in output.splitlines():
                self.output("%s" % line)
        if error:
            for line in error.splitlines():
                self.output("%s" % line)

        # Parse the output for certificate authority names
        authority_name_chain = []
        for match in re.finditer(RE_AUTHORITY_PKGUTIL, output):
            authority_name_chain.append(match.group('authority'))

        # Return a tuple with boolean status and
        # a list with certificate authority names
        return proc.returncode == 0, authority_name_chain

    def process_app_bundle(self, path):
        '''Verifies the signature for an application bundle'''
        self.output("Verifying application bundle signature...")
        # The first step is to run 'codesign --verify <path>'
        requirement = self.env.get('requirement', None)
        if self.codesign_verify(path, requirement):
            self.output("Signature is valid")
        else:
            raise ProcessorError(
                "Code signature verification failed. Note that "
                "all verifications can be disabled by setting the variable "
                "DISABLE_CODE_SIGNATURE_VERIFICATION to a non-empty value.")

        if self.env.get('expected_authority_names', None):
            authority_names = self.codesign_get_authority_names(path)
            expected_authority_names = self.env['expected_authority_names']
            if authority_names != expected_authority_names:
                self.output("Mismatch in authority names")
                self.output(
                    "Expected: %s" % ' -> '.join(expected_authority_names))
                self.output("Found:    %s" % ' -> '.join(authority_names))
                raise ProcessorError(
                    "Mismatch in authority names. Note that all "
                    "verification can be disabled by setting the variable "
                    "DISABLE_CODE_SIGNATURE_VERIFICATION to a non-empty value.")
            else:
                self.output("Authority name chain is valid")

    def process_installer_package(self, path):
        '''Verifies the signature for an installer pkg'''
        self.output("Verifying installer package signature...")
        # The first step is to run 'pkgutil --check-signature <path>'
        pkgutil_succeeded, authority_names = self.pkgutil_check_signature(path)

        if pkgutil_succeeded:
            self.output("Signature is valid")
        else:
            raise ProcessorError(
                "Code signature verification failed. Note that all "
                "verification can be disabled by setting the variable "
                "DISABLE_CODE_SIGNATURE_VERIFICATION to a non-empty value.")

        if self.env.get('expected_authority_names', None):
            expected_authority_names = self.env['expected_authority_names']
            if authority_names != expected_authority_names:
                self.output("Mismatch in authority names")
                self.output(
                    "Expected: %s" % ' -> '.join(expected_authority_names))
                self.output("Found:    %s" % ' -> '.join(authority_names))
                raise ProcessorError(
                    "Mismatch in authority names. Note that all "
                    "verification can be disabled by setting the variable "
                    "DISABLE_CODE_SIGNATURE_VERIFICATION to a non-empty value.")
            else:
                self.output("Authority name chain is valid")

    def main(self):
        if self.env.get('DISABLE_CODE_SIGNATURE_VERIFICATION'):
            self.output("Code signature verification disabled for this recipe "
                        "run.")
            return
        # Check if we're trying to read something inside a dmg.
        (dmg_path, dmg, dmg_source_path) = self.parsePathForDMG(
            self.env['input_path'])
        try:
            if dmg:
                # Mount dmg and copy path inside.
                mount_point = self.mount(dmg_path)
                globbed_paths = glob(os.path.join(mount_point, dmg_source_path))
                if len(globbed_paths) > 0:
                    input_path = globbed_paths[0]
                else:
                    self.output(
                        "Invalid input path: %s" % self.env['input_path'])
                    raise ProcessorError("Invalid input path")
            else:
                # just use the given path
                input_path = self.env['input_path']

            # Get current Darwin kernel version
            darwin_version = os.uname()[2]

            # Currently we support only .app, .pkg or .mpkg types
            file_extension = os.path.splitext(input_path)[1]
            if file_extension == ".app":
                self.process_app_bundle(input_path)
            elif file_extension in [".pkg", ".mpkg"]:
                # Check the kernel version to make sure we're running on
                # Snow Leopard:
                # Mac OS X 10.6.8 == Darwin Kernel Version 10.8.0
                if StrictVersion(darwin_version) < StrictVersion('11.0'):
                    self.output("Warning: Installer package signature "
                                "verification not supported on Mac OS X 10.6")
                else:
                    self.process_installer_package(input_path)
            else:
                raise ProcessorError("Unsupported file type")

        finally:
            if dmg:
                self.unmount(dmg_path)


if __name__ == '__main__':
    PROCESSOR = CodeSignatureVerifier()
    PROCESSOR.execute_shell()
