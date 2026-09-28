#!/bin/bash
#
# check-sanitized.sh — scan the toolkit tree for content that must not ship.
#
# This kit is an upstream that orgs fork. Forks accumulate org-specific data
# (names, identifiers, paths, tickets); this guard stops that data flowing back
# upstream, and stops a fork's own secrets leaking into commits.
#
# Usage:
#   check-sanitized.sh                     # scan the whole toolkit tree
#   check-sanitized.sh --path docs --path bin
#   check-sanitized.sh --staged            # only files staged for commit
#   check-sanitized.sh --install-hook      # add a git pre-commit hook
#
# Options:
#   --root <dir>        Tree to scan (default: the toolkit root)
#   --path <rel>        Limit the scan to this path under --root (repeatable)
#   --staged            Scan only files in `git diff --cached`
#   --patterns <file>   Denylist file (default: <root>/.leak-patterns)
#   --customer <name>   Scan that customer's folder (config/customers.yaml) with
#                       the kit's denylist and every *other* customer's
#   --all-customers     Scan each registered customer's folder in turn
#   --allow <rel>       Exempt a file from the denylist patterns (repeatable).
#                       LICENSE and NOTICE are always exempt (they name the
#                       copyright holder).
#   --max-kb <n>        Flag files larger than n KB (default: 1024)
#   --install-hook      Write .git/hooks/pre-commit to run `--staged`
#   -h, --help          Show this help
#
# The denylist (.leak-patterns) is one extended regex per line; blank lines and
# lines starting with # are ignored. A line starting with ! is an exemption
# instead: a denylist hit on a line that also matches it is not reported (e.g.
# the maintainer's own "# Author:" line in script headers). It is gitignored on
# purpose: a committed denylist would itself leak every name it lists. Each fork
# keeps its own.
#
# Built-in checks run whether or not a denylist exists:
#   - home-directory paths (/Users/<name>, except generic placeholders)
#   - change/incident ticket numbers (CHG, RITM, INC, CTASK + 6 or more digits)
#   - "Serial Number" followed by a value
#   - OneDrive tenant sync-folder paths (OneDrive-<Org>)
#   - files larger than --max-kb
#   - installer/archive binaries (.pkg .mpkg .dmg .zip) outside tests/fixtures
#
# Customers (specs/toolkit/02-customers.md): when a registry exists, each
# customer's own .leak-patterns applies everywhere except inside that customer's
# folder. A customer's names may appear only in its own folder.
#
# Always skipped: .git/, every .leak-patterns file, and reference/autopkg-wiki/
# (a third-party mirror whose pages legitimately contain example paths).
#
# Exit codes: 0 clean, 1 findings, 2 usage error.
#
# Bash 3.2 compatible; uses only stock macOS tools.
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT

set -uo pipefail

_CS_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_CS_BIN_DIR}/../lib/toolkit-common.sh"

GREP=/usr/bin/grep
[[ -x "${GREP}" ]] || GREP="grep"

ROOT="${TOOLKIT_ROOT}"
PATTERNS_FILE=""
STAGED=false
INSTALL_HOOK=false
MAX_KB=1024
SCAN_PATHS=()
ALLOW=("LICENSE" "NOTICE")
SCAN_CUSTOMER=""
ALL_CUSTOMERS=false
ROOT_GIVEN=false
LINE_ALLOW=()   # "!<ere>" lines from the denylist file

# Generic placeholder home directories that are fine in docs and examples.
readonly HOME_PLACEHOLDERS='^/Users/((Shared|you|your[-_]?user|YourUser|user|username|USERNAME|USER|me|myself|example|name|jappleseed|admin)$|[][$<{(.*…])'

usage() {
    sed -n '3,54p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --root)
            [[ -n "${2:-}" && "$2" != -* ]] || tk_die "--root requires a directory"
            ROOT="$2"; ROOT_GIVEN=true; shift 2 ;;
        --customer)
            [[ -n "${2:-}" && "$2" != -* ]] || tk_die "--customer requires a name"
            SCAN_CUSTOMER="$2"; shift 2 ;;
        --all-customers) ALL_CUSTOMERS=true; shift ;;
        --path)
            [[ -n "${2:-}" && "$2" != -* ]] || tk_die "--path requires a relative path"
            SCAN_PATHS+=("${2%/}"); shift 2 ;;
        --patterns)
            [[ -n "${2:-}" && "$2" != -* ]] || tk_die "--patterns requires a file"
            PATTERNS_FILE="$2"; shift 2 ;;
        --allow)
            [[ -n "${2:-}" && "$2" != -* ]] || tk_die "--allow requires a relative path"
            ALLOW+=("${2#./}"); shift 2 ;;
        --max-kb)
            [[ "${2:-}" =~ ^[0-9]+$ ]] || tk_die "--max-kb requires a number"
            MAX_KB="$2"; shift 2 ;;
        --staged)       STAGED=true; shift ;;
        --install-hook) INSTALL_HOOK=true; shift ;;
        -h|--help)      usage; exit 0 ;;
        *)              tk_die "Unknown option: $1 (see --help)" ;;
    esac
done

# ── Customers ─────────────────────────────────────────────────────────────────
if ${ALL_CUSTOMERS}; then
    has_customer_registry || tk_die "--all-customers: no customer registry"
    customers_tsv="$(tk_python -m recipekit.customers list --output tsv)" || exit 2
    worst=0
    while IFS=$'\t' read -r c_name _; do
        [[ -n "${c_name}" ]] || continue
        echo "=== Customer: ${c_name}"
        "${BASH_SOURCE[0]}" --customer "${c_name}" --max-kb "${MAX_KB}" \
            ${PATTERNS_FILE:+--patterns "${PATTERNS_FILE}"}
        rc=$?
        [[ "${rc}" -gt "${worst}" ]] && worst="${rc}"
    done <<< "${customers_tsv}"
    exit "${worst}"
fi
if [[ -n "${SCAN_CUSTOMER}" ]]; then
    resolve_customer "${SCAN_CUSTOMER}" || exit 2
    ${ROOT_GIVEN} || ROOT="${CUSTOMER_ROOT}"
    # The kit maintainer's denylist applies to customer folders too.
    [[ -n "${PATTERNS_FILE}" ]] || PATTERNS_FILE="${TOOLKIT_ROOT}/.leak-patterns"
fi

[[ -d "${ROOT}" ]] || tk_die "Not a directory: ${ROOT}"
ROOT="$(cd "${ROOT}" && pwd -P)"
[[ -n "${PATTERNS_FILE}" ]] || PATTERNS_FILE="${ROOT}/.leak-patterns"

# ── --install-hook ────────────────────────────────────────────────────────────
if ${INSTALL_HOOK}; then
    hook_dir="$(git -C "${ROOT}" rev-parse --git-path hooks 2>/dev/null)" \
        || tk_die "${ROOT} is not a git repository"
    [[ "${hook_dir}" = /* ]] || hook_dir="${ROOT}/${hook_dir}"
    hook="${hook_dir}/pre-commit"
    if [[ -e "${hook}" ]]; then
        tk_die "${hook} already exists — add this line to it instead:
  \"\$(git rev-parse --show-toplevel)/bin/check-sanitized.sh\" --staged || exit 1"
    fi
    mkdir -p "${hook_dir}"
    cat > "${hook}" <<'HOOK'
#!/bin/bash
# Installed by bin/check-sanitized.sh --install-hook
exec "$(git rev-parse --show-toplevel)/bin/check-sanitized.sh" --staged
HOOK
    chmod +x "${hook}"
    echo "Installed ${hook}"
    exit 0
fi

# ── Collect files ─────────────────────────────────────────────────────────────
FILE_LIST="$(mktemp -t check-sanitized)"
HITS="$(mktemp -t check-sanitized-hits)"
trap 'rm -f "${FILE_LIST}" "${HITS}"' EXIT

is_skipped() {
    case "$1" in
        .git|.git/*|.leak-patterns|*/.leak-patterns|reference/autopkg-wiki/*) return 0 ;;
    esac
    [[ "${ROOT}/$1" == "${PATTERNS_FILE}" ]]
}

if ${STAGED}; then
    git -C "${ROOT}" rev-parse --git-dir >/dev/null 2>&1 \
        || tk_die "--staged needs a git repository at ${ROOT}"
    git -C "${ROOT}" diff --cached --name-only --diff-filter=ACMR > "${FILE_LIST}.raw"
else
    if [[ ${#SCAN_PATHS[@]} -eq 0 ]]; then
        SCAN_PATHS=(".")
    fi
    : > "${FILE_LIST}.raw"
    for p in "${SCAN_PATHS[@]}"; do
        [[ -e "${ROOT}/${p}" ]] || { tk_warn "no such path: ${p}"; continue; }
        (cd "${ROOT}" && find "${p}" -type f -not -path '*/.git/*' -not -path './.git/*' -print) \
            | sed 's|^\./||' >> "${FILE_LIST}.raw"
    done
fi

# Filter in the current shell (not a pipeline subshell) so skipped_wiki survives.
skipped_wiki=false
: > "${FILE_LIST}.kept"
while IFS= read -r f; do
    [[ -n "${f}" ]] || continue
    if is_skipped "${f}"; then
        case "${f}" in reference/autopkg-wiki/*) skipped_wiki=true ;; esac
        continue
    fi
    [[ -f "${ROOT}/${f}" ]] && printf '%s\n' "${f}" >> "${FILE_LIST}.kept"
done < "${FILE_LIST}.raw"
sort -u "${FILE_LIST}.kept" > "${FILE_LIST}"
rm -f "${FILE_LIST}.raw" "${FILE_LIST}.kept"

${skipped_wiki} && echo "skipped: reference/autopkg-wiki (third-party mirror)"
file_count="$(wc -l < "${FILE_LIST}" | tr -d ' ')"

# ── Checks ────────────────────────────────────────────────────────────────────

# record <label> <file> <line> <excerpt>
record() {
    local excerpt="$4"
    [[ ${#excerpt} -gt 100 ]] && excerpt="${excerpt:0:100}…"
    printf '%s:%s: [%s] %s\n' "$2" "$3" "$1" "${excerpt}" >> "${HITS}"
}

is_allowed() {
    local a
    for a in "${ALLOW[@]}"; do
        [[ "$1" == "${a}" ]] && return 0
    done
    return 1
}

line_allowed() {
    local a
    [[ ${#LINE_ALLOW[@]} -gt 0 ]] || return 1
    for a in "${LINE_ALLOW[@]}"; do
        printf '%s\n' "$1" | "${GREP}" -qE -e "${a}" && return 0
    done
    return 1
}

# grep_files <label> <ere> [allow]
# Runs one grep across every collected file; "allow" skips --allow files and
# lines matching a "!" exemption.
grep_files() {
    local label="$1" re="$2" use_allow="${3:-}" exclude="${4:-}" f line text
    [[ "${file_count}" -gt 0 ]] || return 0
    (cd "${ROOT}" && tr '\n' '\0' < "${FILE_LIST}" \
        | xargs -0 "${GREP}" -nHIE -e "${re}" -- 2>/dev/null) \
    | while IFS= read -r hit; do
        f="${hit%%:*}"; hit="${hit#*:}"
        line="${hit%%:*}"; text="${hit#*:}"
        [[ -n "${exclude}" && "${f}" == "${exclude}/"* ]] && continue
        if [[ -n "${use_allow}" ]]; then
            is_allowed "${f}" && continue
            line_allowed "${text}" && continue
        fi
        record "${label}" "${f}" "${line}" "${text}"
    done
}

# Home-directory paths: find candidates, then drop generic placeholders.
[[ "${file_count}" -gt 0 ]] && \
(cd "${ROOT}" && tr '\n' '\0' < "${FILE_LIST}" \
    | xargs -0 "${GREP}" -nHIoE -e '/Users/[^/[:space:]"'"'"'`)]+' -- 2>/dev/null) \
| while IFS= read -r hit; do
    f="${hit%%:*}"; hit="${hit#*:}"
    line="${hit%%:*}"; path="${hit#*:}"
    # Sentence punctuation after a placeholder ("/Users/you.") is still a placeholder.
    bare="$(printf '%s\n' "${path}" | sed 's/[.,;:!?]*$//')"
    printf '%s\n' "${bare}" | "${GREP}" -qE "${HOME_PLACEHOLDERS}" && continue
    record "home-path" "${f}" "${line}" "${path}"
done

grep_files "ticket"     '(^|[^A-Za-z0-9])(CHG|RITM|INC|CTASK)[0-9]{6,}'
grep_files "serial"     '[Ss]erial [Nn]umber[-: ]+[A-Z0-9-]{6,}'
grep_files "onedrive"   'One''Drive-[A-Z]'   # tenant sync folders (OneDrive-<Org>); split so this line doesn't match itself

# Size and binary-type checks.
while IFS= read -r f; do
    kb="$(( ($(stat -f%z "${ROOT}/${f}") + 1023) / 1024 ))"
    [[ "${kb}" -gt "${MAX_KB}" ]] && record "large-file" "${f}" 0 "${kb} KB > ${MAX_KB} KB"
    case "${f}" in
        tests/fixtures/*) ;;
        *.pkg|*.mpkg|*.dmg|*.zip) record "binary" "${f}" 0 "installer/archive file" ;;
    esac
done < "${FILE_LIST}"

# Denylist.
pattern_count=0
if [[ -f "${PATTERNS_FILE}" ]]; then
    while IFS= read -r pat || [[ -n "${pat}" ]]; do
        case "${pat}" in '!'?*) LINE_ALLOW+=("${pat#!}") ;; esac
    done < "${PATTERNS_FILE}"
    while IFS= read -r pat || [[ -n "${pat}" ]]; do
        case "${pat}" in ''|'#'*|'!'*) continue ;; esac
        pattern_count=$((pattern_count + 1))
        grep_files "denylist:${pattern_count}" "${pat}" allow
    done < "${PATTERNS_FILE}"
else
    echo "note: no denylist at ${PATTERNS_FILE#"${ROOT}/"} — built-in checks only"
fi

# Customers' denylists: each applies everywhere but its own customer's folder.
customer_pattern_count=0
if has_customer_registry; then
    customers_tsv="$(tk_python -m recipekit.customers list --output tsv)" || exit 2
    while IFS=$'\t' read -r c_name c_root c_leak; do
        [[ -n "${c_leak}" && -f "${c_leak}" ]] || continue
        [[ "${c_name}" == "${CUSTOMER_NAME}" ]] && continue   # scanning its own folder
        own=""
        [[ -d "${c_root}" ]] && c_root="$(cd "${c_root}" && pwd -P)"
        case "${c_root}/" in "${ROOT}/"*) own="${c_root#"${ROOT}/"}" ;; esac
        while IFS= read -r pat || [[ -n "${pat}" ]]; do
            case "${pat}" in '!'?*) LINE_ALLOW+=("${pat#!}") ;; esac
        done < "${c_leak}"
        n=0
        while IFS= read -r pat || [[ -n "${pat}" ]]; do
            case "${pat}" in ''|'#'*|'!'*) continue ;; esac
            n=$((n + 1))
            customer_pattern_count=$((customer_pattern_count + 1))
            grep_files "customer:${c_name}:${n}" "${pat}" allow "${own}"
        done < "${c_leak}"
    done <<< "${customers_tsv}"
    pattern_count=$((pattern_count + customer_pattern_count))
fi

# ── Report ────────────────────────────────────────────────────────────────────
hit_count="$(wc -l < "${HITS}" | tr -d ' ')"
if [[ "${hit_count}" -eq 0 ]]; then
    echo "clean: ${file_count} file(s) scanned, ${pattern_count} denylist pattern(s)"
    exit 0
fi

sort -t: -k1,1 -k2,2n "${HITS}"
hit_files="$(cut -d: -f1 "${HITS}" | sort -u | wc -l | tr -d ' ')"
echo ""
echo "${hit_count} finding(s) in ${hit_files} file(s) (${file_count} scanned, ${pattern_count} denylist pattern(s))"
echo "denylist:N = line N of the non-comment patterns in ${PATTERNS_FILE#"${ROOT}/"}"
[[ "${customer_pattern_count}" -gt 0 ]] \
    && echo "customer:NAME:N = line N of that customer's .leak-patterns"
exit 1
