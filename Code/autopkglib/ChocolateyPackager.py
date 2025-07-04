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
"""See docstring for ChocolateyPackager class"""

import os
import subprocess
from shutil import copy2, rmtree
from tempfile import mkdtemp
from typing import Any, Dict, List, Optional, Union

from autopkglib import Processor, ProcessorError
from nuget import (
    CHOCO_CHECKSUM_TYPES,
    CHOCO_FILE_TYPES,
    ChocolateyInstallGenerator,
    NuspecDependency,
    NuspecGenerator,
)

__all__ = ["ChocolateyPackager"]


class VariableSentinel:
    pass


DefaultValue = VariableSentinel()


class ChocolateyPackager(Processor):
    """
    Run `choco.exe` to build a single Nuget package.
    """

    description: str = __doc__

    # Input variables for Nuspec creation. These correspond to the schema referenced
    # `Scripts/regenerate_nuspec_ds.py`.
    nuspec_variables = {
        "id": {
            "required": True,
            "description": (
                "The unique ID of the package. "
                "Recommended to be lower case, with '-' for space. "
                "E.g., 'Google Chrome' -> google-chrome"
            ),
        },
        "version": {
            "required": True,
            "description": (
                "The version of the package. "
                "Please see the technical reference for more details on "
                "acceptable versions: "
                "https://docs.microsoft.com/en-us/nuget/concepts/package-versioning"
            ),
        },
        "title": {
            "required": True,
            "description": ("This is user-friendly package name."),
        },
        "authors": {
            "required": True,
            "description": ("The authors of the software (and package)."),
        },
        "description": {
            "required": True,
            "description": (
                "A long form description of what the package does, what it "
                "installs, changelogs, etc."
            ),
        },
        "owners": {"required": False, "description": ("The owners of the package.")},
        "licenseUrl": {
            "required": False,
            "description": ("A URL to the license of the software being packaged."),
        },
        "projectUrl": {
            "required": False,
            "description": ("A URL to the project of the software being packaged."),
        },
        "iconUrl": {
            "required": False,
            "description": (
                "A URL to the favicon of the software being packaged. "
                "This is what gets displayed in GUIs if they render available "
                "packages."
            ),
        },
        "summary": {
            "required": False,
            "description": ("A short description of what the package does."),
        },
        "releaseNotes": {
            "required": False,
            "description": ("Notes on this particular release of the package."),
        },
        "copyright": {"required": False, "description": ("Copyright information.")},
        "tags": {
            "required": False,
            "description": ("Tagging information to aid searches. Space separated."),
        },
        "icon": {
            "required": False,
            "description": (
                "Not sure, but probably something to do with the icon of the "
                "package."
            ),
        },
        "license": {"required": False, "description": ("Licensing information.")},
        "dependencies": {
            "required": False,
            "description": (
                "Dependencies for this package. Must be a list of dictionaries, each "
                "with `id` and `version` keys. Where `id` is the chocolatey package id."
            ),
        },
        "contentFiles": {
            "required": False,
            "description": ("Lists the file contents for this package. "),
        },
    }

    # Input variables for `chocolateyInstall.ps1`.
    # See `ChocolateyInstallGenerator` for more details.
    chocolateyinstall_variables = {
        "installer_path": {
            "required": False,
            "description": (
                "The local path to the installation file.\n"
                "        This should either be an MSI or an EXE that can perform the "
                "application's setup. Defaults to the `pathname` variable, e.g. as set "
                "by `URLDownloader`. Note that using this will **copy** the installer "
                "into the nupkg. Which is problematic if the installer is over 200MB "
                "give or take, according to the Chocolatey documentation.\n"
                "        Either this variable **or** `installer_url` MUST be provided."
            ),
            "default": DefaultValue,
        },
        "installer_url": {
            "required": False,
            "description": (
                "A URL (HTTPS, UNC, ...) to the installation file.\n"
                "        Chocolatey will **download** this file and compare with its "
                "embedded checksum at package installation time.\n"
                "        Either this variable **or** `installer_path` MUST be provided."
            ),
        },
        "installer_checksum": {
            "required": False,
            "description": (
                "Hex encoded checksum of the installation file.\n"
                "        NOTE: The checksum provided here IS NOT checked when using "
                "`installer_path`!"
            ),
        },
        "installer_checksum_type": {
            "required": False,
            "description": (
                "One of the valid checksum types: " f"{', '.join(CHOCO_CHECKSUM_TYPES)}"
            ),
            "default": "sha512",
        },
        "installer_type": {
            "required": True,
            "description": (f"The type of installer: {', '.join(CHOCO_FILE_TYPES)}"),
        },
        "installer_args": {
            "required": False,
            "description": (
                "List of arguments to pass to the installer. "
                "If the type is **not** `msi`, then arguments are virtually always "
                "necessary to make the installer operate silently. For MSI installers, "
                "the processor uses the standard silencing arguments **unless** this "
                "variable is provided."
            ),
        },
        "output_directory": {
            "required": False,
            "description": (
                "Where the final nupkg output will be placed. "
                "Defaults to RECIPE_CACHE_DIR/nupkgs"
            ),
        },
    }

    input_variables = {
        "KEEP_BUILD_DIRECTORY": {
            "required": False,
            "description": (
                "Usually the temporary directory used for building the package is "
                "destroyed after this processor runs. However, for testing and "
                "development, it is often useful to inspect the intermediate outputs."
            ),
            "default": False,
        },
        "chocoexe_path": {
            "required": False,
            "description": (
                "The absolute path to `choco.exe` This is not usually needed."
            ),
            "default": r"C:\ProgramData\chocolatey\bin\choco.exe",
        },
        "additional_install_actions": {
            "required": False,
            "description": (
                "Additional powershell code to include after the generated "
                "portion of `chocolateyInstall.ps1`. The code provided will run "
                "**after** the generated `Install-Chocolatey*` cmdlet has executed. "
                "You may rely on the following variables to be defined when this code "
                "runs: `$toolsDir`, and `$packageArgs`. These follow their usual "
                "convention as shown in examples for building chocolatey packages. "
            ),
        },
        # See above for descriptions of the variables described by these.
        **chocolateyinstall_variables,
        **nuspec_variables,
    }

    output_variables = {
        "nuget_package_path": {"description": "Path to the generated nuget package."},
        "choco_build_directory": {
            "description": (
                "Path to where chocolatey build files were created.\n"
                "Path will only exist on completion if KEEP_BUILD_DIRECTORY is set."
            )
        },
        "chocolatey_packager_summary_result": {"description": "Summary of packaging."},
    }

    def _check_enum_var(self, varname: str, enum_values: List[str]) -> None:
        value = self.env.get(varname)
        if value not in enum_values:
            raise ValueError(
                f"Variable '{varname}' value '{value}' "
                f" not one of: {','.join(enum_values)}"
            )

    def _ensure_path_var(self, varname: str, default_var: Optional[str] = None) -> str:
        default_path: Optional[str] = None
        default_msg: str = ""
        if default_var is not None:
            default_path = self.env.get(default_var)
            default_msg = f" or {default_var}"

        path = self.env.get(varname, default_path)
        if path is None:
            raise ProcessorError(
                f"{self.__class__.__name__} requires a {varname}{default_msg} variable"
            )
        path = os.path.abspath(path)
        if not os.path.exists(path):
            raise ProcessorError(f"{varname} not found at: {path}")
        else:
            self.env[varname] = path
        return path

    def _build_path(self, build_dir: str, *additional_parts: str) -> str:
        r"""Return absolute path of `build_dir` and any additional path parts.
        Example:
        ```
        self._build_path(build_dir, "tools/chocolateyInstall.ps1")`
        # C:\choco_builds\build_xy2820.44\tools\chocolateyInstall.ps1
        ```
        """
        return os.path.abspath(os.path.join(build_dir, *additional_parts))

    @property
    def idver(self):
        return f"{self.env['id']}.{self.env['version']}"

    def _nuspec_path(self, build_dir: str) -> str:
        return self._build_path(build_dir, f"{self.env['id']}.nuspec")

    def _chocolateyinstall_path(self, build_dir: str) -> str:
        return self._build_path(build_dir, "tools", "chocolateyInstall.ps1")

    def nuspec_definition(self) -> NuspecGenerator:
        def_args: Dict[str, Any] = {}
        for k in self.nuspec_variables.keys():
            if k not in self.env:
                continue
            if k == "dependencies":
                def_args[k] = list(
                    map(lambda dep_args: NuspecDependency(**dep_args), self.env[k])
                )
            else:
                def_args[k] = self.env[k]
        return NuspecGenerator(**def_args)

    def chocolateyinstall_ps1(self) -> ChocolateyInstallGenerator:
        computed_args: List[str] = []
        if "installer_args" in self.env:
            installer_args = self.env["installer_args"]
            if isinstance(installer_args, List):
                computed_args = installer_args
            elif isinstance(installer_args, str):
                computed_args = [installer_args]
            else:
                raise
        elif self.env["installer_type"] == "msi":
            computed_args = [
                "/qn",  # No UI
                "/norestart",
                "/l*v",  # Log verbose everything
                "MsiInstall.log",
                # TODO: Determine if/how to expose these property arguments:
                # ALLUSERS=1 DISABLEDESKTOPSHORTCUT=1 ADDDESKTOPICON=0 ADDSTARTMENU=0
            ]

        installer_kwargs = {}
        if "installer_url" in self.env:
            installer_kwargs["url"] = self.env["installer_url"]
            installer_kwargs["installer_checksum"] = self.env["installer_checksum"]
            installer_kwargs["installer_checksum_type"] = self.env[
                "installer_checksum_type"
            ]
        else:
            installer_kwargs["file"] = self.env["installer_path"]

        assert len(installer_kwargs) > 0, "Processor experienced a fatal logic error."

        return ChocolateyInstallGenerator(
            packageName=self.env["id"],
            fileType=self.env["installer_type"],
            silentArgs=" ".join(computed_args),
            **installer_kwargs,
        )

    def _write_chocolatey_install(self, build_dir: str) -> None:
        install_gen = self.chocolateyinstall_ps1()
        with open(self._chocolateyinstall_path(build_dir), "w") as install_fh:
            install_gen.render_to(install_fh)
            install_fh.write(self.env.get("additional_install_actions", ""))

    def write_build_configs(self, build_dir: str) -> None:
        """Given a directory, writes the necessary files to run `choco.exe pack`"""
        tools_dir = self._build_path(build_dir, "tools")
        os.mkdir(tools_dir)
        nuspec_gen = self.nuspec_definition()

        with open(self._nuspec_path(build_dir), "w") as nuspec_fh:
            nuspec_gen.render_to(nuspec_fh)

        self._write_chocolatey_install(build_dir)

        if self.env["installer_path"] != DefaultValue:
            copy2(self.env["installer_path"], tools_dir)
            installer_file = os.path.basename(self.env["installer_path"])
            # Touch a .ignore file next to the installer. This causes chocolatey to
            # include the file in the Nupkg, but not create a "shim" for it when the
            # package is installed.
            open(os.path.join(tools_dir, f"{installer_file}.ignore"), "w").close()

    def choco_pack(self, build_dir: str, output_dir: str) -> str:
        """Run `choco.exe pack` and return absolute path to built Nupkg, or raise
        an exception."""
        self.log(f"Building package {self.env['id']} version {self.env['version']}")
        nuspec_filename = self._nuspec_path(build_dir)
        command = [
            self.env["chocoexe_path"],
            "pack",
            nuspec_filename,
            f"--output-directory={output_dir}",
            f"--log-file={os.path.join(output_dir, f'{self.idver}.log')}",
        ]
        self.log(f"Running: {' '.join(command)}", 1)
        proc = subprocess.Popen(
            command,
            stdin=None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        (output, _) = proc.communicate()
        self.log(output.splitlines(), 1)
        if proc.returncode != 0:
            raise ProcessorError(
                f"Command: ``{' '.join(command)}`` returned: {proc.returncode}",
                proc.returncode,
            )
        expected_nupkg_path = os.path.abspath(
            os.path.join(output_dir, f"{self.idver}.nupkg")
        )
        os.stat(expected_nupkg_path)  # Test for package existence, or raise.
        return expected_nupkg_path

    def log(self, msgs: Union[List[str], str], verbose_level: int = 0) -> None:
        if isinstance(msgs, List):
            for m in msgs:
                self.output(m, verbose_level)
            return
        self.output(msgs, verbose_level)

    def main(self):
        # Validate arguments, apply dynamic defaults as needed.
        self._ensure_path_var("chocoexe_path")
        if (
            self.env.get("installer_url") is not None
            and self.env["installer_path"] != DefaultValue
        ):
            raise ProcessorError(
                "Variables `installer_url`, `installer_path` conflict. Provide one."
            )

        if (
            self.env.get("installer_url") is None
            and self.env["installer_path"] == DefaultValue
        ):
            # Delete this since we know its value, but would like a useful
            # error message from `_ensure_path_var`.
            del self.env["installer_path"]
            # Set the path from `pathname`, an output variable from `URLDownloader`.
            self._ensure_path_var("installer_path", "pathname")

        self._check_enum_var("installer_type", CHOCO_FILE_TYPES)
        self._check_enum_var("installer_checksum_type", CHOCO_CHECKSUM_TYPES)

        if (
            "installer_args" in self.env
            and not isinstance(self.env["installer_args"], List)
            and not isinstance(self.env["installer_args"], str)
        ):
            raise ProcessorError(
                "Variable `installer_args` must have type list or string, "
                f"got {self.env['installer_args'].__class_.__name__}"
            )

        output_dir = self.env.get(
            "output_directory",
            os.path.abspath(os.path.join(self.env["RECIPE_CACHE_DIR"], "nupkgs")),
        )
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        build_dir_base = os.path.abspath(
            os.path.join(self.env.get("RECIPE_CACHE_DIR"), "builds")
        )
        if not os.path.exists(build_dir_base):
            os.makedirs(build_dir_base)

        keep_build_directory = self.env.get("KEEP_BUILD_DIRECTORY", False)

        self.env["chocolatey_packager_summary_result"] = {}
        build_dir: Optional[str] = None
        try:
            build_dir = mkdtemp(prefix=f"{self.env['id']}.", dir=build_dir_base)

            self.write_build_configs(build_dir)
            nuget_package_path = self.choco_pack(build_dir, output_dir)
            self.log(f"Wrote Nuget package to: {nuget_package_path}")
            self.env["nuget_package_path"] = nuget_package_path
            self.env["choco_build_directory"] = build_dir
            self.env["chocolatey_packager_summary_result"] = {
                "summary_text": "The following packages were built:",
                "report_fields": ["identifier", "version", "pkg_path"],
                "data": {
                    "identifier": self.env["id"],
                    "version": self.env["version"],
                    "pkg_path": self.env["nuget_package_path"],
                },
            }
        except Exception:
            raise ProcessorError("Chocolatey packaging failed unexpectedly.")
        finally:
            if not keep_build_directory and build_dir is not None:
                rmtree(build_dir)
                self.log("Cleaned up build directory.")
            elif build_dir is not None:
                self.log(f"Preserved build directory: {build_dir}")


if __name__ == "__main__":
    PROCESSOR = ChocolateyPackager()
    PROCESSOR.read_input_plist()
    PROCESSOR.parse_arguments()
    PROCESSOR.process()
    PROCESSOR.write_output_plist()
    # PROCESSOR.execute_shell()
