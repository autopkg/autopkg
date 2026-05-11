# Python formatting

This project uses three methods of code style enforcement, linting, and checking:

* [flake8](http://flake8.pycqa.org/en/latest) with [bugbear](https://github.com/PyCQA/flake8-bugbear)
* [isort](https://github.com/timothycrosley/isort)
* [black](https://github.com/python/black)

All code that is contributed to AutoPkg must match these style requirements. These
requirements are enforced by [pre-commit](https://pre-commit.com).

## Use relocatable-python to safely build 3

We recommend using Greg Neagle's [Relocatable Python](https://github.com/gregneagle/relocatable-python) to build a custom Python 3 framework with the included [requirements.txt](https://github.com/autopkg/autopkg/blob/master/requirements.txt).

First, create a safe path to place your frameworks. The easiest choice is
/Users/Shared, because you won't have any permissions issues there, but you can
place this anywhere that makes sense to you:

```sh
mkdir -p /Users/Shared/Python3
```

Now create your relocatable Python frameworks using the provided requirements.txt files:

```sh
./make_relocatable_python_framework.py --python-version 3.10.11 --pip-requirements /path/to/requirements.txt --destination /Users/Shared/Python3/
```

### Symlink the frameworks
You can symlink in the python executables into a more useful path:

```sh
sudo ln -s /Users/Shared/Python3/Python.framework/Versions/3.7/bin/python3 /usr/local/bin/python3_custom
```

## Use pre-commit to set automatic commit requirements

This project makes use of [pre-commit](https://pre-commit.com/) to do automatic
lint and style checking on every commit containing Python files.

To install the pre-commit hook, run the executable from your Python 3 framework
while in your current autopkg git checkout:

```sh
cd ~/autopkg
/Users/Shared/Python3/Python.framework/Versions/3.7/bin/pre-commit install --install-hooks
```

```console
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

```sh
git commit -m "test a bad commit for pre-commit"
```

```console
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

```sh
git commit -m "test a good commit for pre-commit"
```

```console
black....................................................................Passed
isort....................................................................Passed
Flake8...................................................................Passed
[test ebe7fea] test2 for pre-commit
 1 file changed, 3 insertions(+)
```
