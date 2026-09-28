#!/bin/bash
# normalize-vendor-cache.sh — Normalize vendor cache filenames before autopkg runs
#
# Reads a vendor-drop-registry.yaml from the recipe repo and renames files
# in VENDOR_CACHE_ROOT to their canonical names.
#
# Usage:
#   bin/normalize-vendor-cache.sh \
#     --repo /path/to/recipe-repo \
#     --vendor-cache /tmp/autopkg/vendor_cache [--dry-run] [--relocate-dir <dir>]
#
# Arguments:
#   --repo         Path to the recipe repo root (looks for vendor-drop-registry.yaml here)
#   --vendor-cache Path to the vendor cache directory
#   --dry-run      Report what would change; change nothing
#   --relocate-dir Where stale files go, as <dir>/<Vendor>/<App>/<file>
#                  (default <vendor-cache>/relocated; names are never overwritten)
#
# Only files of the canonical name's type are renamed or pruned; protected files
# are never touched; stale files are moved aside, never deleted.
# Output: ACTION<TAB>VENDOR/APP<TAB>OLD<TAB>NEW<TAB>MESSAGE, one line per action.
#
# Exit codes:
#   0 — All entries processed (warnings OK)
#   1 — Config or vendor-cache not found, bad arguments, or a rename/move failed
#
# Spec: specs/vendor-cache/01-pre-scan-script.md
# Implementation: lib/python/recipekit/vendor_cache.py (this file is the front end).
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
set -uo pipefail

_NV_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_NV_BIN_DIR}/../lib/toolkit-common.sh"

for _arg in "$@"; do
    case "${_arg}" in
        -h|--help) sed -n '2,27p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    esac
done

tk_python -m recipekit.vendor_cache normalize "$@"
