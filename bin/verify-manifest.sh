#!/bin/bash
#
# verify-manifest.sh
#
# Verifies every file listed in manifest.sha256 (at repo root) matches its expected
# content exactly. Run this after extracting any handoff zip or applying any set of
# individual file changes, BEFORE running autopkg against anything — this is the
# single command that replaces "I think everything landed correctly."
#
# Usage:
#   ./verify-manifest.sh [--repo <recipe-repo>] [--strict]
#
# --strict additionally reports files present on disk under recipes/ that are NOT
# listed in the manifest. Without it, drift in the "someone added a file" direction
# is invisible -- the manifest only ever checks what it already knows about.
#
# Exit code 0 = every file verified. Non-zero = at least one mismatch or missing file
# (or, under --strict, at least one unlisted file).
#
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
set -uo pipefail

_VM_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_VM_BIN_DIR}/../lib/toolkit-common.sh"

REPO_ARG=""
STRICT=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      [[ -z "${2:-}" || "$2" == -* ]] && tk_die "--repo requires a directory path"
      REPO_ARG="$2"; shift 2 ;;
    --strict) STRICT=true; shift ;;
    -h|--help)
      echo "Usage: $(basename "$0") [--repo <recipe-repo>] [--strict]"
      exit 0 ;;
    *) tk_die "Unknown option: $1" ;;
  esac
done

resolve_repo_root "${REPO_ARG}"
MANIFEST_PATH="${REPO_ROOT}/manifest.sha256"

cd "${REPO_ROOT}"

if [[ ! -f "${MANIFEST_PATH}" ]]; then
  echo "ERROR: manifest.sha256 not found at ${REPO_ROOT}. Nothing to verify against." >&2
  exit 1
fi

ok_count=0
fail_count=0
missing_count=0
declare -a failures=()
declare -a missing=()

while IFS= read -r line; do
  [[ -z "${line}" ]] && continue
  expected_hash="${line%%  *}"
  filepath="${line#*  }"

  if [[ ! -f "${filepath}" ]]; then
    missing+=("${filepath}")
    ((missing_count++))
    continue
  fi

  actual_hash="$(shasum -a 256 "${filepath}" | awk '{print $1}')"
  if [[ "${actual_hash}" == "${expected_hash}" ]]; then
    ((ok_count++))
  else
    failures+=("${filepath}")
    ((fail_count++))
  fi
done < "${MANIFEST_PATH}"

unlisted_count=0
declare -a unlisted=()
if ${STRICT}; then
  while IFS= read -r ondisk; do
    if ! grep -qF "  ${ondisk}" "${MANIFEST_PATH}"; then
      unlisted+=("${ondisk}")
      unlisted_count=$((unlisted_count + 1))
    fi
  done < <(find recipes *.md -type f ! -name ".DS_Store" ! -name "manifest.sha256" 2>/dev/null | sort)
fi

echo ""
echo "=========================================="
if ${STRICT}; then
  echo "Verified: ${ok_count} OK, ${fail_count} MISMATCH, ${missing_count} MISSING, ${unlisted_count} UNLISTED"
else
  echo "Verified: ${ok_count} OK, ${fail_count} MISMATCH, ${missing_count} MISSING"
fi
echo "=========================================="

if [[ "${#failures[@]}" -gt 0 ]]; then
  echo ""
  echo "MISMATCHED (file exists but content differs from manifest):"
  printf '  - %s\n' "${failures[@]}"
fi

if [[ "${#missing[@]}" -gt 0 ]]; then
  echo ""
  echo "MISSING (listed in manifest but not found on disk):"
  printf '  - %s\n' "${missing[@]}"
fi

if [[ "${#unlisted[@]}" -gt 0 ]]; then
  echo ""
  echo "UNLISTED (present on disk but absent from the manifest):"
  printf '  - %s\n' "${unlisted[@]}"
  echo "  Regenerate with generate-manifest.sh if these are intentional."
fi

if [[ "${fail_count}" -eq 0 && "${missing_count}" -eq 0 && "${unlisted_count}" -eq 0 ]]; then
  echo ""
  echo "All files verified. Safe to proceed."
fi

[[ "${fail_count}" -eq 0 && "${missing_count}" -eq 0 && "${unlisted_count}" -eq 0 ]]
