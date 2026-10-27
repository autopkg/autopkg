#!/usr/local/autopkg/python
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
"""Console-script entry point used by wheel installs.

The CLI lives in Code/autopkg, a script with no .py extension, so it can't be
imported. The wheel build copies it into this package (see setup.py) and
main() runs it the same way `python autopkg` does, so the script stays the
one copy of the CLI that the macOS pkg, install.sh and autopkg.ps1 also run.
"""

import os
import runpy


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = (
        # wheel install: copied in by setup.py
        os.path.join(here, "autopkg"),
        # source checkout or editable install: Code/autopkg
        os.path.join(here, os.pardir, "autopkg"),
    )
    for script in candidates:
        if os.path.isfile(script):
            runpy.run_path(script, run_name="__main__")
            return
    raise SystemExit(f"autopkg: CLI script not found in {', '.join(candidates)}")
