#!/bin/bash
#
# clear-autopkg-cache.sh
#
# Clears AutoPkg's own cache directory (~/Library/AutoPkg/Cache/<identifier>/) for
# specific recipe identifiers — and ONLY that directory. This script deliberately
# does not accept an arbitrary path argument; the cache root is hard-coded, and every
# deletion target is verified to resolve to a real path inside that root before
# anything is removed. It cannot touch build/, vendor_cache/, or any repo-relative
# path, regardless of what identifier string is passed in.
#
# Usage:
#   ./clear-autopkg-cache.sh com.acmefruit.autopkg.download.Firefox com.acmefruit.autopkg.pkg.Firefox
#   ./clear-autopkg-cache.sh --dry-run com.acmefruit.autopkg.pkg.Moonlight
#   ./clear-autopkg-cache.sh --all              # clears the entire cache root
#   ./clear-autopkg-cache.sh --all --dry-run    # preview only
#
# Exit codes: 0 done (or nothing to clear), 1 an identifier was refused or could
# not be removed, 2 usage error.
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
set -uo pipefail

# Hard-coded — not a parameter, flag or toolkit variable. This is the entire
# safety model: there is exactly one directory this script will ever touch, the
# current user's AutoPkg cache (HOME decides whose).
CACHE_ROOT="${HOME}/Library/AutoPkg/Cache"

DRY_RUN=0
CLEAR_ALL=0
declare -a IDENTIFIERS=()

for arg in "$@"; do
  case "${arg}" in
    --dry-run) DRY_RUN=1 ;;
    --all) CLEAR_ALL=1 ;;
    -h|--help) sed -n '3,19p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "ERROR: Unknown option: ${arg}" >&2; exit 2 ;;
    *) IDENTIFIERS+=("${arg}") ;;
  esac
done

if [[ ! -d "${CACHE_ROOT}" ]]; then
  echo "Cache root does not exist: ${CACHE_ROOT} — nothing to clear."
  exit 0
fi

# Resolve the real, symlink-free path of the cache root once, as the reference point
# every deletion target gets checked against.
CACHE_ROOT_REAL="$(cd "${CACHE_ROOT}" && pwd -P)"

# Verifies a target path actually resolves to somewhere inside CACHE_ROOT_REAL.
# Returns 1 (refuses) if the target doesn't exist yet (nothing to check against —
# safe by construction, since rm -rf on a nonexistent path is a no-op anyway) or if
# it resolves outside the cache root for any reason (symlink, path traversal, etc).
verify_and_remove() {
  local target="$1"
  if [[ ! -e "${target}" ]]; then
    echo "  (nothing to clear: ${target})"
    return 0
  fi

  local target_real
  target_real="$(cd "$(dirname "${target}")" && pwd -P)/$(basename "${target}")"

  # Strictly inside the cache root: never the root itself (use --all for that).
  case "${target_real}" in
    "${CACHE_ROOT_REAL}"/.|"${CACHE_ROOT_REAL}"/..)
      echo "  REFUSED: '${target}' is not an entry inside ${CACHE_ROOT_REAL}." >&2
      return 1
      ;;
    "${CACHE_ROOT_REAL}"/*)
      : # confirmed inside cache root, safe to proceed
      ;;
    *)
      echo "  REFUSED: '${target}' resolves to '${target_real}', which is outside ${CACHE_ROOT_REAL}. Not touching it." >&2
      return 1
      ;;
  esac

  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "  [DRY RUN] would remove: ${target_real}"
  else
    if rm -rf "${target_real}"; then
      echo "  removed: ${target_real}"
    else
      echo "  FAILED to remove: ${target_real}" >&2
      return 1
    fi
  fi
}

if [[ "${CLEAR_ALL}" -eq 1 ]]; then
  echo "Clearing entire cache root: ${CACHE_ROOT_REAL}"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    echo "[DRY RUN] would remove contents of: ${CACHE_ROOT_REAL}"
    find "${CACHE_ROOT_REAL}" -mindepth 1 -maxdepth 1
  else
    find "${CACHE_ROOT_REAL}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    echo "Cache root emptied."
  fi
  exit 0
fi

if [[ "${#IDENTIFIERS[@]}" -eq 0 ]]; then
  echo "No identifiers given and --all not passed. Nothing to do." >&2
  echo "Usage: $0 <identifier> [<identifier> ...] | --all [--dry-run]" >&2
  exit 1
fi

status=0
for id in "${IDENTIFIERS[@]}"; do
  # Reject anything that isn't a single reverse-DNS-style token
  # (com.acmefruit.autopkg.pkg.AppName). An empty identifier would name the cache
  # root itself, and "." or a path could name something else entirely.
  if [[ -z "${id}" || "${id}" == "." || "${id}" == *"/"* || "${id}" == *".."* ]]; then
    echo "REFUSED: '${id}' is empty, '.', or contains a path separator or '..' — not a valid identifier, skipping." >&2
    status=1
    continue
  fi
  echo "Clearing cache for: ${id}"
  verify_and_remove "${CACHE_ROOT}/${id}" || status=1
done
exit "${status}"
