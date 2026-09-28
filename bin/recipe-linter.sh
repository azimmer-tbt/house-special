#!/bin/bash
#
# recipe-linter.sh — AutoPkg YAML recipe linter (config-driven).
#
# Validates .recipe.yaml files against the rules in config/checks.yaml; no rule
# logic is in code.
#
# Usage:
#   recipe-linter.sh <recipe-file.yaml> [recipe-file.yaml ...]
#   recipe-linter.sh --dir <recipe-directory> [--pair-check]
#   recipe-linter.sh --repo <recipe-repo> [--pair-check]   # lints <repo>/recipes
#   recipe-linter.sh --config <path>                       # alternate checks.yaml
#   recipe-linter.sh --org <path>                          # alternate org.yaml
#   recipe-linter.sh --customer <name>                     # a customer (config/customers.yaml)
#   recipe-linter.sh --all-customers [--pair-check]        # each customer in turn
#   recipe-linter.sh --list-rules
#   recipe-linter.sh --help
#
# The engine is recipekit.lint (lib/python/recipekit/lint.py) on AutoPkg's Python.
# In CI without AutoPkg, set AUTOPKG_TOOLKIT_PYTHON to a Python 3.10+ with PyYAML.
#
# Exit codes: 0 all checks passed, 1 lint errors or warnings, 2 usage or config error.
#
# Specs: specs/recipe-linter/ (00-constitution.md §6 covers the runtime).
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT

set -uo pipefail

_LINTER_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_LINTER_BIN_DIR}/../lib/toolkit-common.sh"

tk_python -m recipekit.lint "$@"
