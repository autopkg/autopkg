# Python formatting

This project uses three methods of code style enforcement, linting, and checking:
* [flake8](http://flake8.pycqa.org/en/latest) with [bugbear](https://github.com/PyCQA/flake8-bugbear)
* [isort](https://github.com/timothycrosley/isort)
* [black](https://github.com/python/black)

All code that is contributed to AutoPkg must match these style requirements. These
requirements are enforced by [pre-commit](https://pre-commit.com).

## Python 2 and Python 3

While macOS transitions from Python 2 to Python 3, this project will as well.
Until the transition is complete, this project needs to be compatible with both
Python 2 and Python 3. Since this project also uses Black for enforced style,
it's necessary to have both Pythons installed in order to effectively
contribute.

Python 3 is required to run black and flake8 with the bugbear plugin.

## Use relocatable-python to safely build Python 2 and 3

We recommend using Greg Neagle's [Relocatable Python](https://github.com/gregneagle/relocatable-python)
to build a custom Python 2 and Python 3 framework.

This project provides two different requirements.txt files - one for 2, one for
3. You can use Relocatable Python to build a custom Python framework with all
of the requirements pre-installed.

First, create a safe path to place your frameworks. The easiest choice is
/Users/Shared, because you won't have any permissions issues there:
```
mkdir -p /Users/Shared/Python2 /Users/Shared/Python3
```

Now create your relocatable Python frameworks using the provided requirements.txt files:
```
./make_relocatable_python_framework.py --python-version 2.7.15 --pip-requirements /path/to/python2_requirements.txt --destination /Users/Shared/Python2/
./make_relocatable_python_framework.py --python-version 3.7.3 --pip-requirements /path/to/python3_requirements.txt --destination /Users/Shared/Python3/
```

### Symlink the frameworks
You can symlink in the python executables into a more useful path:
```
sudo ln -s /Users/Shared/Python2/Python.framework/Versions/Current/bin/python2.7 /usr/local/bin/python2_custom
sudo ln -s /Users/Shared/Python3/Python.framework/Versions/3.7/bin/python3 /usr/local/bin/python3_custom
```

## Use pre-commit to set automatic commit requirements

This project makes use of [pre-commit](https://pre-commit.com/) to do automatic
lint and style checing on every commit containing Python files.

To install the pre-commit hook, run the executable from your Python 3 framework
while in your current autopkg git checkout:
```
$ cd ~/autopkg
$ /Users/Shared/Python3/Python.framework/Versions/3.7/bin/pre-commit install --install-hooks
pre-commit installed at .git\hooks\pre-commit
[INFO] Initializing environment for https://github.com/pre-commit/mirrors-isort.
[INFO] Initializing environment for https://github.com/pre-commit/pre-commit-hooks.
[INFO] Installing environment for https://github.com/python/black.
[INFO] Once installed this environment will be reused.
[INFO] This may take a few minutes...
[INFO] Installing environment for https://github.com/pre-commit/mirrors-isort.
[INFO] Once installed this environment will be reused.
[INFO] This may take a few minutes...
[INFO] Installing environment for https://github.com/pre-commit/pre-commit-hooks.
[INFO] Once installed this environment will be reused.
[INFO] This may take a few minutes...
```

Once installed, all commits will run the test hooks. If your commit fails any of
the tests, the commit will be rejected.

### Example of a failed commit
```
$ git commit -m "test a bad commit for pre-commit"
black....................................................................Failed
hookid: black

Files were modified by this hook. Additional output:

reformatted Code\autopkglib\AppDmgVersioner.py
All done! \u2728 \U0001f370 \u2728
1 file reformatted.

isort....................................................................Failed
hookid: isort

Files were modified by this hook. Additional output:

Fixing C:\Users\nmcspadden\Documents\GitHub\nmcspadden-autopkg\Code\autopkglib\AppDmgVersioner.py

Flake8...................................................................Failed
hookid: flake8

Code/autopkglib/AppDmgVersioner.py:31:1: E303 too many blank lines (3)
```

### Example of a successful commit
```
$ git commit -m "test a good commit for pre-commit"
black....................................................................Passed
isort....................................................................Passed
Flake8...................................................................Passed
[test ebe7fea] test2 for pre-commit
 1 file changed, 3 insertions(+)
```
