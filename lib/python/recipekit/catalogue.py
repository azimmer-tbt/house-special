# catalogue.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""The processor-output catalogue: which variables each built-in processor sets.

One table for the whole kit (specs/recipekit/01-recipe-model.md FR-07). No other
tool keeps its own copy (AIP-05). Values follow the `output_variables` of AutoPkg's
own processors; update them from AutoPkg's source and cite the version.

Checked against AutoPkg 2.9.
"""

# Variables AutoPkg sets for every recipe run (FR-06, step 1).
AUTOPKG_VARS = frozenset(
    {
        "RECIPE_DIR",
        "RECIPE_CACHE_DIR",
        "RECIPE_PATH",
        "PARENT_RECIPES",
        "RECIPE_SEARCH_DIRS",
        "CACHE_DIR",
        "verbose",
    }
)

# Static outputs per built-in processor. Processors whose outputs depend on their
# arguments (URLTextSearcher, Versioner, PlistReader) are handled in
# `outputs()`; their static entry lists what they always set.
PROCESSOR_OUTPUTS: dict[str, frozenset[str]] = {
    "AppDmgVersioner": frozenset({"app_name", "bundleid", "version"}),
    "AppPkgCreator": frozenset(
        {"pkg_path", "version", "app_pkg_creator_summary_result"}
    ),
    "CodeSignatureVerifier": frozenset(),
    "Copier": frozenset(),
    "DeprecationWarning": frozenset(),
    "DmgCreator": frozenset({"dmg_path"}),
    "DmgMounter": frozenset(),
    "EndOfCheckPhase": frozenset(),
    "FileCreator": frozenset(),
    "FileFinder": frozenset({"found_filename", "found_basename"}),
    "FileMover": frozenset(),
    "FlatPkgPacker": frozenset(),
    "FlatPkgUnpacker": frozenset(),
    "GitHubReleasesInfoProvider": frozenset(
        {"url", "version", "release_notes", "asset_url", "asset_created_at"}
    ),
    "InstallFromDMG": frozenset(),
    "Installer": frozenset(),
    "MunkiImporter": frozenset(
        {
            "pkginfo_repo_path",
            "pkg_repo_path",
            "munki_info",
            "munki_repo_changed",
            "munki_importer_summary_result",
        }
    ),
    "PathDeleter": frozenset({"path_deleter_summary_result"}),
    "PkgCopier": frozenset({"pkg_path", "pkg_copier_summary_result"}),
    "PkgCreator": frozenset(
        {"pkg_path", "new_package_request", "pkg_creator_summary_result"}
    ),
    "PkgExtractor": frozenset(),
    "PkgPayloadUnpacker": frozenset(),
    "PkgRootCreator": frozenset({"pkgroot", "pkgdirs"}),
    "PlistEditor": frozenset(),
    "PlistReader": frozenset(),
    "SparkleUpdateInfoProvider": frozenset({"url", "version", "additional_pkginfo"}),
    "StopProcessingIf": frozenset({"stop_processing_recipe"}),
    "Symlinker": frozenset(),
    "Unarchiver": frozenset(),
    "URLDownloader": frozenset(
        {
            "pathname",
            "download_changed",
            "last_modified",
            "etag",
            "url_downloader_summary_result",
        }
    ),
    "URLGetter": frozenset(),
    "URLTextSearcher": frozenset(),
    "Versioner": frozenset(),
}


def is_shared(processor: str) -> bool:
    """A shared processor is referenced as `<recipe identifier>/<Processor>`."""
    return "/" in processor


def is_known(processor: str) -> bool:
    """True for a built-in processor with a catalogue entry."""
    return not is_shared(processor) and processor in PROCESSOR_OUTPUTS


def outputs(processor: str, args: dict, resolve) -> frozenset[str] | None:
    """Variables a step sets, or None when that can't be known (shared or unknown
    processors). `resolve(text)` substitutes Input values, so a `re_pattern` held in
    an Input variable still yields its named groups."""
    if not is_known(processor):
        return None
    found = set(PROCESSOR_OUTPUTS[processor])
    if processor == "URLTextSearcher":
        found.add(str(args.get("result_output_var_name", "match")))
        pattern = resolve(str(args.get("re_pattern", "")))
        found.update(_named_groups(pattern))
    elif processor == "Versioner":
        found.add(str(args.get("output_var_name", "version")))
    elif processor == "PlistReader":
        keys = args.get("plist_keys") or {}
        if isinstance(keys, dict):
            found.update(str(v) for v in keys.values())
    return frozenset(found)


def _named_groups(pattern: str) -> set[str]:
    names, i = set(), 0
    while True:
        i = pattern.find("(?P<", i)
        if i < 0:
            return names
        end = pattern.find(">", i)
        if end < 0:
            return names
        names.add(pattern[i + 4 : end])
        i = end
