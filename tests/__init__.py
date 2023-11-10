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

import importlib
from types import ModuleType
from typing import Type, Union

from autopkglib import Processor


def get_processor_module(
    processor: Union[str, Type[Processor]], package_name: str = "autopkglib"
) -> ModuleType:
    """Get the module for a processor, which may be passed as a string or class object.

    Typically used for patching module scoped functions for unit testing like so:
        proc_module = get_processor_module("Unarchiver")
        patcher = unittest.mock.patch.object(proc_module, "is_mac", return_value=False)

    Necessary because `autopkglib` contains code that makes it impossible to import a
    processor *module* without significant effort and/or modifications to some of the
    basic machinery of `autopkglib`. This function wraps simple `importlib` machinery.
    """
    if isinstance(processor, str):
        module_name: str = ".".join([package_name, processor])
    else:
        module_name = processor.__module__
    # The default value for `package_name` relies on the convention in
    # `autopkglib.import_processors` that expects module name to equal processor name.
    return importlib.import_module(module_name)
