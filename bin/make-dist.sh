#!/bin/bash
#
# make-dist.sh
#
# Builds a distribution copy of this toolkit — all FUNCTION, none of the
# development scaffolding. Copies files into a new directory; it does not
# reconfigure, rewrite, or transform anything it copies.
#
# Ships:      bin/ lib/ config/ (incl. org.yaml) guardrails/ templates/ docs/
#             reference/methodology.md reference/recipe-standards.md
#             README.md LICENSE NOTICE CONTRIBUTING.md requirements.txt
# Excluded:   .git/ tests/ specs/ customer/ BUGFIX.md PROGRESS.md .leak-patterns
#             bin/make-dist.sh, any venv, reference/autopkg-wiki/ (unless
#             --with-wiki), .devagent/ .roo/ .clinerules AGENT_GREETING.md
#             (unless --with-devagent)
#
# Usage:
#   ./make-dist.sh                          # -> dist/house-special/
#   ./make-dist.sh --out /tmp/kit           # explicit output directory
#   ./make-dist.sh --with-wiki              # include the AutoPkg wiki mirror
#   ./make-dist.sh --with-devagent          # include agent rules/skills
#   ./make-dist.sh --tar                    # also produce a .tar.gz
#
# Exit 0 on success, non-zero if the smoke test fails.
#
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
set -uo pipefail

_MD_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_MD_BIN_DIR}/../lib/toolkit-common.sh"

OUT_DIR=""
WITH_WIKI=false
WITH_DEVAGENT=false
MAKE_TAR=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)
      [[ -z "${2:-}" || "$2" == -* ]] && tk_die "--out requires a directory path"
      OUT_DIR="$2"; shift 2 ;;
    --with-wiki)     WITH_WIKI=true; shift ;;
    --with-devagent) WITH_DEVAGENT=true; shift ;;
    --tar)           MAKE_TAR=true; shift ;;
    -h|--help)
      echo "Usage: $(basename "$0") [--out <dir>] [--with-wiki] [--with-devagent] [--tar]"
      exit 0 ;;
    *) tk_die "Unknown option: $1" ;;
  esac
done

DIST_NAME="house-special"
if [[ -z "${OUT_DIR}" ]]; then
  OUT_DIR="${TOOLKIT_ROOT}/dist/${DIST_NAME}"
fi

tk_section "Building distribution"
echo "  source: ${TOOLKIT_ROOT}"
echo "  output: ${OUT_DIR}"

if [[ -e "${OUT_DIR}" ]]; then
  tk_die "Output path already exists: ${OUT_DIR} (remove it or pass --out elsewhere)"
fi

mkdir -p "${OUT_DIR}" || tk_die "Could not create ${OUT_DIR}"

# ── Copy ──────────────────────────────────────────────────────────────────────
# -L dereferences symlinks so a corp checkout can never inherit a broken link
# pointing at a path that does not exist on that machine.

copy_tree() {
  local rel="$1"
  if [[ ! -e "${TOOLKIT_ROOT}/${rel}" ]]; then
    tk_warn "skipping ${rel} (not present in source)"
    return 0
  fi
  mkdir -p "$(dirname "${OUT_DIR}/${rel}")"
  cp -RL "${TOOLKIT_ROOT}/${rel}" "${OUT_DIR}/${rel}"
  echo "  + ${rel}"
}

tk_section "Copying function"
copy_tree "bin"
copy_tree "lib"
copy_tree "config"
copy_tree "guardrails"
copy_tree "templates"

mkdir -p "${OUT_DIR}/reference"
copy_tree "reference/methodology.md"
copy_tree "reference/recipe-standards.md"

copy_tree "docs"

for f in README.md LICENSE LICENSE.md NOTICE CONTRIBUTING.md requirements.txt; do
  [[ -f "${TOOLKIT_ROOT}/${f}" ]] && copy_tree "${f}"
done

# make-dist itself is a development tool, not function. A dist copy that can
# re-dist itself invites confusion about which tree is canonical.
rm -f "${OUT_DIR}/bin/make-dist.sh"
# Local virtualenvs are machine-specific; never ship one.
rm -rf "${OUT_DIR}/bin/venv" "${OUT_DIR}/.venv"

if ${WITH_WIKI}; then
  tk_section "Including wiki (--with-wiki)"
  copy_tree "reference/autopkg-wiki"
fi

if ${WITH_DEVAGENT}; then
  tk_section "Including agent scaffolding (--with-devagent)"
  copy_tree ".devagent"
  copy_tree ".clinerules"
  copy_tree "AGENT_GREETING.md"
  mkdir -p "${OUT_DIR}/.roo"
  cp -RL "${TOOLKIT_ROOT}/.devagent/rules" "${OUT_DIR}/.roo/rules"
  echo "  + .roo/rules (dereferenced)"
fi

find "${OUT_DIR}" -name '.DS_Store' -delete 2>/dev/null || true
find "${OUT_DIR}" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

# ── Provenance ────────────────────────────────────────────────────────────────
# A dist copy has no git history. Without this, nobody downstream can tell what
# they have or how stale it is.

tk_section "Stamping provenance"
SRC_COMMIT="$(cd "${TOOLKIT_ROOT}" && git rev-parse --short HEAD 2>/dev/null || echo unknown)"
SRC_BRANCH="$(cd "${TOOLKIT_ROOT}" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
SRC_DIRTY=""
if ! (cd "${TOOLKIT_ROOT}" && git diff --quiet HEAD 2>/dev/null); then
  SRC_DIRTY=" (working tree had uncommitted changes)"
fi

cat > "${OUT_DIR}/PROVENANCE.md" <<PROVEOF
# Provenance

This is a distribution build of **House Special** — function only,
development scaffolding removed.

| Field | Value |
|-------|-------|
| Built | $(date -u '+%Y-%m-%d %H:%M UTC') |
| Source commit | \`${SRC_COMMIT}\`${SRC_DIRTY} |
| Source branch | \`${SRC_BRANCH}\` |
| Wiki included | ${WITH_WIKI} |
| Agent scaffolding included | ${WITH_DEVAGENT} |

## What is not here

Development scaffolding was excluded by design: \`tests/\` (shellspec suite),
\`specs/\` (spec documents), \`customer/\` (the worked example),
\`BUGFIX.md\`, \`PROGRESS.md\`, and git history. The tools are fully
functional without them; documentation links into \`specs/\` or
\`customer/acme/\` point at the source repository.

If \`reference/autopkg-wiki/\` is absent, that is expected — it is excluded
unless built with \`--with-wiki\`. Documentation that references
\`reference/autopkg-wiki/Processor-<Name>.md\` describes an optional resource,
not a broken path.

To modify or extend this toolkit, work in the source repository rather than
here — this copy has no tests to verify a change against.
PROVEOF
echo "  + PROVENANCE.md (${SRC_COMMIT}${SRC_DIRTY})"

# ── Manifest ──────────────────────────────────────────────────────────────────
# A dist tarball is precisely the handoff case the manifest exists for.

tk_section "Generating manifest"
# NUL-delimited end to end: shipped filenames can contain spaces and quotes,
# which plain xargs rejects ("unterminated quote") and silently yields an
# empty manifest.
( cd "${OUT_DIR}" \
    && find . -type f ! -name '.DS_Store' ! -name 'manifest.sha256' -print0 \
       | sort -z | xargs -0 shasum -a 256 | sed 's|  \./|  |' > manifest.sha256 )
MANIFEST_COUNT="$(wc -l < "${OUT_DIR}/manifest.sha256" | tr -d ' ')"
SHIPPED_COUNT="$(find "${OUT_DIR}" -type f ! -name '.DS_Store' ! -name 'manifest.sha256' | wc -l | tr -d ' ')"
if [[ "${MANIFEST_COUNT}" -ne "${SHIPPED_COUNT}" ]]; then
  tk_die "manifest lists ${MANIFEST_COUNT} files but ${SHIPPED_COUNT} were shipped"
fi
echo "  + manifest.sha256 (${MANIFEST_COUNT} files)"

# ── Smoke test ────────────────────────────────────────────────────────────────
# An allowlist copy silently omits any runtime file added later. This catches
# that class at build time rather than on someone else's machine.

tk_section "Smoke test"
# Don't paper over missing exec bits with chmod: a front end that isn't
# executable here isn't executable in the source either.
NOT_EXEC="$(find "${OUT_DIR}/bin" -maxdepth 1 -type f \( -name '*.sh' -o -name '*.py' \) ! -perm -u+x)"
if [[ -n "${NOT_EXEC}" ]]; then
  tk_err "[FAIL] front ends without the exec bit:"
  tk_err "${NOT_EXEC}"
  exit 1
fi
echo "  [PASS] every bin/ front end is executable"

if "${OUT_DIR}/bin/recipe-linter.sh" --list-rules >/dev/null 2>&1; then
  echo "  [PASS] recipe-linter.sh --list-rules"
else
  tk_err "[FAIL] recipe-linter.sh --list-rules failed in the dist copy."
  tk_err "       A runtime file is probably missing from the copy allowlist above."
  tk_err "       Diagnose with: ${OUT_DIR}/bin/recipe-linter.sh --list-rules"
  exit 1
fi

if "${OUT_DIR}/bin/analyze-package.sh" --help >/dev/null 2>&1; then
  echo "  [PASS] analyze-package.sh --help"
else
  tk_err "[FAIL] analyze-package.sh --help failed in the dist copy."
  tk_err "       The script or its library (lib/toolkit-common.sh) is missing."
  exit 1
fi

# Analyzers without --output json (verify basic function without a .pkg file)
if "${OUT_DIR}/bin/inspect-app.sh" --help >/dev/null 2>&1; then
  echo "  [PASS] inspect-app.sh --help"
else
  tk_err "[FAIL] inspect-app.sh --help"
  exit 1
fi

if "${OUT_DIR}/bin/inspect-archive.sh" --help >/dev/null 2>&1; then
  echo "  [PASS] inspect-archive.sh --help"
else
  tk_err "[FAIL] inspect-archive.sh --help"
  exit 1
fi

if "${OUT_DIR}/bin/capture-perms.sh" --help >/dev/null 2>&1; then
  echo "  [PASS] capture-perms.sh --help"
else
  tk_err "[FAIL] capture-perms.sh --help"
  exit 1
fi

# A shipped template example must pass the shipped linter with the shipped config.
SMOKE_EXAMPLE="${OUT_DIR}/templates/pattern-4-vendor-drop/example-Xerox-Drivers"
if "${OUT_DIR}/bin/recipe-linter.sh" --dir "${SMOKE_EXAMPLE}" --pair-check >/dev/null 2>&1; then
  echo "  [PASS] recipe-linter.sh lints a shipped template example clean"
else
  tk_err "[FAIL] recipe-linter.sh failed on ${SMOKE_EXAMPLE}"
  exit 1
fi

# verify docs/ exists and has content
DOC_COUNT=$(find "${OUT_DIR}/docs" -name '*.md' -type f 2>/dev/null | wc -l | tr -d ' ')
if [[ "${DOC_COUNT}" -ge 1 ]]; then
  echo "  [PASS] docs/ (${DOC_COUNT} files)"
else
  tk_err "[FAIL] docs/ is empty or missing"
  exit 1
fi

# ── Optional tarball ──────────────────────────────────────────────────────────

if ${MAKE_TAR}; then
  tk_section "Creating tarball"
  TAR_PATH="$(cd "$(dirname "${OUT_DIR}")" && pwd -P)/${DIST_NAME}.tar.gz"
  ( cd "$(dirname "${OUT_DIR}")" && tar czf "${TAR_PATH}" "$(basename "${OUT_DIR}")" )
  echo "  + ${TAR_PATH}"
fi

tk_section "Done"
echo "  ${OUT_DIR}"
