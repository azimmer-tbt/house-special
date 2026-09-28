#!/bin/bash
#
# run-recipes.sh
#
# Local test runner for a recipe repo's recipes. Reads each app's .overrides file and
# invokes real `autopkg run` against both the download and pkg recipes, passing
# override values the same way a CI job would (via --key).
#
# Prerequisites (all macOS-only — this cannot run in a Linux sandbox):
#   1. AutoPkg installed:  brew install autopkg  (or the .pkg installer from github.com/autopkg/autopkg)
#   2. This repo's recipes/ directory added to AutoPkg's search path, so ParentRecipe
#      Identifiers resolve across recipe pairs:
#        defaults write com.github.autopkg RECIPE_SEARCH_DIRS -array-add "/absolute/path/to/recipes"
#   3. build/vendor_cache/<AppName>/... populated with REAL files for whichever apps
#      you're testing — this run will fail (correctly) for any app still holding a
#      REPLACE_* placeholder in its .overrides, since that's not a real value.
#
# Usage:
#   ./run-recipes.sh --repo <recipe-repo>              # run every app
#   ./run-recipes.sh --repo <recipe-repo> Moonlight   # substring filter
#   ./run-recipes.sh --customer acme Moonlight         # that customer's repo
#   ./run-recipes.sh --clear-cache     # wipe each app's cache dir before running
#   ./run-recipes.sh --clear-cache Moonlight   # combine both
#
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
set -uo pipefail

_RR_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_RR_BIN_DIR}/../lib/toolkit-common.sh"

REPO_ARG=""
CUSTOMER_ARG=""
_POSITIONAL=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      [[ -z "${2:-}" || "$2" == -* ]] && tk_die "--repo requires a directory path"
      REPO_ARG="$2"; shift 2 ;;
    --customer)
      [[ -z "${2:-}" || "$2" == -* ]] && tk_die "--customer requires a name"
      CUSTOMER_ARG="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $(basename "$0") [--repo <recipe-repo> | --customer <name>] [filter]"
      exit 0 ;;
    *) _POSITIONAL+=("$1"); shift ;;
  esac
done
set -- "${_POSITIONAL[@]+"${_POSITIONAL[@]}"}"

# A customer (named, from the environment, or the registry default when nothing else
# names a repo) supplies its recipe repo (specs/toolkit/02-customers.md FR-02).
if [[ -n "${CUSTOMER_ARG}" || -n "${AUTOPKG_TOOLKIT_CUSTOMER:-}" ]]; then
  resolve_customer "${CUSTOMER_ARG}" || exit 2
  [[ -n "${REPO_ARG}" || -n "${AUTOPKG_TOOLKIT_REPO:-}" ]] || REPO_ARG="${CUSTOMER_REPO}"
elif [[ -z "${REPO_ARG}" && -z "${AUTOPKG_TOOLKIT_REPO:-}" ]] \
    && ! looks_like_recipe_repo "$(pwd -P)" && has_customer_registry; then
  resolve_customer "" || exit 2
  REPO_ARG="${CUSTOMER_REPO}"
fi

resolve_repo_root "${REPO_ARG}"
RECIPES_ROOT="$(repo_recipes_dir)"
FILTER=""
CLEAR_CACHE=0

for arg in "$@"; do
  case "${arg}" in
    --clear-cache) CLEAR_CACHE=1 ;;
    *) FILTER="${arg}" ;;
  esac
done

if ! command -v autopkg >/dev/null 2>&1; then
  echo "ERROR: autopkg not found on PATH. Install it first (brew install autopkg)." >&2
  exit 1
fi

pass_count=0
fail_count=0
skip_count=0
declare -a failures=()
declare -a skips=()

# Find every app dir (one level under VendorName/) that has a .download.recipe.yaml
while IFS= read -r -d '' download_recipe; do
  app_dir="$(dirname "${download_recipe}")"
  app_name="$(basename "${app_dir}")"
  vendor_name="$(basename "$(dirname "${app_dir}")")"

  if [[ -n "${FILTER}" && "${app_name}" != *"${FILTER}"* ]]; then
    continue
  fi

  pkg_recipe="${app_dir}/${app_name}.pkg.recipe.yaml"
  overrides_file="${app_dir}/.overrides"

  echo ""
  echo "=== ${vendor_name}/${app_name} ==="

  if [[ ! -f "${pkg_recipe}" ]]; then
    echo "  SKIP: no matching pkg recipe found at ${pkg_recipe}"
    skips+=("${vendor_name}/${app_name}: missing pkg recipe")
    ((skip_count++))
    continue
  fi

  # Build --key=Key=Value args from .overrides, if present. Flags any REPLACE_* /
  # placeholder-looking value loudly rather than silently feeding it to autopkg.
  override_args=()
  has_placeholder=0
  if [[ -f "${overrides_file}" ]]; then
    # "|| [[ -n ... ]]" keeps a last line that has no trailing newline.
    while IFS='=' read -r key value || [[ -n "${key}" ]]; do
      [[ -z "${key}" ]] && continue
      [[ "${key}" == \#* ]] && continue
      if [[ "${value}" == REPLACE* || "${value}" == *"PENDING"* || "${value}" == "TEAMID_"* ]]; then
        echo "  WARNING: ${key}=${value} looks like an unresolved placeholder"
        has_placeholder=1
      fi
      override_args+=("--key=${key}=${value}")
    done < "${overrides_file}"
  fi

  if [[ "${has_placeholder}" -eq 1 ]]; then
    echo "  SKIP: unresolved placeholder(s) in .overrides — fix before running for real"
    skips+=("${vendor_name}/${app_name}: unresolved .overrides placeholder(s)")
    ((skip_count++))
    continue
  fi

  if [[ "${CLEAR_CACHE}" -eq 1 ]]; then
    download_id="$(grep "^Identifier:" "${download_recipe}" | head -1 | sed -E 's/^Identifier: *//; s/^["'"'"']//; s/["'"'"'] *$//')"
    pkg_id="$(grep "^Identifier:" "${pkg_recipe}" | head -1 | sed -E 's/^Identifier: *//; s/^["'"'"']//; s/["'"'"'] *$//')"
    "${TOOLKIT_BIN_DIR}/clear-autopkg-cache.sh" "${download_id}" "${pkg_id}"
  fi

  echo "  Running download recipe..."
  if ! autopkg run "${download_recipe}" ${override_args[@]+"${override_args[@]}"} -v; then
    echo "  FAIL: download recipe"
    failures+=("${vendor_name}/${app_name}: download recipe failed")
    ((fail_count++))
    continue
  fi

  echo "  Running pkg recipe..."
  if ! autopkg run "${pkg_recipe}" ${override_args[@]+"${override_args[@]}"} -v; then
    echo "  FAIL: pkg recipe"
    failures+=("${vendor_name}/${app_name}: pkg recipe failed")
    ((fail_count++))
    continue
  fi

  echo "  PASS"
  ((pass_count++))

done < <(find "${RECIPES_ROOT}" -type f -name "*.download.recipe.yaml" -print0 | sort -z)

echo ""
echo "=========================================="
echo "Results: ${pass_count} passed, ${fail_count} failed, ${skip_count} skipped"
echo "=========================================="

if [[ "${#failures[@]}" -gt 0 ]]; then
  echo ""
  echo "Failures:"
  printf '  - %s\n' "${failures[@]}"
fi

if [[ "${#skips[@]}" -gt 0 ]]; then
  echo ""
  echo "Skipped:"
  printf '  - %s\n' "${skips[@]}"
fi

[[ "${fail_count}" -eq 0 ]]
