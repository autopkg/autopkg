from __future__ import print_function

# We're effectively using this package as module
try:
    from FoundationPlist import *
except:
    print(
        "WARNING: using 'from plistlib import *' instead of 'from "
        "FoundationPlist import *' in " + __name__
    )
