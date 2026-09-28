#!/bin/bash
#
# blueprint-to-recipe.sh
#
# Generates a first-draft Pattern 4 recipe pair from a blueprint.conf produced by
# pkg-reverse.sh. Output is a DRAFT — it has never been run. Review it, then run
# bin/autopkg-preflight.py and a real `autopkg run` before trusting it.
#
# Usage:
#   ./blueprint-to-recipe.sh --blueprint <path/blueprint.conf> --out <recipe-dir>
#   ./blueprint-to-recipe.sh --blueprint <path> --out <dir> --vendor "Company Name"
#   ./blueprint-to-recipe.sh --blueprint <path> --out <dir> --vendor-cache vendor_cache
#   ./blueprint-to-recipe.sh --blueprint <path> --out <dir> --org <org.yaml>
#
# Identifiers and the pkgname prefix come from config/org.yaml (or --org /
# $AUTOPKG_TOOLKIT_ORG) — see read_org_config in lib/toolkit-common.sh.
#
# --vendor-cache is the vendor cache path RELATIVE TO THE RECIPE REPO ROOT, and
# must match how that repo is laid out. Defaults to build/vendor_cache, the
# layout reference/recipe-standards.md documents for a production repo. A local
# repo created with `init-recipe-repo.sh --vendor-cache vendor_cache` needs the
# same value here, or the generated recipe will point at a path that does not
# exist.
#
# Writes into <recipe-dir>:
#   <AppName>.download.recipe.yaml
#   <AppName>.pkg.recipe.yaml
#   README.md
#
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
set -uo pipefail

_BR_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_BR_BIN_DIR}/../lib/toolkit-common.sh"

BLUEPRINT=""
OUT_DIR=""
VENDOR=""
VENDOR_CACHE="build/vendor_cache"
ORG_FILE=""
FORCE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --blueprint)
      [[ -z "${2:-}" || "$2" == -* ]] && tk_die "--blueprint requires a path"
      BLUEPRINT="$2"; shift 2 ;;
    --out)
      [[ -z "${2:-}" || "$2" == -* ]] && tk_die "--out requires a directory path"
      OUT_DIR="$2"; shift 2 ;;
    --vendor)
      [[ -z "${2:-}" || "$2" == -* ]] && tk_die "--vendor requires a value"
      VENDOR="$2"; shift 2 ;;
    --vendor-cache)
      [[ -z "${2:-}" || "$2" == -* ]] && tk_die "--vendor-cache requires a relative path"
      [[ "$2" = /* ]] && tk_die "--vendor-cache must be relative to the repo root, not absolute"
      VENDOR_CACHE="${2%/}"; shift 2 ;;
    --org)
      [[ -z "${2:-}" || "$2" == -* ]] && tk_die "--org requires a path"
      ORG_FILE="$2"; shift 2 ;;
    --force) FORCE=true; shift ;;
    -h|--help)
      sed -n '3,24p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) tk_die "Unknown option: $1" ;;
  esac
done

[[ -z "${BLUEPRINT}" ]] && tk_die "--blueprint is required"
[[ -z "${OUT_DIR}"   ]] && tk_die "--out is required"
[[ -f "${BLUEPRINT}" ]] || tk_die "Blueprint not found: ${BLUEPRINT}"
read_org_config "${ORG_FILE}" || exit 2

# ── Read blueprint ────────────────────────────────────────────────────────────
# Deliberately not `source`d — a blueprint is data, and sourcing it would execute
# whatever is in it.

bp() {
  awk -F'=' -v k="$1" '
    /^#/ { next }
    $1 == k { sub(/^[^=]*=/, ""); print; exit }
  ' "${BLUEPRINT}"
}

APP_NAME="$(bp app_name)"
PKG_ID="$(bp pkg_id)"
VERSION="$(bp version)"
INSTALL_LOCATION="$(bp install_location)"
SIG_STATUS="$(bp signature_status)"
SIG_AUTHORITY="$(bp signature_authority)"
SOURCE_PKG_BASENAME="$(bp source_pkg_basename)"
SCRIPTS="$(bp scripts)"
CHOWN_NEEDED="$(bp chown_block_needed)"
PAYLOAD_FILES="$(bp payload_files)"

[[ -z "${APP_NAME}" ]] && tk_die "Blueprint has no app_name — is ${BLUEPRINT} a real blueprint?"

# Pattern 6 letter (docs/patterns.md): 6d no payload, 6b payload + scripts, 6a payload only.
if [[ "${PAYLOAD_FILES:-0}" == "0" ]]; then
  PATTERN="6d"
  PATTERN_NOTE="rebuilt payloadless (script-only) package"
elif [[ -n "${SCRIPTS// /}" ]]; then
  PATTERN="6b"
  PATTERN_NOTE="rebuilt package, payload plus install scripts"
else
  PATTERN="6a"
  PATTERN_NOTE="rebuilt package, flat payload"
fi

tk_section "Generating draft recipe for ${APP_NAME}"

MISSING=""
[[ -z "${PKG_ID}"  ]] && MISSING="${MISSING} pkg_id"
[[ -z "${VERSION}" ]] && MISSING="${MISSING} version"
if [[ -n "${MISSING}" ]]; then
  tk_warn "Blueprint is missing:${MISSING}"
  tk_warn "REPLACE_ placeholders will be emitted; bin/scan-placeholders.sh will find them."
  [[ -z "${PKG_ID}"  ]] && PKG_ID="REPLACE_PKG_ID"
  [[ -z "${VERSION}" ]] && VERSION="REPLACE_VERSION"
fi
[[ -z "${VENDOR}" ]] && VENDOR="REPLACE_VENDOR"

[[ -e "${OUT_DIR}" && "${FORCE}" == "false" ]] && \
  tk_die "Output directory exists: ${OUT_DIR} (pass --force to write into it anyway)"
mkdir -p "${OUT_DIR}" || tk_die "Could not create ${OUT_DIR}"

SIG_NOTE=""
if [[ "${SIG_STATUS}" == "signed" ]]; then
  SIG_NOTE="#
# WARNING: the source package was SIGNED by:
#   ${SIG_AUTHORITY}
# Rebuilding discards that signature. If you did not build this package
# yourself, stop and use PkgCopier on the original instead (Pattern 4 Variant A,
# see templates/pattern-4-vendor-drop/)."
fi

# ── download recipe ───────────────────────────────────────────────────────────

{
cat <<EOF
# ─────────────────────────────────────────────────────────────────────────────
# DRAFT — generated by blueprint-to-recipe.sh. Never run. Review before use.
#
# Reverse-engineered from ${SOURCE_PKG_BASENAME} (${PAYLOAD_FILES} files).
# The payload tree under vendor_cache is the source of truth; the original .pkg
# is only a reference.${SIG_NOTE}
# ─────────────────────────────────────────────────────────────────────────────
Comment: Pattern ${PATTERN} — ${PATTERN_NOTE}; payload reverse-engineered from an existing package with pkg-reverse.sh.
Description: Stages the ${APP_NAME} payload from vendor_cache.
Identifier: ${ORG_IDENTIFIER_PREFIX}.download.${APP_NAME}
MinimumVersion: "2.3"

Input:
  NAME: ${APP_NAME}
  # Pinned from the original package; nothing in the payload reports a version.
  # The pkg recipe inherits it. Bump it with each new drop.
  version: "${VERSION}"

  # No CodeSignatureVerifier: this package is rebuilt from an extracted payload,
  # so there is no vendor signature left to verify. The trust boundary is that
  # the source package came from inside the org.
  NO_CODE_SIGNATURE_REQUIRED: true

  LOCAL_DIR_PATH: "%RECIPE_DIR%/../../../${VENDOR_CACHE}/${VENDOR}/${APP_NAME}/payload"
EOF

if [[ -n "${SCRIPTS// /}" ]]; then
cat <<EOF
  LOCAL_SCRIPTS_PATH: "%RECIPE_DIR%/../../../${VENDOR_CACHE}/${VENDOR}/${APP_NAME}/scripts"
EOF
fi

cat <<'EOF'

Process:
  # overwrite: true is required — Copier fails with [Errno 17] File exists on a
  # second run against a populated cache when copying a directory.
  - Processor: Copier
    Arguments:
      source_path: "%LOCAL_DIR_PATH%"
      destination_path: "%RECIPE_CACHE_DIR%/payload"
      overwrite: true
EOF

if [[ -n "${SCRIPTS// /}" ]]; then
cat <<EOF

  # The pkg recipe hands %RECIPE_CACHE_DIR%/scripts to PkgCreator, so the
  # scripts have to be staged into the cache here alongside the payload.
  # Extracted scripts: ${SCRIPTS% }
  - Processor: Copier
    Arguments:
      source_path: "%LOCAL_SCRIPTS_PATH%"
      destination_path: "%RECIPE_CACHE_DIR%/scripts"
      overwrite: true
EOF
fi

cat <<'EOF'

  - Processor: EndOfCheckPhase
EOF
} > "${OUT_DIR}/${APP_NAME}.download.recipe.yaml"

# ── pkg recipe ────────────────────────────────────────────────────────────────

{
cat <<EOF
# ─────────────────────────────────────────────────────────────────────────────
# DRAFT — generated by blueprint-to-recipe.sh. Never run. Review before use.
#
# Rebuilds ${APP_NAME} from the extracted payload with PkgCreator.
#
# install-location from the original package: ${INSTALL_LOCATION}
# If that is not "/", the payload tree must be rooted to match it — PkgCreator
# has no install-location argument, so the path structure inside pkgroot IS the
# install location. Verify with:  pkgutil --files ${PKG_ID}
# ─────────────────────────────────────────────────────────────────────────────
Comment: Pattern ${PATTERN} — ${PATTERN_NOTE}. PkgCreator rebuilds it from the staged payload with the org's naming.
Description: Rebuilds ${APP_NAME} with ${ORG_NAME} naming convention.
Identifier: ${ORG_IDENTIFIER_PREFIX}.pkg.${APP_NAME}
ParentRecipe: ${ORG_IDENTIFIER_PREFIX}.download.${APP_NAME}
MinimumVersion: "2.3"

Input:
  NAME: ${APP_NAME}
  PKG_ID: ${PKG_ID}

Process:
  - Processor: PkgCreator
    Arguments:
      pkg_request:
        pkgroot: "%RECIPE_CACHE_DIR%/payload"
        pkgname: "${ORG_PKGNAME_PREFIX}%NAME%"
        pkgdir: "%RECIPE_CACHE_DIR%"
        id: "%PKG_ID%"
        version: "%version%"
EOF

if [[ -n "${SCRIPTS// /}" ]]; then
cat <<EOF
        # Scripts extracted from the original package: ${SCRIPTS% }
        # PkgCreator rejects the build if preinstall/postinstall are not
        # executable; pkg-reverse.sh sets that bit, and git preserves it.
        scripts: "%RECIPE_CACHE_DIR%/scripts"
EOF
fi

if [[ "${CHOWN_NEEDED}" == "true" ]]; then
cat <<'EOF'
        # The payload was extracted WITHOUT root, so on-disk ownership is wrong
        # and must be restored here. Entries below are rolled up per directory —
        # PkgCreator's chown walks the tree, so one entry covers everything
        # beneath it.
        #
        # Do NOT add a "mode" key to a rollup entry unless the whole subtree
        # shares one mode: PkgCreator applies the same octal mode to every child,
        # files and directories alike, which makes directories non-traversable or
        # files executable. Per-path entries are the safe way to set a mode.
        #
        # Source: chown-entries.txt beside the blueprint. Fill these in.
        chown:
          - path: REPLACE_PATH
            user: root
            group: wheel
EOF
else
cat <<'EOF'
        # No chown block: the payload was extracted as root, so ownership is
        # correct on disk and PkgCreator's ditto carries it into the build.
EOF
fi
} > "${OUT_DIR}/${APP_NAME}.pkg.recipe.yaml"

# ── README ──────────────────────────────────────────────────────────────────────

cat > "${OUT_DIR}/README.md" <<EOF
# ${APP_NAME}

Reverse-engineered from an existing package with \`bin/pkg-reverse.sh\`.
**This recipe is a draft and has not been run.**

## Origin

| Field | Value |
|-------|-------|
| Source package | \`${SOURCE_PKG_BASENAME}\` |
| Identifier | \`${PKG_ID}\` |
| Version | ${VERSION} |
| install-location | \`${INSTALL_LOCATION}\` |
| Signature | ${SIG_STATUS}${SIG_AUTHORITY:+ — ${SIG_AUTHORITY}} |
| Payload | ${PAYLOAD_FILES} files |
| Scripts | ${SCRIPTS:-none} |

Source files for this package were not available; the payload was extracted from
a built package rather than rebuilt from source.

## Before trusting this

1. Compare against the original: \`pkgutil --files ${PKG_ID}\`
2. Confirm install-location — PkgCreator has no install-location argument, so the
   structure inside \`pkgroot\` **is** the install location. If the original was
   not \`/\`, the payload tree must be rooted to match.
3. Read any extracted scripts. They may reference paths, receipts, or versions
   that no longer hold.
4. \`bin/autopkg-preflight.py --app <this directory>\`
5. \`autopkg run ./${APP_NAME}.pkg.recipe.yaml\`
6. Install the result on a test Mac and compare against the original's receipt.

## Known gaps

- No signature. The rebuilt package is unsigned regardless of the original.
- A Distribution wrapper, if the original had one, is not reproduced — install
  choices, requirements, and any JavaScript are gone.
- Version is pinned in the download recipe's \`Input\`; there is nothing to detect a new one.
EOF

tk_section "Done"
echo "  ${OUT_DIR}/"
for f in "${APP_NAME}.download.recipe.yaml" "${APP_NAME}.pkg.recipe.yaml" README.md; do
  echo "    ${f}"
done
echo ""
echo "  This is a DRAFT. Next:"
echo "    bin/scan-placeholders.sh --repo <repo> ${APP_NAME}"
echo "    bin/recipe-linter.sh --dir ${OUT_DIR}"
echo "    bin/autopkg-preflight.py --app ${OUT_DIR}"
