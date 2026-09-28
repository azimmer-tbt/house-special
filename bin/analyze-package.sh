#!/bin/bash
#
# analyze-package.sh
#
# Classifies a .pkg file as vendor-originated or custom-built, identifies the
# recipe pattern it matches, and outputs structured metadata.
#
# Usage:
#   bin/analyze-package.sh <package.pkg>                         # text output
#   bin/analyze-package.sh <package.pkg> --output json           # JSON output
#   bin/analyze-package.sh <package.pkg> --clues clues.yaml      # custom heuristics
#   bin/analyze-package.sh <package.pkg> --customer acme         # customer clues
#
# Exit codes:
#   0  Classification determined (confidence high or medium)
#   1  Classification completed but confidence is low
#   2  Usage error, missing file, invalid config, or extraction failure
#
# Spec: specs/analysis/analyze-package/01-analyze-package.md
# Implementation: lib/python/recipekit/analyze_package.py (this file is the front end).
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
set -uo pipefail

_AP_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_AP_BIN_DIR}/../lib/toolkit-common.sh"

for _arg in "$@"; do
    case "${_arg}" in
        -h|--help) sed -n '3,15p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    esac
done

require_macos
require_command pkgutil "pkgutil ships with macOS."

tk_python -m recipekit.analyze_package "$@"
