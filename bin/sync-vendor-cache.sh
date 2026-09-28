#!/bin/bash
# sync-vendor-cache.sh — Copy only the files listed in an index from
# a source vendor_cache directory to a target vendor_cache directory.
#
# Usage:
#   bin/sync-vendor-cache.sh [--dry-run] <index> <from_dir> <to_dir>
#
# Arguments:
#   index     Path to a YAML file listing files to copy (see
#             customer/acme/output/files_to_copy.yaml
#             for the canonical example).
#   from_dir  Source vendor_cache root (e.g., a populated archive or
#             your recipe repo's vendor_cache on this machine).
#   to_dir    Target vendor_cache root (e.g., /tmp/autopkg/vendor_cache
#             on the test machine).
#
# The index file is a flat YAML list under the `files:` key:
#
#   files:
#     - "Vendor/App/filename.pkg"
#     - "Vendor/App/payload"
#
# Directories are copied recursively (the target folder is replaced). Single
# files are copied individually and skipped when the target has the same size
# and is as new. Timestamps are kept, so an unchanged file isn't copied again.
# Intermediate directories are created as needed. An entry that is absolute or
# contains ".." is refused. --dry-run reports what would be copied.
#
# Exit codes:
#   0 — All entries copied successfully
#   1 — One or more entries failed (missing source, copy error, etc.)
#   2 — Usage error (bad args, missing or empty index)
#
# Spec: specs/vendor-cache/03-sync.md
# Implementation: lib/python/recipekit/vendor_cache.py (this file is the front end).
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT

set -uo pipefail

_SV_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_SV_BIN_DIR}/../lib/toolkit-common.sh"

for _arg in "$@"; do
    case "${_arg}" in
        -h|--help) sed -n '2,36p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    esac
done

tk_python -m recipekit.vendor_cache sync "$@"
