#!/bin/bash
#
# scan-placeholders.sh
#
# Lightweight audit tool — no AutoPkg required. Scans every recipe/.overrides file
# under recipes/ for unresolved placeholder values and reports them grouped by app.
# Intended to be run repeatedly as real values get filled in, to track what's left.
#
# Usage:
#   ./scan-placeholders.sh --repo <recipe-repo>
#   ./scan-placeholders.sh --repo <recipe-repo> Moonlight   # substring filter
#
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
set -uo pipefail

_SP_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_SP_BIN_DIR}/../lib/toolkit-common.sh"

REPO_ARG=""
_POSITIONAL=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      [[ -z "${2:-}" || "$2" == -* ]] && tk_die "--repo requires a directory path"
      REPO_ARG="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $(basename "$0") [--repo <recipe-repo>] [filter]"
      exit 0 ;;
    *) _POSITIONAL+=("$1"); shift ;;
  esac
done
set -- "${_POSITIONAL[@]+"${_POSITIONAL[@]}"}"

resolve_repo_root "${REPO_ARG}"
RECIPES_ROOT="$(repo_recipes_dir)"
FILTER="${1:-}"

# Placeholder patterns to detect. Add new ones here as new conventions get introduced.
# UNSIGNED_NO_TEAMID is deliberately absent: it is a decision recorded in a recipe's
# Input (the publisher has no team ID), not a value someone forgot to fill in.
PLACEHOLDER_PATTERN='REPLACE_|TEAMID_[A-Z]+|PENDING|NOT_APPLICABLE_SEE_README|PLACEHOLDER'

total_found=0

while IFS= read -r -d '' app_dir; do
  app_name="$(basename "${app_dir}")"
  vendor_name="$(basename "$(dirname "${app_dir}")")"

  if [[ -n "${FILTER}" && "${app_name}" != *"${FILTER}"* ]]; then
    continue
  fi

  hits="$(grep -rnE "${PLACEHOLDER_PATTERN}" "${app_dir}" --include="*.yaml" --include=".overrides" 2>/dev/null || true)"

  # Structural check: a download recipe that verifies with expected_authority_names
  # must list the full certificate chain, not just the vendor's leaf cert. Missing
  # this caused a real "Mismatch in authority names" failure that only surfaced on
  # first real run. A recipe that verifies with a designated `requirement` has no
  # chain to list, so it is not checked here (KI-28).
  chain_issue=""
  for recipe_file in "${app_dir}"/*.download.recipe.yaml; do
    [[ -f "${recipe_file}" ]] || continue
    if grep -q "Processor: CodeSignatureVerifier" "${recipe_file}" \
        && grep -Eq "^[[:space:]]*expected_authority_names:" "${recipe_file}"; then
      has_ca="$(grep -c "Developer ID Certification Authority" "${recipe_file}" || true)"
      has_root="$(grep -c "Apple Root CA" "${recipe_file}" || true)"
      if [[ "${has_ca}" -eq 0 || "${has_root}" -eq 0 ]]; then
        chain_issue="$(basename "${recipe_file}"): CodeSignatureVerifier present but missing 'Developer ID Certification Authority' and/or 'Apple Root CA' — expected_authority_names likely has only the leaf cert, not the full chain"
      fi
    fi
  done

  if [[ -n "${hits}" || -n "${chain_issue}" ]]; then
    echo ""
    echo "=== ${vendor_name}/${app_name} ==="
    if [[ -n "${hits}" ]]; then
      while IFS= read -r line; do
        file="${line%%:*}"
        rest="${line#*:}"
        linenum="${rest%%:*}"
        content="${rest#*:}"
        echo "  $(basename "${file}"):${linenum}  ${content#"${content%%[![:space:]]*}"}"
        ((total_found++))
      done <<< "${hits}"
    fi
    if [[ -n "${chain_issue}" ]]; then
      echo "  [CHAIN] ${chain_issue}"
      ((total_found++))
    fi
  fi

done < <(find "${RECIPES_ROOT}" -mindepth 2 -maxdepth 2 -type d -print0 | sort -z)

echo ""
echo "=========================================="
if [[ "${total_found}" -eq 0 ]]; then
  echo "No placeholders found."
else
  echo "Total placeholder lines found: ${total_found}"
  echo ""
  echo "Note: PKG_ID values are NOT flagged by this scanner — they're invented"
  echo "identifiers (not vendor-confirmed), a different category than a marked"
  echo "placeholder. Check those by hand if it matters for a given app."
  echo ""
  echo "Note: teamid: UNSIGNED_NO_TEAMID is not flagged. It records on purpose that"
  echo "the publisher has no team ID (ad-hoc signed or unsigned); the recipe's README"
  echo "says why."
fi
echo "=========================================="

[[ "${total_found}" -eq 0 ]]
