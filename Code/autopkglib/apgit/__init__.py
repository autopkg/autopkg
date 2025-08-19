import os
import subprocess
from typing import Dict, Optional

from autopkglib.common import is_executable, is_linux, is_mac, is_windows, log_err
from autopkglib.prefs import get_pref


# git functions
def git_cmd():
    """Returns a path to a git binary, priority in the order below.
    Returns None if none found.
    1. app pref 'GIT_PATH'
    2. a 'git' binary that can be found in the PATH environment variable
    3. '/usr/bin/git'
    """
    return find_binary("git")


class GitError(Exception):
    """Exception to throw if git fails"""

    pass


def run_git(git_options_and_arguments, git_directory=None):
    """Run a git command and return its output if successful;
    raise GitError if unsuccessful."""
    gitcmd = git_cmd()
    if not gitcmd:
        raise GitError("ERROR: git is not installed!")
    cmd = [gitcmd]
    cmd.extend(git_options_and_arguments)
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=git_directory,
            text=True,
        )
        (cmd_out, cmd_err) = proc.communicate()
    except OSError as err:
        raise GitError from OSError(
            f"ERROR: git execution failed with error code {err.errno}: "
            f"{err.strerror}"
        )
    if proc.returncode != 0:
        raise GitError(f"ERROR: {cmd_err}")
    else:
        return cmd_out


def get_git_commit_hash(filepath):
    """Get the current git commit hash if possible"""
    try:
        git_toplevel_dir = run_git(
            ["rev-parse", "--show-toplevel"], git_directory=os.path.dirname(filepath)
        ).rstrip("\n")
    except GitError:
        return None
    try:
        relative_path = os.path.relpath(filepath, git_toplevel_dir)
        # this was the _wrong_ implementation and essentially is the same
        # as `git hash-object filepath`. It gives us the object hash for the
        # file. Fine for later getting diff info but no good for finding the
        # the commits since the hash was recorded
        #
        # git_hash = run_git(
        #    ['rev-parse', ':' + relative_path],
        #    git_directory=git_toplevel_dir).rstrip('\n')
        #
        # instead, we need to use `rev-list` to find the most recent commit
        # hash for the file in question.
        git_hash = run_git(
            ["rev-list", "-1", "HEAD", "--", relative_path],
            git_directory=git_toplevel_dir,
        ).rstrip("\n")
    except GitError:
        return None
    # make sure the file hasn't been changed locally since the last git pull
    # if git diff produces output, it's been changed, and therefore storing
    # the hash is pointless
    try:
        diff_output = run_git(
            ["diff", git_hash, relative_path], git_directory=git_toplevel_dir
        ).rstrip("\n")
    except GitError:
        return None
    if diff_output:
        return None
    return git_hash


# TODO: Figure out how to move this to make the git functions happy
def find_binary(binary: str, env: Optional[Dict] = None) -> Optional[str]:
    r"""Returns the full path for `binary`, or `None` if it was not found.

    The search order is as follows:
    * A key in the optional `env` dictionary named `<binary>_PATH`.
        Where `binary` is uppercase. E.g., `git` -> `GIT`.
    * A preference named `<binary>_PATH` uppercase, as above.
    * The directories listed in the system-dependent `$PATH` environment variable.
    * On POSIX-y platforms only: `/usr/bin/<binary>`
    In all cases, the binary found at any path must be executable to be used.

    The `binary` parameter should be given without any file extension. A platform
    specific file extension for executables will be added automatically, as needed.

    Example: `find_binary('curl')` may return `C:\Windows\system32\curl.exe`.
    """

    if env is None:
        env = {}
    pref_key = f"{binary.upper()}_PATH"

    bin_env = env.get(pref_key)
    if bin_env:
        if not is_executable(bin_env):
            log_err(
                f"WARNING: path given in the '{pref_key}' environment: '{bin_env}' "
                "either doesn't exist or is not executable! "
                f"Continuing search for usable '{binary}'."
            )
        else:
            return env[pref_key]

    bin_pref = get_pref(pref_key)
    if bin_pref:
        if not is_executable(bin_pref):
            log_err(
                f"WARNING: path given in the '{pref_key}' preference: '{bin_pref}' "
                "either doesn't exist or is not executable! "
                f"Continuing search for usable '{binary}'."
            )
        else:
            return bin_pref

    if is_windows():
        extension = ".exe"
    else:
        extension = ""

    full_binary = f"{binary}{extension}"

    for search_dir in os.get_exec_path():
        exe_path = os.path.join(search_dir, full_binary)
        if is_executable(exe_path):
            return exe_path

    if (is_linux() or is_mac()) and is_executable(f"/usr/bin/{binary}"):
        return f"/usr/bin/{binary}"

    log_err(
        f"WARNING: Unable to find '{full_binary}' in either configured, "
        "or environmental locations. Things aren't guaranteed to work from here."
    )
    return None
