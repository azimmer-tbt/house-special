#!/bin/bash
#
# classify-recipe.sh — Classify a recipe folder by its pattern (docs/patterns.md).
#
# Reads <App>.download.recipe.yaml and <App>.pkg.recipe.yaml, reports the pattern
# label (2b, 4d, 6c, 5, …) with its reasoning, and compares it with the pattern
# the recipe claims in its Comment:. Read-only.
#
# Usage:
#   classify-recipe.sh [--interactive|-i] [--dry-run|-n] [--org <org.yaml>]
#                      [--output text|json] <recipe-dir>
#
# The work is done by the shared recipe model (lib/python/recipekit, module
# recipekit.classify), which runs on AutoPkg's Python. This front end keeps the
# command name and flags (constitution P-10).
#
# Exit codes: 0 classified, 1 no recipe pair in the folder, 2 usage error.
#
# Spec: specs/analysis/classify-recipe/01-classify-recipe.md
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT

set -uo pipefail

_CR_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_CR_BIN_DIR}/../lib/toolkit-common.sh"

tk_python -m recipekit.classify "$@"
