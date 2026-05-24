from autopkglib.munkirepolibs.AutoPkgLib import AutoPkgLib
from autopkglib.munkirepolibs.MunkiLib import MunkiLib


def fetch_repo_library(
    munki_repo, munki_repo_plugin, munkilib_dir, repo_subdirectory, force_munki_lib
):
    """Return the appropriate repo library for the given plugin configuration."""
    if munki_repo_plugin == "FileRepo" and not force_munki_lib:
        return AutoPkgLib(munki_repo, repo_subdirectory)
    else:
        return MunkiLib(munki_repo, munki_repo_plugin, munkilib_dir, repo_subdirectory)
