#!/usr/bin/env python
#
# Copyright 2013 Timothy Sutton
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


from subprocess import Popen, PIPE
from autopkglib import Processor, ProcessorError

DEFAULT_BRANCH = "release"
BASE_URL = "http://api.textmate.org/downloads/"

# Another interesting URL that returns an ASCII-style plist used by
# the app's own SU mechanism, but the download URL it returns is an
# https URL that urllib/2 cannot handshake with:
# http://api.textmate.org/releases/

__all__ = ["TextMateURLProvider"]


class TextMateURLProvider(Processor):
    """Provides a download URL for a TextMate 2 update.
    TextMate 1 is not supported."""
    input_variables = {
        "branch": {
            "required": False,
            "description": ("The update branch. One of 'release', 'beta', or 'nightly'. "
                            "In the TM GUI, 'Normal' corresponds to 'release', 'Nightly' = "
                            "'beta'. Defaults to %s" % DEFAULT_BRANCH)
        }
    }
    output_variables = {
        "url": {
            "description": "URL to the latest TextMate 2 tbz.",
        }
    }
    description = __doc__

    def main(self):
        url = BASE_URL + self.env.get("branch", DEFAULT_BRANCH)
        # Using curl to fetch Location header(s) because urllib/2
        # cannot verify the SSL cert and the server won't accept this
        # TextMate's SSL hostnames don't seem to match the SSL cert name,
        # depending on the CA bundle being used. This can be verified
        # using the 'requests' Python library.
        p = Popen(['/usr/bin/curl', '-ILs', url], stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        parsed_url = None
        if err:
            print err
            raise ProcessorError("curl returned an error: %s" % out)
        for line in out.splitlines():
            if line.startswith("Location"):
                parsed_url = line.split()[1]
        if not parsed_url:
            raise ProcessorError("curl didn't find a resolved 'Location' header "
                                "we can use. Full curl output:\n %s"
                                % "\n".join(out.splitlines()))

        self.env["url"] = parsed_url

if __name__ == "__main__":
    processor = TextMateURLProvider()
    processor.execute_shell()
