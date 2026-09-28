#!/bin/bash
#
# init-recipe-repo.sh
#
# Creates the directory shape an AutoPkg recipe repo needs for this toolkit to
# operate on it. The repo can live anywhere — the toolkit finds it via --repo or
# $AUTOPKG_TOOLKIT_REPO, and recipes resolve vendor_cache relative to themselves,
# so the toolkit's own location never enters into it.
#
# What it creates:
#   recipes/                  where recipes live, as <Vendor>/<App>/
#   <vendor-cache>/           installers and extracted payloads (NOT tracked)
#   .gitignore                excluding the vendor cache and the usual noise
#   README.md                 a stub explaining the layout
#
# Usage:
#   ./init-recipe-repo.sh ~/Projects/AutoPkg
#   ./init-recipe-repo.sh ~/Projects/AutoPkg --git
#   ./init-recipe-repo.sh ~/Projects/AutoPkg --vendor-cache vendor_cache
#
# The vendor cache defaults to build/vendor_cache, which is the layout
# reference/recipe-standards.md documents for a production repo — its GitHub
# Actions workflow copies installers to that path and the Git LFS plan is pinned
# to it. Use --vendor-cache for a local repo that does not feed that pipeline;
# recipes generated for it will carry the matching path.
#
# Safe to re-run: existing files are left alone, missing ones are created.
#
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
set -uo pipefail

_IR_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_IR_BIN_DIR}/../lib/toolkit-common.sh"

TARGET=""
DO_GIT=false
VENDOR_CACHE="build/vendor_cache"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --git) DO_GIT=true; shift ;;
    --vendor-cache)
      [[ -z "${2:-}" || "$2" == -* ]] && tk_die "--vendor-cache requires a relative path"
      [[ "$2" = /* ]] && tk_die "--vendor-cache must be relative to the repo root, not absolute"
      VENDOR_CACHE="${2%/}"; shift 2 ;;
    -h|--help)
      sed -n '3,22p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    -*) tk_die "Unknown option: $1" ;;
    *)
      [[ -n "${TARGET}" ]] && tk_die "Unexpected argument: $1"
      TARGET="$1"; shift ;;
  esac
done

[[ -z "${TARGET}" ]] && tk_die "Usage: $(basename "$0") <repo-directory> [--git]"

mkdir -p "${TARGET}" || tk_die "Could not create ${TARGET}"
TARGET="$(cd "${TARGET}" && pwd -P)"

tk_section "Initializing recipe repo"
echo "  ${TARGET}"

make_dir() {
  if [[ -d "${TARGET}/$1" ]]; then
    echo "  = $1/ (exists)"
  else
    mkdir -p "${TARGET}/$1" && echo "  + $1/"
  fi
}

make_dir recipes
make_dir "${VENDOR_CACHE}"

# What gets excluded from git is the TOP level of the vendor cache path, so
# --vendor-cache build/vendor_cache ignores build/, and --vendor-cache
# vendor_cache ignores vendor_cache/.
IGNORE_TOP="${VENDOR_CACHE%%/*}"

# ── .gitignore ────────────────────────────────────────────────────────────────
# build/ is working scratch: installers you can re-source and payloads that a
# command re-extracts. Recipes and documentation are what cost thought, and
# those are tracked.

if [[ -f "${TARGET}/.gitignore" ]]; then
  if grep -qE "^${IGNORE_TOP}/?\$" "${TARGET}/.gitignore"; then
    echo "  = .gitignore (already excludes ${IGNORE_TOP}/)"
  else
    printf '\n# Working scratch — installers and extracted payloads.\n# Re-sourced and re-extracted, never version-controlled.\n%s/\n' \
      "${IGNORE_TOP}" >> "${TARGET}/.gitignore"
    echo "  ~ .gitignore (appended ${IGNORE_TOP}/)"
  fi
else
  cat > "${TARGET}/.gitignore" <<EOF
# Working scratch — installers and extracted payloads.
# Re-sourced and re-extracted, never version-controlled.
${IGNORE_TOP}/

# macOS
.DS_Store

# AutoPkg local overrides
*.recipe.yaml.bak
EOF
  echo "  + .gitignore"
fi

# ── README ────────────────────────────────────────────────────────────────────

if [[ -f "${TARGET}/README.md" ]]; then
  echo "  = README.md (exists)"
else
  cat > "${TARGET}/README.md" <<EOF
# AutoPkg Recipes

Recipes for internal software packaging. Tooling lives separately in
**House Special** (\`house-special\`) — clone it anywhere and point it here:

\`\`\`bash
export AUTOPKG_TOOLKIT_REPO=${TARGET}
<toolkit>/bin/recipe-linter.sh
\`\`\`

## Layout

\`\`\`
recipes/<Vendor>/<App>/     recipe pair and README.md (plus .overrides if your pipeline uses one)
${VENDOR_CACHE}/         installers and extracted payloads — NOT tracked
\`\`\`

The nesting matters. Recipes in this repo resolve their installers with

\`\`\`
%RECIPE_DIR%/../../../${VENDOR_CACHE}/<Vendor>/<App>/<file>
\`\`\`

Three levels up from \`recipes/<Vendor>/<App>/\` is this directory. Move a recipe
to a different depth and that path silently breaks at runtime.

Generate recipes for this repo with the matching path:

\`\`\`bash
<toolkit>/bin/blueprint-to-recipe.sh --vendor-cache ${VENDOR_CACHE} ...
\`\`\`

## ${IGNORE_TOP}/ is not tracked

Installers are re-sourced from the vendor; payloads are re-extracted with
\`pkg-reverse.sh\`. Neither costs thought to recreate, so neither is committed.
Recipes and documentation are.

Anyone cloning this repo needs to populate \`${VENDOR_CACHE}/\` themselves
before running a vendor-drop recipe.
EOF
  echo "  + README.md"
fi

# ── git ───────────────────────────────────────────────────────────────────────

if ${DO_GIT}; then
  if [[ -d "${TARGET}/.git" ]]; then
    echo "  = .git (already a repo)"
  elif ! command -v git >/dev/null 2>&1; then
    tk_warn "git not found on PATH — skipping --git"
  else
    # git init defaults to 'master' on older versions; normalize to main.
    # Report failures rather than swallowing them: an unconfigured user.email
    # makes the commit fail, and a silently uncommitted repo is worse than none.
    if ( cd "${TARGET}" && git init -q && git branch -M main 2>/dev/null; ); then
      echo "  + git repo initialized (branch: main)"
      if ( cd "${TARGET}" && git add . && \
           git commit -q -m "Initial commit: recipe repo structure" 2>/dev/null; ); then
        echo "  + initial commit"
      else
        tk_warn "git commit failed — the repo exists but has no commit."
        tk_warn "  Most likely git user.name / user.email are not configured:"
        tk_warn "    git config --global user.name  \"Your Name\""
        tk_warn "    git config --global user.email \"you@example.com\""
        tk_warn "  Then:  cd ${TARGET} && git add . && git commit -m 'Initial commit'"
      fi
    else
      tk_warn "git init failed in ${TARGET} — continuing without version control"
    fi
  fi
fi

# ── Verify ────────────────────────────────────────────────────────────────────
# The toolkit refuses a directory without recipes/, so confirm it now rather
# than letting the first real command fail.

tk_section "Verifying"
if looks_like_recipe_repo "${TARGET}"; then
  echo "  the toolkit will accept this path"
else
  tk_die "Something went wrong — ${TARGET}/recipes was not created."
fi

tk_section "Next"
cat <<EOF
  export AUTOPKG_TOOLKIT_REPO=${TARGET}

  Start a recipe from a template:
    mkdir -p ${TARGET}/recipes/<Vendor>/<App>
    cp ${TOOLKIT_ROOT}/templates/pattern-4-vendor-drop/TEMPLATE.* \\
       ${TARGET}/recipes/<Vendor>/<App>/

  Then fill the REPLACE_ tokens and check your work:
    ${TOOLKIT_ROOT}/bin/scan-placeholders.sh --repo ${TARGET}
    ${TOOLKIT_ROOT}/bin/recipe-linter.sh --repo ${TARGET}
EOF
