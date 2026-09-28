#!/bin/bash
#
# pkg-compare.sh
#
# Compares an original .pkg against a rebuilt one (from PkgCreator) to confirm
# the two are equivalent in file inventory, permissions, scripts, and metadata.
#
# Reads permissions from each package's BOM (Bill of Materials), NOT from the
# expanded on-disk tree — so this tool does NOT require root/sudo to produce
# correct ownership data.
#
# Usage:
#   ./pkg-compare.sh --old-pkg <original.pkg> --new-pkg <rebuilt.pkg>
#   ./pkg-compare.sh --old-pkg <original.pkg> --new-pkg <rebuilt.pkg> --work-dir /tmp/my-compare
#
# Exit codes:
#   0  All comparisons pass
#   1  File inventory mismatch
#   2  Permission mismatch
#   3  Script mismatch
#   4  (reserved — never emitted; metadata differences are informational)
#   5  Expansion failure
#
# Depends on: pkgutil, lsbom, ditto (all ship with macOS) and AutoPkg's Python.
#
# Implementation: lib/python/recipekit/pkg_compare.py (this file is the front end).
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
set -uo pipefail

_PR_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_PR_BIN_DIR}/../lib/toolkit-common.sh"

for _arg in "$@"; do
  case "${_arg}" in
    -h|--help) sed -n '3,24p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
  esac
done

require_macos
require_command pkgutil "pkgutil ships with macOS; if it is missing, something is very wrong."
require_command lsbom   "lsbom ships with macOS; if it is missing, something is very wrong."

tk_python -m recipekit.pkg_compare "$@"
