#!/bin/bash
#
# inspect-archive.sh
#
# Lists the contents of a compressed archive (.zip, .tar.gz, .tgz, .tar.bz2, .tar)
# without full extraction. For .zip, also shows per-file compression info.
#
# Usage:
#   bin/inspect-archive.sh <archive.zip>                            # text output
#   bin/inspect-archive.sh <archive.tar.gz> --output json           # JSON
#   bin/inspect-archive.sh <archive.zip> --max-entries 50           # limit output
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
        -h|--help) sed -n '3,14p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    esac
done

require_macos
tk_python -m recipekit.inspect_tools archive "$@"
