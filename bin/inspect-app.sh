#!/bin/bash
#
# inspect-app.sh
#
# Extracts metadata from an .app bundle (or any bundle with Info.plist):
# name, identifier, version, build, minimum OS, architectures, code signature.
#
# Usage:
#   bin/inspect-app.sh <path/to/Example.app>                 # text output
#   bin/inspect-app.sh <path/to/Example.app> --output json    # JSON output
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
        -h|--help) sed -n '3,13p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    esac
done

require_macos
tk_python -m recipekit.inspect_tools app "$@"
