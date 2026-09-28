#!/bin/bash
#
# generate-manifest.sh
#
# Regenerates manifest.sha256 at the root of a RECIPE REPO, covering recipes/ and
# any top-level .md files. Run this any time recipe content changes and needs to be
# handed off — the manifest is what lets the receiving end verify every file landed
# correctly in one command, instead of trusting that a zip extracted cleanly or that
# individual files were all applied.
#
# Scope note: the manifest covers the recipe repo, not the toolkit. The toolkit is
# version-controlled and cloned; the recipes are what move across the assistant/user
# boundary, and moving is where drift happens.
#
# Usage:
#   ./generate-manifest.sh --repo /path/to/recipe-repo
#   AUTOPKG_TOOLKIT_REPO=/path/to/recipe-repo ./generate-manifest.sh
#   cd /path/to/recipe-repo && /path/to/toolkit/bin/generate-manifest.sh
#
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
set -uo pipefail

_GM_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_GM_BIN_DIR}/../lib/toolkit-common.sh"

REPO_ARG=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      [[ -z "${2:-}" || "$2" == -* ]] && tk_die "--repo requires a directory path"
      REPO_ARG="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $(basename "$0") [--repo <recipe-repo>]"
      exit 0 ;;
    *) tk_die "Unknown option: $1" ;;
  esac
done

resolve_repo_root "${REPO_ARG}"
MANIFEST_PATH="${REPO_ROOT}/manifest.sha256"

cd "${REPO_ROOT}" || tk_die "cannot cd to ${REPO_ROOT}"

# NUL-delimited: recipe paths can contain spaces or quotes (plain xargs fails
# on a quote with "unterminated quote" and writes an empty manifest).
find recipes *.md -type f ! -name ".DS_Store" ! -name "manifest.sha256" -print0 2>/dev/null \
  | sort -z \
  | xargs -0 shasum -a 256 > "${MANIFEST_PATH}"

count=$(wc -l < "${MANIFEST_PATH}" | tr -d ' ')
echo "Wrote ${MANIFEST_PATH} covering ${count} files."
echo "Include this file in any handoff — the receiving end runs verify-manifest.sh to confirm everything landed correctly."
