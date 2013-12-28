#!/usr/bin/env python
#
# Copyright 2013 Allister Banks, with code heavily influenced/copied from Greg Neagle, Tim Sutton, and Zack Smith. Moral support and general guidance by pudquick/mikeymikey/frogor
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
import FoundationPlist
import shutil
from xml.etree import ElementTree
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
    
    def checkItem(self, repoUrl, apiUrl, item_to_check, base64string):
        """This checks for all items of a certain type, and if found, returns the id"""
        # build our request for the entire list of items
        if apiUrl[-1] == "y":
            submitRequest = urllib2.Request(repoUrl + "/JSSResource/" + apiUrl[:-1] + "ies")
            print('\nTrying to reach JSS and fetch all %s at URL %s' % (apiUrl[:-1] + "ies", repoUrl))
        else:
            submitRequest = urllib2.Request(repoUrl + "/JSSResource/" + apiUrl + "s")
            print('\nTrying to reach JSS and fetch all %s at URL %s' % (apiUrl  + "s", repoUrl))
        submitRequest.add_header("Authorization", "Basic %s" % base64string)
        # try reaching the server and performing the GET
        try:
            submitResult = urllib2.urlopen(submitRequest)
        except urllib2.URLError, e:
            if hasattr(e, 'reason'):
                print 'Error! reason:', e.reason
            elif hasattr(e, 'code'):
                print 'Error! code:', e.code
                if e.code == 401:
                    raise RuntimeError('Got a 401 error.. check the api username and password')
            raise RuntimeError('Did not get a valid response from the server')
        # assign fetched JSS info to a string (or ET) and search if object to create already exists
        jss_results = submitResult.read()
        self.output("Results:", jss_results)
        try:
            xmldata = ElementTree.fromstring(jss_results)
        except:
            raise ProcessorError("Error parsing XML from checkItem results.")
        if apiUrl == "computergroup":
            item_ids = [e.text for e in xmldata.findall('computer_group/id')]
            item_names = [e.text for e in xmldata.findall('computer_group/name')]
        else:
            item_ids = [e.text for e in xmldata.findall(apiUrl + '/id')]
            item_names = [e.text for e in xmldata.findall(apiUrl + '/name')]
        item_nameplusids = zip(item_ids, item_names)
        self.output(item_nameplusids)
        proceed_list = []
        for tup in item_nameplusids:
            if item_to_check == tup[1]:
                proceed_list = ["proceed"]
                proceed_list.append(tup[0])
        self.output(jss_results)
        return proceed_list
    
    def checkSpecificItem(self, repoUrl, apiUrl, item_id, base64string, ids_list=None):
        """This checks for the targeted item in the JSS and returns applicable info"""
        # build our request for the entire list of items
        if apiUrl[-1] != "y":
            submitRequest = urllib2.Request(repoUrl + "/JSSResource/" + apiUrl + "s/id/" + item_id)
            submitRequest.add_header("Authorization", "Basic %s" % base64string)
            submitResult = urllib2.urlopen(submitRequest)
            jss_results = submitResult.read()
            try:
                xmldata = ElementTree.fromstring(jss_results)
            except:
                raise ProcessorError("Error parsing XML from checkItem results.")
            crit_name = [e.text for e in xmldata.findall('criteria/criterion/name')]
            crit_val = [e.text for e in xmldata.findall('criteria/criterion/value')]
            item_nameplusvals = zip(crit_name, crit_val)
            self.output(item_nameplusvals)
            for tup in item_nameplusvals:
                if "Application Version" == tup[0]:
                    found_pkg_ver = tup[1]
            return found_pkg_ver
        else:
            submitRequest = urllib2.Request(repoUrl + "/JSSResource/" + apiUrl[:-1] + "ies/id/" + item_id)
            submitRequest.add_header("Authorization", "Basic %s" % base64string)
            submitResult = urllib2.urlopen(submitRequest)
            jss_results = submitResult.read()
            try:
                xmldata = ElementTree.fromstring(jss_results)
            except:
                raise ProcessorError("Error parsing XML from checkItem results.")
            found_list = []
            item_ids = [e.text for e in xmldata.findall('scope/computer_groups/computer_group/id')]
            item_names = [e.text for e in xmldata.findall('scope/computer_groups/computer_group/name')]
            item_nameplusids = zip(item_ids, item_names)
            self.output(item_nameplusids)
            for tup in item_nameplusids:
                if ids_list[0] == tup[1]:
                    found_list = [tup[0]]
            item_ids = [e.text for e in xmldata.findall('package_configuration/packages/package/id')]
            item_names = [e.text for e in xmldata.findall('package_configuration/packages/package/name')]
            item_nameplusids = zip(item_ids, item_names)
            self.output(item_nameplusids)
            for tup in item_nameplusids:
                if ids_list[1] == tup[1]:
                    found_list.append(tup[0])
            if len(found_list) == 2:
                self.output("Found group id %s and pkg_id %s in policy" % (found_list[0], found_list[1]))
            return found_list
    
    def putUpdate(self, repoUrl, apiUrl, item_id, replace_dict, template_string, base64string):
        """After finding a mismatch, this PUTS a template with updated info"""
        for key, value in replace_dict.iteritems():
            template_string = template_string.replace(key, value)
            if apiUrl[-1] == "y":
                submitRequest = urllib2.Request(repoUrl + "/JSSResource/" + apiUrl[:-1] + "ies/id/" + item_id, template_string, {'Content-type': 'text/xml'})
                self.output("/JSSResource/" + apiUrl[:-1] + "ies/id/" + item_id, template_string)
            else:
                submitRequest = urllib2.Request(repoUrl + "/JSSResource/" + apiUrl + "s/id/" + item_id, template_string, {'Content-type': 'text/xml'})
        submitRequest.add_header("Authorization", "Basic %s" % base64string)
        submitRequest.get_method = lambda: 'PUT'
        submitResult = urllib2.urlopen(submitRequest)
        jss_results = submitResult.read()
        self.output(jss_results)
        self.output("Added to %s section of JSS via API" % apiUrl)
    
    def createObject(self, repoUrl, apiUrl, replace_dict, template_string, base64string):
        """After not finding an item, this updates and POSTs a template at id/0"""
        for key, value in replace_dict.iteritems():
            template_string = template_string.replace(key, value)
            if apiUrl[-1] == "y":
                submitRequest = urllib2.Request(repoUrl + "/JSSResource/" + apiUrl[:-1] + "ies/id/0", template_string, {'Content-type': 'text/xml'})
            else:
                submitRequest = urllib2.Request(repoUrl + "/JSSResource/" + apiUrl + "s/id/0", template_string, {'Content-type': 'text/xml'})
        submitRequest.add_header("Authorization", "Basic %s" % base64string)
        try:
            submitResult = urllib2.urlopen(submitRequest)
        except urllib2.URLError, e:
            if hasattr(e, 'reason'):
                print 'Error! reason:', e.reason
            elif hasattr(e, 'code'):
                print 'Error! code:', e.code
                if e.code == 409:
                    raise RuntimeError('Got a 409 error.. generic "instance busy" issue?')
            raise RuntimeError('Did not get a valid response from the server')
        jss_results = submitResult.read()
        self.output(jss_results)
        try:
            xmldata = ElementTree.fromstring(jss_results)
        except:
            raise ProcessorError("Error parsing XML results after createObject.")
        created_id = xmldata.find("id").text
        self.output("Added to %s section of JSS via API" % apiUrl)
        return created_id
    
    def main(self):
        # pull jss recipe-specific args, prep api auth
        repoUrl = self.env["jss_url"]
        authUser = self.env["api_username"]
        authPass = self.env["api_password"]
        base64string = base64.encodestring('%s:%s' % (authUser, authPass)).replace('\n', '')
        pkg_name = os.path.basename(self.env["pkg_path"])
        prod_name = self.env["prod_name"]
        version = self.env["version"]
        # pre-set 'changed/added/updated' output checks to False
        self.env["jss_repo_changed"] = False
        self.env["jss_category_added"] = False
        self.env["jss_smartgroup_added"] = False
        self.env["jss_smartgroup_updated"] = False
        self.env["jss_staticgroup_added"] = False
        self.env["jss_staticgroup_updated"] = False
        self.env["jss_policy_added"] = False
        self.env["jss_policy_updated"] = False
        #
        # check for category if var set
        #
        if self.env.get("category"):
            category_name = self.env.get("category")
            item_to_check = category_name
            apiUrl = "category"
            proceed_list = self.checkItem(repoUrl, apiUrl, item_to_check, base64string)
            template_string = """<?xml version="1.0" encoding="UTF-8"?><category><name>%CAT_NAME%</name></category>"""
            if "proceed" not in proceed_list:
                replace_dict = {"%CAT_NAME%" : category_name}
                cat_id = self.createObject(repoUrl, apiUrl, replace_dict, template_string, base64string)
                self.env["jss_category_added"] = True
            else:
                self.output("Category already exists according to JSS, moving on")
        #
        # check for package by pkg_name for both API POST
        #   and if exists at repo_path
        #
            template_string = """<?xml version="1.0" encoding="UTF-8"?><package><name>%PKG_NAME%</name><category>%CAT_NAME%</category><filename>%PKG_NAME%</filename><info/><notes/><priority>10</priority><reboot_required>false</reboot_required><fill_user_template>false</fill_user_template><fill_existing_users>false</fill_existing_users><boot_volume_required>false</boot_volume_required><allow_uninstalled>false</allow_uninstalled><os_requirements/><required_processor>None</required_processor><switch_with_package>Do Not Install</switch_with_package><install_if_reported_available>false</install_if_reported_available><reinstall_option>Do Not Reinstall</reinstall_option><triggering_files/><send_notification>false</send_notification></package>"""
            replace_dict = {"%PKG_NAME%" : pkg_name, "%PROD_NAME%" : prod_name, "%CAT_NAME%" : category_name}
        else:
            template_string = """<?xml version="1.0" encoding="UTF-8"?><package><name>%PKG_NAME%</name><filename>%PKG_NAME%</filename><info/><notes/><priority>10</priority><reboot_required>false</reboot_required><fill_user_template>false</fill_user_template><fill_existing_users>false</fill_existing_users><boot_volume_required>false</boot_volume_required><allow_uninstalled>false</allow_uninstalled><os_requirements/><required_processor>None</required_processor><switch_with_package>Do Not Install</switch_with_package><install_if_reported_available>false</install_if_reported_available><reinstall_option>Do Not Reinstall</reinstall_option><triggering_files/><send_notification>false</send_notification></package>"""
            replace_dict = {"%PKG_NAME%" : pkg_name, "%PROD_NAME%" : prod_name}
        apiUrl = "package"
        item_to_check = pkg_name
        proceed_list = self.checkItem(repoUrl, apiUrl, item_to_check, base64string)
        if "proceed" not in proceed_list:
            pkg_id = self.createObject(repoUrl, apiUrl, replace_dict, template_string, base64string)
        else:
              pkg_id = str(proceed_list[1])
              self.output("Pkg already exists according to JSS, moving on")
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
        #
        # check for smartGroup if var set
        #
        if self.env.get("smart_group"):
            smart_group_name = self.env.get("smart_group")
            item_to_check = smart_group_name
            apiUrl = "computergroup"
            proceed_list = self.checkItem(repoUrl, apiUrl, item_to_check, base64string)
            template_string = """<?xml version="1.0" encoding="UTF-8"?><computer_group><name>LessThanMostRecent_%PROD_NAME%</name><is_smart>true</is_smart><criteria><size>2</size><criterion><name>Application Title</name><priority>0</priority><and_or>and</and_or><search_type>is</search_type><value>%PROD_NAME%</value></criterion><criterion><name>Application Version</name><priority>1</priority><and_or>and</and_or><search_type>is not</search_type><value>%version%</value></criterion></criteria><computers><size>0</size></computers></computer_group>"""
            replace_dict = {"%PROD_NAME%" : prod_name, "%version%" : version}
            if "proceed" not in proceed_list:
                grp_id = self.createObject(repoUrl, apiUrl, replace_dict, template_string, base64string)
                self.env["jss_smartgroup_added"] = True
            else:
                grp_id = str(proceed_list[1])
                pkg_ver = self.checkSpecificItem(repoUrl, apiUrl, grp_id, base64string)
                if pkg_ver != version:
                    self.putUpdate(repoUrl, apiUrl, grp_id, replace_dict, template_string, base64string)
                    self.env["jss_smartgroup_updated"] = True
        #
        # check for arbitraryGroupID if var set
        #
        if self.env.get("arb_group_name"):
            static_group_name = self.env.get("arb_group_name")
            item_to_check = static_group_name
            apiUrl = "computergroup"
            proceed_list = self.checkItem(repoUrl, apiUrl, item_to_check, base64string)
            if "proceed" not in proceed_list:
                raise ProcessorError("Static group not present in JSS.")
            else:
                grp_id = str(proceed_list[1])
        #
        # check for policy if var set
        #
        if self.env.get("selfserve_policy"):
            item_to_check = self.env.get("selfserve_policy")
            apiUrl = "policy"
            proceed_list = self.checkItem(repoUrl, apiUrl, item_to_check, base64string)
            template_string = """<?xml version="1.0" encoding="UTF-8"?><policy><general><name>SelfServeLatest_%PROD_NAME%</name><enabled>true</enabled><frequency>Once per computer</frequency></general><scope><computer_groups><computer_group><id>%grp_id%</id></computer_group></computer_groups></scope><self_service><use_for_self_service>true</use_for_self_service></self_service><package_configuration><packages><size>1</size><package><id>%pkg_id%</id><action>Install</action></package></packages></package_configuration><maintenance><recon>true</recon></maintenance></policy>"""
            self.output("Current grp_id is %s, pkg_id is %s" % (grp_id, pkg_id))
            replace_dict = {"%PROD_NAME%" : prod_name, "%grp_id%" : grp_id, "%pkg_id%" : pkg_id}
            if "proceed" not in proceed_list:
                self.createObject(repoUrl, apiUrl, replace_dict, template_string, base64string)
                self.env["jss_policy_added"] = True
            else:
                policy_id = str(proceed_list[1])
                if self.env.get("smart_group"):
                    group_name = smart_group_name
                else:
                    group_name = static_group_name
                found_list = self.checkSpecificItem(repoUrl, apiUrl, policy_id, base64string, [group_name, pkg_name])
                if len(found_list) != 2:
                    self.putUpdate(repoUrl, apiUrl, policy_id, replace_dict, template_string, base64string)
                    self.env["jss_policy_updated"] = True
                elif grp_id != found_list[0] or pkg_id != found_list[1]:
                    self.output("current pkg_id is %s, found is %s current group_id is %s, found is %s" % (pkg_id, found_list[1], grp_id, found_list[0]))
                    self.putUpdate(repoUrl, apiUrl, policy_id, replace_dict, template_string, base64string)
                    self.env["jss_policy_updated"] = True

if __name__ == "__main__":
    processor = JSSImporter()
    processor.execute_shell()