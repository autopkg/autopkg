#!/usr/bin/env python
#
# Copyright 2014 Thomas Burgin
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


import os
import shutil
import subprocess
import binascii
import datetime
import plistlib

from autopkglib import Processor, ProcessorError

__all__ = ["AbsoluteManageExport"]


class AbsoluteManageExport(Processor):
    '''Take as input a pkg or executable and a SDPackages.ampkgprops (plist config) to output a .amsdpackages for use in Absolute Manage.
        If no SDPackages.ampkgprops is specified a default config will be generated'''

    description = __doc__

    input_variables = {
        'source_payload_path': {
            'description': 'Path to a pkg or executable',
            'required': True,
        },
        'dest_payload_path': {
            'description': 'Path to the exported .amsdpackages',
            'required': True,
        },
        'sdpackages_ampkgprops_path': {
            'description': 'Path to a plist config for the Software Package to be used in Absolute Manage',
            'required': False,
        },
    }

    output_variables = {}
    appleSingleTool = "/Library/Application Support/LANrev Agent/LANrev Agent.app/Contents/MacOS/AppleSingleTool"
    s = lambda x: binascii.b2a_hex(os.urandom(x)).upper()
    unique_id = s(4) + "-" + s(2) + "-" + s(2) + "-" + s(2) + "-" + s(6)
    unique_id_sd = s(4) + "-" + s(2) + "-" + s(2) + "-" + s(2) + "-" + s(6)
    sdpackages_template = {'SDPackageExportVersion': 1, 'SDPayloadFolder': 'Payloads', 'SDPackageList': [{'IsNewEntry': False, 'OptionalData': [], 'RequiresLoggedInUser': False, 'InstallTimeEnd': [], 'AllowOnDemandInstallation': False, 'InstallTime': [], 'AutoStartInstallationMinutes': [], 'SoftwarePatchIdentifier': [], 'RestartNotificationNagTime': [], 'PlatformArchitecture': 131071, 'ExecutableSize': 0, 'ResetSeed': 1, 'Priority': 2, 'WU_LanguageCode': [], 'WU_SuperseededByPackageID': [], 'WU_IsUninstallable': [], 'WU_LastDeploymentChangeTime': [], 'IsMacOSPatch': False, 'UploadStatus': [], 'id': 0, 'RequiresAdminPrivileges': False, 'InstallationContextSelector': 2, 'SoftwareSpecNeedToExist': True, 'MinimumOS': 0, 'Description': '', 'AllowOnDemandRemoval': False, 'RetrySeed': 1, 'MaximumOS': 0, 'SoftwarePatchStatus': 0, 'IsMetaPackage': False, 'SoftwarePatchSupportedOS': [], 'ScanAllVolumes': False, 'DontInstallOnSlowNetwork': False, 'ShowRestartNotification': False, 'SelfHealingOptions': [], 'AllowDeferMinutes': [], 'last_modified': '', 'SoftwarePatchRecommended': [], 'UserContext': '', 'EnableSelfHealing': False, 'InstallationDateTime': [], 'AllowToPostponeRestart': False, 'PayloadExecutableUUID': '', 'WU_IsBeta': [], 'OSPlatform': 1, 'RequiresRestart': 0, 'Name': '', 'FindCriteria': {'Operator': 'AND', 'Value': [{'Operator': 'AND', 'Value': [{'Operator': '=', 'Units': 'Minutes', 'Property': 'Name', 'Value2': '', 'Value': ''}]}, {'UseNativeType': True, 'Value': True, 'Units': 'Minutes', 'Value2': '', 'Operator': '=', 'Property': 'IsPackage'}, {'UseNativeType': True, 'Value': True, 'Units': 'Minutes', 'Value2': '', 'Operator': '=', 'Property': 'IsApplication'}]}, 'SDPayloadList': [{'IsNewEntry': 0, 'OptionalData': [], 'SelectedObjectIsExecutable': True, 'Description': '', 'ExecutableName': '', 'ExecutableSize': 0, 'TransferExecutableFolder': False, 'id': 0, 'SourceFilePath': '', 'last_modified': '', 'PayloadOptions': 0, 'UniqueID': '', 'IsVisible': True, 'UploadStatus': 2, 'MD5Checksum': '', 'Name': ''}], 'DisplayProgressDuringInstall': False, 'ContinueInstallationAfterFailure': False, 'UserInteraction': 1, 'WarnAboutSlowNetwork': False, 'InstallTimeOptions': 1, 'WU_IsMandatory': [], 'DownloadPackagesBeforeShowingToUser': False, 'PackageType': 1, 'WU_Deadline': [], 'SoftwarePatchVersion': [], 'WU_DeploymentAction': [], 'TargetInstallationVolume': '', 'KeepPackageFileAfterInstallation': False, 'MD5Checksum': [], 'TransferExecutableFolder': [], 'WU_SuperseededByPackageName': [], 'StagingServerOption': 1, 'ExecutableOptions': '', 'WU_UninstallationBehaviorImpact': [], 'ExecutableName': [], 'ExecutableServerVolume': [], 'DontInstallIfUserIsLoggedIn': False, 'SourceFilePath': [], 'UserContextPassword': '', 'AvailabilityDate': datetime.datetime.today(), 'WU_InstallationBehaviorImpact': [], 'PostNotificationAutoClose': [], 'UniqueID': '', 'UseSoftwareSpec': False, 'ExecutablePath': [], 'IsWindowsPatch': False}]}

    def export_amsdpackages(self, source_dir, dest_dir, am_options):

        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)

        try:
            os.mkdir(dest_dir)
            os.mkdir(dest_dir + "/Payloads")

        except OSError, err:
            if os.path.exists(dest_dir):
                pass
            else:
                self.output("[+] Failed to create [%s] Please check your permissions and try again. Error [%s]"  (dest_dir, err))

        try:
            subprocess.check_output([self.appleSingleTool, "encode", "-s", source_dir, "-t", dest_dir + "/Payloads/" + self.unique_id])

        except (subprocess.CalledProcessError, OSError), err:
            raise err

        if os.path.exists(am_options):
            shutil.copyfile(am_options, dest_dir + "/SDPackages.ampkgprops")

        else:
            plistlib.writePlist(self.sdpackages_template, dest_dir + "/SDPackages.ampkgprops")

        try:
            executable_size = subprocess.check_output(["/usr/bin/stat", "-f%z", source_dir])
            md5_checksum = subprocess.check_output(["/sbin/md5", dest_dir + "/Payloads/" + self.unique_id]).split("=")[-1].strip(" ")

        except (subprocess.CalledProcessError, OSError), err:
            raise err

        self.sdpackages_template = plistlib.readPlist(dest_dir + "/SDPackages.ampkgprops")

        self.sdpackages_template['SDPackageList'][0]['Name'] = source_dir.split("/")[-1].strip(".pkg")
        self.sdpackages_template['SDPackageList'][0]['PayloadExecutableUUID'] = self.unique_id
        self.sdpackages_template['SDPackageList'][0]['UniqueID'] = self.unique_id_sd
        self.sdpackages_template['SDPackageList'][0]['ExecutableSize'] = int(executable_size)
        self.sdpackages_template['SDPackageList'][0]['SDPayloadList'][0]['ExecutableName'] = source_dir.split("/")[-1]
        self.sdpackages_template['SDPackageList'][0]['SDPayloadList'][0]['ExecutableSize'] = int(executable_size)
        self.sdpackages_template['SDPackageList'][0]['SDPayloadList'][0]['MD5Checksum'] = md5_checksum
        self.sdpackages_template['SDPackageList'][0]['SDPayloadList'][0]['Name'] = source_dir.split("/")[-1].strip(".pkg")
        self.sdpackages_template['SDPackageList'][0]['SDPayloadList'][0]['SourceFilePath'] = source_dir
        self.sdpackages_template['SDPackageList'][0]['SDPayloadList'][0]['UniqueID'] = self.unique_id
        self.sdpackages_template['SDPackageList'][0]['SDPayloadList'][0]['last_modified'] = ""

        plistlib.writePlist(self.sdpackages_template, dest_dir + "/SDPackages.ampkgprops")


    def main(self):
        source_payload = self.env.get('source_payload_path')
        dest_payload = self.env.get('dest_payload_path')
        sdpackages_ampkgprops = self.env.get('sdpackages_ampkgprops_path')

        self.export_amsdpackages(source_payload, dest_payload, sdpackages_ampkgprops)

        self.output("[+] Exported [%s] to ./"
            % source_payload)

if __name__ == '__main__':
    processor = AbsoluteManageExport()
    processor.execute_shell()
