#!/bin/bash
#
# check-doc-links.sh — find references in the docs to files that don't exist.
#
# Checks two kinds of reference in Markdown files:
#   - relative links  [text](path)       resolved against the file's own directory
#   - backticked paths `bin/tool.sh`     resolved against the toolkit root, when
#     the path starts with one of the toolkit's top-level directories
#
# Skipped: fenced code blocks, URLs, anchors, and anything that looks like a
# placeholder (<name>, *, %VAR%, {{TOKEN}}, ...). A line that says "(planned"
# may name paths that don't exist yet (specs describe files before they're
# written). Third-party mirrors under reference/autopkg-wiki/ are not checked.
# Backticked mentions of local-only paths (config/customers.yaml, the wiki clone)
# are skipped.
#
# Usage:
#   check-doc-links.sh                 # every tracked-looking .md in the kit
#   check-doc-links.sh --root <dir>    # another tree (tests use this)
#   check-doc-links.sh FILE.md ...     # just these files
#
# Exit codes: 0 all references resolve, 1 broken references, 2 usage error.
# Bash 3.2 compatible; stock macOS tools only.
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT

set -uo pipefail

_CDL_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_CDL_BIN_DIR}/../lib/toolkit-common.sh"

ROOT="${TOOLKIT_ROOT}"
FILES=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --root)
            [[ -n "${2:-}" && "$2" != -* ]] || tk_die "--root requires a directory"
            ROOT="$2"; shift 2 ;;
        -h|--help) sed -n '3,23p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*) tk_die "Unknown option: $1" ;;
        *) FILES+=("$1"); shift ;;
    esac
done
[[ -d "${ROOT}" ]] || tk_die "Not a directory: ${ROOT}"
ROOT="$(cd "${ROOT}" && pwd -P)"

# Top-level directories whose backticked mentions are treated as repo paths.
readonly TOP_DIRS='bin|lib|config|docs|specs|templates|tests|guardrails|reference|customer|\.devagent|\.roo'
# Paths each checkout makes for itself and the kit never ships (gitignored). Docs
# may name them in backticks; a link to one is still reported.
readonly LOCAL_ONLY='config/customers.yaml|reference/autopkg-wiki(/.*)?'

if [[ ${#FILES[@]} -eq 0 ]]; then
    while IFS= read -r f; do FILES+=("${f}"); done < <(
        cd "${ROOT}" && find . \( -path ./.git -o -path ./dist -o -path ./reference/autopkg-wiki \
            -o -path './customer/*/sessions' -o -path './customer/*/troubleshooting' \) -prune \
            -o -type f -name '*.md' -print | sed 's|^\./||' | sort)
fi

# extract_refs <file> — prints "<line>\t<kind>\t<ref>" for each candidate reference.
extract_refs() {
    awk '
        /^[[:space:]]*```/ { fence = !fence; next }
        fence { next }
        tolower($0) ~ /\(planned/ { next }
        {
            line = $0
            # Markdown links: ](target)
            s = line
            while (match(s, /\]\([^)]+\)/)) {
                t = substr(s, RSTART + 2, RLENGTH - 3)
                printf "%d\tlink\t%s\n", NR, t
                s = substr(s, RSTART + RLENGTH)
            }
            # Backticked spans
            s = line
            while (match(s, /`[^`]+`/)) {
                t = substr(s, RSTART + 1, RLENGTH - 2)
                printf "%d\ttick\t%s\n", NR, t
                s = substr(s, RSTART + RLENGTH)
            }
        }' "$1"
}

broken=0
checked=0
for f in "${FILES[@]}"; do
    rel="${f#"${ROOT}"/}"
    abs="${ROOT}/${rel}"
    [[ -f "${abs}" ]] || { tk_warn "no such file: ${f}"; continue; }
    dir="$(dirname "${abs}")"
    while IFS="$(printf '\t')" read -r lineno kind ref; do
        # Strip a title ("…") and an anchor.
        ref="${ref%% \"*}"
        ref="${ref%%#*}"
        [[ -n "${ref}" ]] || continue
        case "${ref}" in
            http://*|https://*|mailto:*|file://*) continue ;;
            *'<'*|*'>'*|*'*'*|*'%'*|*'{'*|*'$'*|*'…'*|*'...'*|*' '*) continue ;;
        esac
        if [[ "${kind}" == "link" ]]; then
            target="${dir}/${ref}"
        else
            # Only backticked strings that look like repo paths.
            [[ "${ref}" =~ ^(${TOP_DIRS})/ ]] || continue
            # Command lines, options and globs are not paths.
            [[ "${ref}" =~ [[:space:]=\|\;] ]] && continue
            [[ "${ref}" =~ ^(${LOCAL_ONLY})$ ]] && continue
            target="${ROOT}/${ref%/}"
        fi
        checked=$((checked + 1))
        if [[ ! -e "${target}" ]]; then
            printf '%s:%s: missing %s\n' "${rel}" "${lineno}" "${ref}"
            broken=$((broken + 1))
        fi
    done < <(extract_refs "${abs}")
done

if [[ "${broken}" -eq 0 ]]; then
    echo "links ok: ${checked} reference(s) in ${#FILES[@]} file(s)"
    exit 0
fi
echo ""
echo "${broken} broken reference(s) (${checked} checked in ${#FILES[@]} file(s))"
exit 1
