#!/bin/bash
#
# pkg-reverse.sh
#
# Explodes an existing flat .pkg into a working tree plus a blueprint file, so a
# first-draft AutoPkg recipe can be generated from it by blueprint-to-recipe.sh.
#
# For in-house packages whose source files are gone. NOT for vendor packages you
# could ship as-is: rebuilding discards the original signature. If the input is
# signed by someone else, Pattern 4 Variant A (PkgCopier) is the right answer and
# this tool is the wrong one.
#
# Ownership: run under sudo. pkgutil extracts as the invoking user, so without
# sudo every file comes out owned by you and the rebuilt package installs with
# the wrong ownership. This script reads the package's BOM either way and tells
# you whether the extracted tree matches it.
#
# Usage:
#   sudo ./pkg-reverse.sh <package.pkg> --dest <vendor-cache-dir> [--name <AppName>]
#   ./pkg-reverse.sh <package.pkg> --dest <dir> --allow-unprivileged
#
# Outputs, under <dest>/<AppName>/:
#   payload/        the package root, ready to hand to PkgCreator
#   scripts/        preinstall/postinstall, executable bits preserved
#   blueprint.conf  what was found; input to blueprint-to-recipe.sh
#   bom.txt         lsbom -p mugsfl: mode, uid, gid, size, path, link (tab-separated)
#   chown-entries.txt  without root only: OWN<TAB><path><TAB><uid>:<gid>, parent first
#
# Implementation: lib/python/recipekit/pkg_reverse.py (this file is the front end).
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
set -uo pipefail

_PR_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_PR_BIN_DIR}/../lib/toolkit-common.sh"

for _arg in "$@"; do
  case "${_arg}" in
    -h|--help) sed -n '3,27p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
  esac
done

require_macos
require_command pkgutil "pkgutil ships with macOS; if it is missing, something is very wrong."
require_command lsbom   "lsbom ships with macOS; if it is missing, something is very wrong."

tk_python -m recipekit.pkg_reverse "$@"
