AutoPkg
=======

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)

Latest release is [here](https://github.com/autopkg/autopkg/releases/latest).

AutoPkg is an automation framework for macOS software packaging and distribution, oriented towards the tasks one would normally perform manually to prepare third-party software for mass deployment to managed clients.

These tasks typically involve at least several of the following steps:

* downloading an application and/or updates for it, usually via a web browser
* extracting them from a multitude of archive formats
* adding site-specific configuration
* adding sane versioning information
* "fixing" poorly-written installer scripts
* saving these modifications back to a compressed disk image or installer package
* importing these into a software distribution system like Munki, Jamf Pro, FileWave, etc.
* customizing the associated metadata for such a system with site-specific data, post-installation scripts, version info or other metadata

Often these tasks follow similar patterns for each individual application, and when managing many applications this becomes a daily task full of sub-tasks that one must remember (and/or maintain documentation for) about exactly what had to be done for a successful deployment of every update for every managed piece of software.

With AutoPkg, we define these steps in a "Recipe" plist-based format, run automatically instead of by hand, and shared with others.


Installation
------------

Install the [latest release](https://github.com/autopkg/autopkg/releases/latest).

AutoPkg requires macOS, and Git is highly recommended to have installed so that autopkg can use git to can manage recipe repositories. Knowledge of Git itself is not required.

AutoPkg is tested on the current macOS release. It may work on older releases, but is not actively tested on older releases.

Git can be installed via Apple's command-line developer tools package, which can be prompted for installation by simply typing 'git' in a Terminal window (OS X 10.9 or later).

Since AutoPkg 2.0, Python 2 is no longer supported. The installer linked above contains a bundled version of Python 3 and all needed dependencies.


Usage
-----

A getting started guide is available [here](https://github.com/autopkg/autopkg/wiki/Getting-Started).

Frequently Asked Questions (and answers!) are [here](https://github.com/autopkg/autopkg/wiki/FAQ).

See [the wiki](https://github.com/autopkg/autopkg/wiki) for more documentation.


Discussion
----------

Discussion of the use and development of AutoPkg is [here](http://groups.google.com/group/autopkg-discuss).
