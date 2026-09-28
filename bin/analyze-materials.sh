#!/bin/bash
#
# analyze-materials.sh
#
# Deterministic source matcher. Given a directory of vendor materials, scan for
# distributable files (.pkg, .dmg, .zip, .tar.gz, .tgz, .tar.bz2, .tar) and
# match them against target recipes from end_result.yaml.
#
# This is NOT a general-purpose analyzer. It produces structured data that an
# LLM or human interprets. The messy stuff (reading notes, decoding _Vendor
# dirs, interpreting PDFs) belongs to the LLM, not this script.
#
# Usage:
#   bin/analyze-materials.sh <source-dir>                         # scan only
#   bin/analyze-materials.sh <source-dir> --targets end_result.yaml  # matching
#   bin/analyze-materials.sh <source-dir> --output json             # JSON
#   bin/analyze-materials.sh <source-dir> --customer acme           # customer ctx
#
# Spec: specs/analysis/analyze-materials/01-analyze-materials.md
# Implementation: lib/python/recipekit/analyze_materials.py (this file is the front end).
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
set -uo pipefail

_AM_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_AM_BIN_DIR}/../lib/toolkit-common.sh"

for _arg in "$@"; do
    case "${_arg}" in
        -h|--help) sed -n '3,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    esac
done

tk_python -m recipekit.analyze_materials "$@"
