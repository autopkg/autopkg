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
from autopkglib import Copier

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
    output_variables = {}
    #     "jss_category_added": {
    #         "description": "True if category was created."
    #     },
    #     "jss_repo_changed": {
    #         "description": "True if item was imported."
    #     },
    # }
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
        category_match = re.search(re.escape(item_to_check), jss_results)
        if category_match:
            return "proceed"
        else:
            bracket = "<id>"
            nums = re.findall(re.escape(bracket) + r'\d+', jss_results)
            highest_num = max(nums)
            highest_id = int(highest_num[4:])
            highest_id += 1
            return highest_id

    def customizeAndPostPackage(self, repoUrl, pkg_id, pkg_name, prod_name, template_string, base64string):
        """After finding an unused id, this updates a template with the id and product name for a category"""
        replace_dict = {"%PKG_ID%" : pkg_id, "%PKG_NAME%" : pkg_name, "%PROD_NAME%" : prod_name}
        for key, value in replace_dict.iteritems():
            template_string = template_string.replace(key, value)
        submitRequest = urllib2.Request(repoUrl + "/JSSResource/packages/id/" + pkg_id, template_string, {'Content-type': 'text/xml'})
        submitRequest.add_header("Authorization", "Basic %s" % base64string)
        submitResult = urllib2.urlopen(submitRequest)
        submittedResult = submitResult.read()
        self.output("Added package to JSS via API")

    def customizeAndPostCategory(self, repoUrl, cat_id, cat_name, template_string, base64string):
        """After finding an unused id, this updates a template with the id and product name for a category"""
        replace_dict = {"%CAT_ID%" : cat_id, "%CAT_NAME%" : cat_name}
        for key, value in replace_dict.iteritems():
            template_string = template_string.replace(key, value)
        submitRequest = urllib2.Request(repoUrl + "/JSSResource/categories/id/" + cat_id, template_string, {'Content-type': 'text/xml'})
        submitRequest.add_header("Authorization", "Basic %s" % base64string)
        submitResult = urllib2.urlopen(submitRequest)
        submittedResult = submitResult.read()
        self.output("Added category to JSS via API")

    def main(self):
        repoUrl = self.env["jss_url"]
        authUser = self.env["api_username"]
        authPass = self.env["api_password"]
        base64string = base64.encodestring('%s:%s' % (authUser, authPass)).replace('\n', '')
        pkg_name = os.path.basename(self.env["pkg_path"])
        prod_name = self.env["prod_name"]
        # create category if var set
        if self.env.get("category"):
            item_to_check = "<name>" + prod_name + "</name>"
            apiUrl = "categories"
            #run me some main, why dontcha, capturing the checkCategory stages output
            highest_id = self.checkItem(repoUrl, base64string, item_to_check, apiUrl)
            # if prod name already exists then we'd proceed to the next processor, otherwise
            template_string = """<?xml version="1.0" encoding="UTF-8"?><category><id>%CAT_ID%</id><name>%CAT_NAME%</name></category>"""
            if highest_id != "proceed":
                highest_id = str(highest_id)
                self.customizeAndPostCategory(repoUrl, highest_id, prod_name, template_string, base64string)
        # start metadata/pkg upload
        template_string = """<?xml version="1.0" encoding="UTF-8"?><package><id>%PKG_ID%</id><name>%PKG_NAME%</name><category>%PROD_NAME%</category><filename>%PKG_NAME%</filename><info/><notes/><priority>10</priority><reboot_required>false</reboot_required><fill_user_template>false</fill_user_template><fill_existing_users>false</fill_existing_users><boot_volume_required>false</boot_volume_required><allow_uninstalled>false</allow_uninstalled><os_requirements/><required_processor>None</required_processor><switch_with_package>Do Not Install</switch_with_package><install_if_reported_available>false</install_if_reported_available><reinstall_option>Do Not Reinstall</reinstall_option><triggering_files/><send_notification>false</send_notification></package>"""
        apiUrl = "packages"
        item_to_check = "<name>" + pkg_name + "</name>"
        highest_id = self.checkItem(repoUrl, base64string, item_to_check, apiUrl)
        source_item = self.env["pkg_path"]
        dest_item = (self.env["repo_path"] + "/" + pkg_name)
        try:
            shutil.copyfile(source_item, dest_item)
            self.output("Copied %s to %s" % (source_item, dest_item))
        except BaseException, err:
            raise ProcessorError(
                "Can't copy %s to %s: %s" % (source_item, dest_item, err))        
        apiUrl = "packages"
        #run me some main, why dontcha, capturing the checkCategory stages output
        highest_id = self.checkItem(repoUrl, base64string, item_to_check, apiUrl)
        # if prod name already exists then we'd proceed to the next processor,
        if highest_id != "proceed":
            pkg_id = str(highest_id)
            self.customizeAndPostPackage(repoUrl, pkg_id, pkg_name, prod_name, template_string, base64string)        
        
        # set output variables
        self.env["jss_repo_changed"] = True
        
        self.output("Copied pkg to %s" % self.env["repo_path"])

if __name__ == "__main__":
    processor = JSSImporter()
    processor.execute_shell()