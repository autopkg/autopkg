#!/usr/bin/env python
#
# Copyright 2013 Allister Banks, with code heavily influenced/copied from Greg Neagle, Tim Sutton, and Zack Smith. Moral support and general gudance by pudquick/mikeymikey/frogor
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


import os, urllib2, sys, re, base64
import subprocess
import FoundationPlist
import shutil

from distutils import version

from autopkglib import Processor, ProcessorError

__all__ = ["JSSImporter"]


class JSSImporter(Processor):
    """Imports a flat pkg to the JSS."""
    input_variables = {
        "pkg_path": {
            "required": True,
            "description": "Path to a pkg or dmg to import - provided by previous pkg recipe/processor.",
        },
        "repo_path": {
            "required": True,
            "description": "Path to a mounted or otherwise local JSS dist point share.",
        },
        "jss_url": {
            "required": True,
            "description": "URL to a JSS that api user can access.",
        },
        "api_username": {
            "required": True,
            "description": "Username of account with appropriate access to jss.",
        },
        "api_password": {
            "required": True,
            "description": "Password of api user, processed along with name, with base64 encoding.",
        },
        "category": {
            "required": False,
            "description": ("Category to create/associate imported app with - created if not present"),
        },
        "selfserve_policy": {
            "required": False,
            "description": "Name of automatically activated self-service policy for offering software to test and older-version users.",
        },
        "stub_policy": {
            "required": False,
            "description": "Name of policy with which to promote software to production once approved and activated.",
        },
        "smart_group": {
            "required": False,
            "description": "Name of scoping group to create with which to offer item to users with an older version.",
        },
        "static_group": {
            "required": False,
            "description": "Name of static group to create with which to offer item to users with an older version.",
        },
    }
    output_variables = {
        "jss_category_added": {
            "description": "True if category was created."
        },
        "jss_repo_changed": {
            "description": "True if item was imported."
        },
        "jss_smartgroup_added": {
            "description": "True if smartgroup was added."
        },
        "jss_smartgroup_updated": {
            "description": "True if smartgroup was updated."
        },
        "jss_staticgroup_added": {
            "description": "True if staticgroup was added."
        },
        "jss_staticgroup_updated": {
            "description": "True if staticgroup was updated."
        },
        "jss_policy_added": {
            "description": "True if policy was added."
        },
        "jss_policy_updated": {
            "description": "True if policy was updated."
        },
    
    }
    description = __doc__
    
    def checkItem(self, repoUrl, base64string, item_to_check, apiUrl):
        """This checks for the targeted item in the JSS and returns the id, otherwise it does a search for the highest unused id with which to create it"""
        # build our request for the entire list of categories
        submitRequest = urllib2.Request(repoUrl + "/JSSResource/" + apiUrl)
        submitRequest.add_header("Authorization", "Basic %s" % base64string)
        # try reaching the server and performing the GET
        print('\nTrying to reach JSS and fetch all %s at URL %s' % (apiUrl, repoUrl))
        try:
            submitResult = urllib2.urlopen(submitRequest)
        except urllib2.URLError, e:
            if hasattr(e, 'reason'):
                print 'Error! reason:', e.reason
            elif hasattr(e, 'code'):
                print 'Error! code:', e.code
                if e.code == 401:
                    raise RuntimeError('Got a 401 error.. check the validity of the authorization file')
            raise RuntimeError('Did not get a valid response from the server')
        # assign fetched JSS categories to a string and search if prod name already exists
        jss_results = submitResult.read()
        item_match = re.search(re.escape(item_to_check), jss_results)
        if item_match:
            highest_id = ["proceed"]
            snip_front = "(\d+)" + "(" + "</id>" + item_to_check + ")"
            the_id = re.search(snip_front, jss_results)
            highest_id.append(the_id.group(1))
            something = str(highest_id[1])
            self.output("Found %s at id %s, moving on" % (item_to_check, something))
            return highest_id
        else:
            bracket = "<id>"
            nums = re.findall(re.escape(bracket) + r'\d+', jss_results)
            highest_num = max(nums)
            highest_id = int(highest_num[4:])
            highest_id += 1
            next_index_list = [highest_id]
            return next_index_list
    
    def checkItemVersion(self, repoUrl, base64string, item_version, apiUrl):
        pass
    
    def customizeAndPostXMLtoAPI(self, repoUrl, apiUrl, item_id, replace_dict, template_string, base64string):
        """After finding an unused id, this updates a template with the id and product name for a category"""
        for key, value in replace_dict.iteritems():
            template_string = template_string.replace(key, value)
        submitRequest = urllib2.Request(repoUrl + "/JSSResource/" + apiUrl + "/id/" + item_id, template_string, {'Content-type': 'text/xml'})
        submitRequest.add_header("Authorization", "Basic %s" % base64string)
        submitResult = urllib2.urlopen(submitRequest)
        submittedResult = submitResult.read()
        self.output("Added to %s section of JSS via API" % apiUrl)
    
    def customizeAndPostPolicy(self, repoUrl, apiUrl, replace_dict, template_string, base64string):
        """After finding an unused id, this updates a template with the id and product name for a category"""
        for key, value in replace_dict.iteritems():
            template_string = template_string.replace(key, value)
        submitRequest = urllib2.Request(repoUrl + "/JSSResource/" + apiUrl + "/id/0", template_string, {'Content-type': 'text/xml'})
        submitRequest.add_header("Authorization", "Basic %s" % base64string)
        submitResult = urllib2.urlopen(submitRequest)
        submittedResult = submitResult.read()
        self.output("Added to %s section of JSS via API" % apiUrl)
    
    def main(self):
        # pull jss recipe-specific args, prep api auth
        repoUrl = self.env["jss_url"]
        authUser = self.env["api_username"]
        authPass = self.env["api_password"]
        base64string = base64.encodestring('%s:%s' % (authUser, authPass)).replace('\n', '')
        pkg_name = os.path.basename(self.env["pkg_path"])
        prod_name = self.env["prod_name"]
        version = self.env["version"]
        # pre-set 'changed' output checks to False
        self.env["jss_repo_changed"] = False
        self.env["jss_category_added"] = False
        self.env["jss_smartgroup_added"] = False
        self.env["jss_smartgroup_updated"] = False
        self.env["jss_staticgroup_added"] = False
        self.env["jss_staticgroup_updated"] = False
        self.env["jss_policy_added"] = False
        self.env["jss_policy_updated"] = False
        # check for category if var set
        #
        if self.env.get("category"):
            item_to_check = "<name>" + prod_name + "</name>"
            apiUrl = "categories"
            highest_id = self.checkItem(repoUrl, base64string, item_to_check, apiUrl)
            # if prod named category already exists then we'd proceed to the next stage, otherwise
            template_string = """<?xml version="1.0" encoding="UTF-8"?><category><id>%CAT_ID%</id><name>%CAT_NAME%</name></category>"""
            if "proceed" not in highest_id:
                highest_id = str(highest_id[0])
                replace_dict = {"%CAT_ID%" : highest_id, "%CAT_NAME%" : prod_name}
                self.customizeAndPostXMLtoAPI(repoUrl, apiUrl, highest_id, replace_dict, template_string, base64string)
                self.env["jss_category_added"] = True
        # start metadata/pkg upload
        template_string = """<?xml version="1.0" encoding="UTF-8"?><package><id>%PKG_ID%</id><name>%PKG_NAME%</name><category>%PROD_NAME%</category><filename>%PKG_NAME%</filename><info/><notes/><priority>10</priority><reboot_required>false</reboot_required><fill_user_template>false</fill_user_template><fill_existing_users>false</fill_existing_users><boot_volume_required>false</boot_volume_required><allow_uninstalled>false</allow_uninstalled><os_requirements/><required_processor>None</required_processor><switch_with_package>Do Not Install</switch_with_package><install_if_reported_available>false</install_if_reported_available><reinstall_option>Do Not Reinstall</reinstall_option><triggering_files/><send_notification>false</send_notification></package>"""
        apiUrl = "packages"
        item_to_check = "<name>" + pkg_name + "</name>"
        highest_id = self.checkItem(repoUrl, base64string, item_to_check, apiUrl)
        # if prod name already exists then we'd proceed to the next stage
        if "proceed" not in highest_id:
            pkg_id = str(highest_id[0])
            replace_dict = {"%PKG_ID%" : pkg_id, "%PKG_NAME%" : pkg_name, "%PROD_NAME%" : prod_name}
            self.customizeAndPostXMLtoAPI(repoUrl, apiUrl, pkg_id, replace_dict, template_string, base64string)
        else:
              pkg_id = str(highest_id[1])
        source_item = self.env["pkg_path"]
        dest_item = (self.env["repo_path"] + "/" + pkg_name)
        if os.path.exists(dest_item):
            self.output("Pkg already exists at %s, moving on" % dest_item)
        else:
            try:
                shutil.copyfile(source_item, dest_item)
                self.output("Copied %s to %s" % (source_item, dest_item))
                # set output variables
                self.env["jss_repo_changed"] = True
            except BaseException, err:
                raise ProcessorError(
                    "Can't copy %s to %s: %s" % (source_item, dest_item, err))
        if self.env.get("smart_group"):
            smart_group_name = self.env.get("smart_group")
            item_to_check = "<name>" + smart_group_name + "</name>"
            apiUrl = "computergroups"
            highest_id = self.checkItem(repoUrl, base64string, item_to_check, apiUrl)
            # if smart group already exists then we'd proceed to the next stage
            template_string = """<?xml version="1.0" encoding="UTF-8"?><computer_group><id>%GRP_ID%</id><name>LessThanMostRecent_%PROD_NAME%</name><is_smart>true</is_smart><site><id>-1</id><name>None</name></site><criteria><size>2</size><criterion><name>Application Title</name><priority>0</priority><and_or>and</and_or><search_type>is</search_type><value>%PROD_NAME%</value></criterion><criterion><name>Application Version</name><priority>1</priority><and_or>and</and_or><search_type>is not</search_type><value>%version%</value></criterion></criteria><computers><size>0</size></computers></computer_group>"""
            if "proceed" not in highest_id:
                grp_id = str(highest_id[0])
                replace_dict = {"%GRP_ID%" : grp_id, "%PROD_NAME%" : prod_name, "%version%" : version}
                self.customizeAndPostXMLtoAPI(repoUrl, apiUrl, grp_id, replace_dict, template_string, base64string)
                self.env["jss_smartgroup_added"] = True
            else:
                grp_id = str(highest_id[1])
        if self.env.get("selfserve_policy"):
            item_to_check = "<name>" + "SelfServeLatest_" + prod_name + "</name>"
            apiUrl = "policies"
            highest_id = self.checkItem(repoUrl, base64string, item_to_check, apiUrl)
            # if prod named category already exists then we'd proceed to the next stage, otherwise
            template_string = """<?xml version="1.0" encoding="UTF-8"?><policy><general><name>SelfServeLatest_%PROD_NAME%</name><enabled>true</enabled><trigger>USER_INITIATED</trigger><frequency>Once per computer</frequency><override_default_settings><target_drive>default</target_drive><distribution_point/><force_afp_smb>false</force_afp_smb><sus>default</sus><netboot_server>current</netboot_server></override_default_settings></general><scope><computer_groups><computer_group><id>%grp_id%</id></computer_group></computer_groups></scope><self_service><use_for_self_service>true</use_for_self_service><install_button_text>Install</install_button_text><self_service_description/><force_users_to_view_description>false</force_users_to_view_description><self_service_icon/></self_service><package_configuration><packages><size>1</size><package><id>%pkg_id%</id><name>%PKG_NAME%</name><action>Install</action><fut>false</fut><feu>false</feu><update_autorun>false</update_autorun></package></packages></package_configuration><maintenance><recon>true</recon></maintenance></policy>"""
            if "proceed" not in highest_id:
                policy_name = "SelfServeLatest_" + prod_name
                replace_dict = {"%grp_id%" : grp_id, "%PROD_NAME%" : prod_name, "%pkg_id%" : pkg_id, "%PKG_NAME%" : pkg_name}
                self.customizeAndPostPolicy(repoUrl, apiUrl, replace_dict, template_string, base64string)
                self.env["jss_policy_added"] = True

if __name__ == "__main__":
    processor = JSSImporter()
    processor.execute_shell()