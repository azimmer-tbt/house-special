#!/bin/bash
# rr-batch.sh — Batch wrapper for Recipe Robot
# Runs recipe-robot against a CSV of URLs and app names, and files the recipes
# it writes into a recipe repo, renamed to the CSV's app names.
#
# Input file format (one per line, no smart quotes):
#   "status","vendor","appname","url"
#
# Usage:
#   rr-batch.sh -i <input.csv> --log-dir <log_dir> [-o <output_dir>] [options]
#
# Options:
#   -i, --input <file>     Input CSV file (required)
#   --log-dir <dir>        Directory for logs (required)
#   -o, --output-dir <dir> Base output directory (default: current directory);
#                          recipes go to <dir>/recipes/<Vendor>/<AppName>/
#   -e, --ignore-existing  Pass --ignore-existing to Recipe Robot
#   -v, --verbose          Pass --verbose to Recipe Robot
#   --vendor <name>        Override vendor for all entries (ignores CSV Vendor column)
#   -l, --lint             Run the linter on the generated recipes afterwards
#   --config <path>        Linter checks.yaml path (default: config/checks.yaml)
#   --org <path>           Org naming file (default: config/org.yaml or $AUTOPKG_TOOLKIT_ORG)
#   --force                Overwrite existing recipe files in the output directory
#   -h, --help             Show this help
#
# Status column values: TEST (process if no output dir), DONE (skip),
# SKIP (skip), blank (always process).
#
# Each recipe Recipe Robot reports writing is copied to
# <AppName>.{download,pkg}.recipe.yaml with NAME, Identifier and ParentRecipe
# set from the org prefix and the CSV AppName. Recipe Robot's own output is
# left in place. Set Recipe Robot to YAML output first (recipe-robot --config).
#
# Exit codes: 0 all passed, 1 a Recipe Robot run failed, 2 usage or config
# error, or the linter could not run.
#
# Spec: specs/rr-batch/01-batch-definitions.md
# Implementation: lib/python/recipekit/rr_batch.py (this file is the front end).
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
set -uo pipefail

_BATCH_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_BATCH_BIN_DIR}/../lib/toolkit-common.sh"

for _arg in "$@"; do
    case "${_arg}" in
        -h|--help) sed -n '2,35p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    esac
done

tk_python -m recipekit.rr_batch "$@"
