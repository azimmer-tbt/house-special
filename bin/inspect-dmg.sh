#!/bin/bash
#
# inspect-dmg.sh
#
# Mounts a .dmg file (read-only), captures its tree structure,
# finds the .app bundles (not helpers inside them), extracts identifier,
# version, build and architectures from each, then unmounts. A DMG that asks
# to accept a license agreement is not mounted: mount it by hand.
#
# Usage:
#   bin/inspect-dmg.sh <file.dmg>                         # text output
#   bin/inspect-dmg.sh <file.dmg> --output json            # JSON output
#   bin/inspect-dmg.sh <file.dmg> --keep-mounted           # leave mounted
#
# Spec: specs/analysis/inspect-tools/01-inspect-tools.md
# Implementation: lib/python/recipekit/inspect_tools.py (this file is the front end).
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
set -uo pipefail

_IT_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_IT_BIN_DIR}/../lib/toolkit-common.sh"

for _arg in "$@"; do
    case "${_arg}" in
        -h|--help) sed -n '3,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    esac
done

require_macos
tk_python -m recipekit.inspect_tools dmg "$@"
