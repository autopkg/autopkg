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
#
# This powershell script exists to provide a convenient wrapper around autopkg on 
# Windows that ensures the right python version and dependencies are used.

<#

.Synopsis
AutoPkg is an automation framework software packaging and distribution, oriented towards
the tasks one would normally perform manually to prepare third-party software for mass
deployment to managed clients.

.Parameter Subcommand
Which specific action to perform, such as: `help`, `audit`, `info`, `install`,
`list-recipes`, `list-repos`, `list-processors`, `run`, and `search`.
More subcommands can be found with the `help` subcommand.

.Parameter AutopkgArgs
Internal argument used for passing arguments after `Subcommand to the real autopkg script.

.Example
   autopkg.ps1 info AutopkgGitMaster.nupkg

Display information such as inputs for the AutopkgGitMaster.nupkg recipe.

.Example
   autopkg.ps1 run AutopkgGitMaster.nupkg

Build the Windows autopkg package from github master branch.

#>

Param(
    [Parameter(Mandatory = $true, Position = 0)]
    [String]
    $Subcommand,
    [Parameter(Position = 1, ValueFromRemainingArguments)]
    [String[]]
    $AutopkgArgs
)

$AutopkgRoot = Join-Path -Resolve -Path $(Split-Path -Parent $PSCommandPath) -ChildPath '..'
if (Test-Path $AutopkgRoot\.python-env) {
    . $AutopkgRoot\.python-env\Scripts\Activate.ps1
}
$AutopkgScript = Join-Path $AutopkgRoot 'Code\autopkg'

& python $AutopkgScript $Subcommand $AutopkgArgs