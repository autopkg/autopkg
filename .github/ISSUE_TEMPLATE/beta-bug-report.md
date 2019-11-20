---
name: Beta Bug report
about: Report an issue with AutoPkg BETA only
title: ''
labels: beta
assignees: nmcspadden

---

**THIS IS ONLY INTENDED FOR AUTOPKG BETAS.**

**Describe the problem**
A clear and concise description of what the problem is.

**Preferences contents**
*BE SURE TO SANITIZE ANY SENSITIVE DATA SUCH AS PASSWORDS OR ADDRESSES.*
Provide the output of `defaults read com.github.autopkg`, or the contents of your external `--prefs` file. 

**AutoPkg output**
*BE SURE TO SANITIZE ANY SENSITIVE DATA SUCH AS PASSWORDS OR ADDRESSES.*
Provide the output of `autopkg run -vvvv <RecipeName>`, or any other command you are running. Please include as much data as possible.

**Expected behavior**
A clear and concise description of what you expected to happen. What specific part of the recipe or AutoPkg run did not behave correctly?

**Version (please complete the following information):**
 - OS version: [e.g. 10.14.6, 10.15.1]
- AutoPkg Version: [e.g. 2.0b1, 2.0b2, a specific commit, etc]
