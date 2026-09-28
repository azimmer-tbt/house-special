#!/bin/bash
#
# capture-perms.sh
#
# Captures ownership and permissions for every file in a directory tree,
# similar to how lsbom reports BOM contents but for arbitrary trees.
# Useful for comparing payload structures or documenting extracted packages.
#
# Usage:
#   bin/capture-perms.sh /path/to/directory                  # text output
#   bin/capture-perms.sh /path/to/directory --output json     # JSON
#   bin/capture-perms.sh /path --relative                     # relative paths
#
# Spec: specs/analysis/inspect-tools/01-inspect-tools.md
#
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
set -uo pipefail

_CP_BIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=../lib/toolkit-common.sh
. "${_CP_BIN_DIR}/../lib/toolkit-common.sh"

TARGET_DIR=""
OUTPUT_MODE="text"
USE_RELATIVE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output)
            [[ -z "${2:-}" || "$2" == -* ]] && tk_die "--output requires text or json"
            [[ "$2" != "text" && "$2" != "json" ]] && tk_die "--output must be text or json"
            OUTPUT_MODE="$2"; shift 2 ;;
        --relative) USE_RELATIVE=true; shift ;;
        -h|--help)
            sed -n '3,15p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        -*) tk_die "Unknown option: $1" ;;
        *)
            [[ -n "${TARGET_DIR}" ]] && tk_die "Unexpected argument: $1"
            TARGET_DIR="$1"; shift ;;
    esac
done

[[ -z "${TARGET_DIR}" ]] && tk_die "No directory specified. Usage: $(basename "$0") <path> [--output text|json] [--relative]"
[[ -d "${TARGET_DIR}" ]] || tk_die "Not a directory: ${TARGET_DIR}"

TARGET_DIR="$(cd "${TARGET_DIR}" && pwd -P)"

# ── Walk tree ──────────────────────────────────────────────────────────────────

ENTRIES=""
FILE_COUNT=0
DIR_COUNT=0
SYMLINK_COUNT=0

while IFS= read -r -d '' item; do
    ITEM_REL="$(echo "${item}" | sed "s|^${TARGET_DIR}/||; s|^${TARGET_DIR}||")"
    [[ -z "${ITEM_REL}" ]] && continue

    ITEM_TYPE="file"
    SYMLINK_TARGET=""
    if [[ -L "${item}" ]]; then
        ITEM_TYPE="symlink"
        SYMLINK_TARGET="$(readlink "${item}")"
        SYMLINK_COUNT=$((SYMLINK_COUNT + 1))
    elif [[ -d "${item}" ]]; then
        ITEM_TYPE="directory"
        DIR_COUNT=$((DIR_COUNT + 1))
    else
        FILE_COUNT=$((FILE_COUNT + 1))
    fi

    MODE="$(stat -f %Lp "${item}" 2>/dev/null || echo "?")"
    F_UID="$(stat -f %u "${item}" 2>/dev/null || echo "?")"
    F_GID="$(stat -f %g "${item}" 2>/dev/null || echo "?")"
    OWNER="$(stat -f %Su "${item}" 2>/dev/null || echo "?")"
    GROUP="$(stat -f %Sg "${item}" 2>/dev/null || echo "?")"
    SIZE="$(stat -f %z "${item}" 2>/dev/null || echo "0")"

    if ${USE_RELATIVE}; then
        PATH_OUT="${ITEM_REL}"
    else
        PATH_OUT="${item}"
    fi

    ENTRIES="${ENTRIES}${PATH_OUT}|${ITEM_TYPE}|${MODE}|${F_UID}|${F_GID}|${OWNER}|${GROUP}|${SIZE}|${SYMLINK_TARGET}\n"
done < <(find "${TARGET_DIR}" -print0 2>/dev/null)

# ── Output ─────────────────────────────────────────────────────────────────────

if [[ "${OUTPUT_MODE}" == "json" ]]; then
    tk_python -c "
import json

entries_raw = '''$(echo "${ENTRIES}")'''
entries_list = []
for line in entries_raw.strip().split('\\\\n'):
    if not line.strip():
        continue
    parts = line.split('|')
    if len(parts) < 9:
        continue
    entry = {
        'path': parts[0],
        'type': parts[1],
        'mode': parts[2],
        'uid': int(parts[3]) if parts[3] != '?' else 0,
        'gid': int(parts[4]) if parts[4] != '?' else 0,
        'owner': parts[5],
        'group': parts[6],
        'size': int(parts[7]) if parts[7] else 0,
        'symlink_target': parts[8].strip() if parts[1] == 'symlink' else None
    }
    entries_list.append(entry)

output = {
    'root': '${TARGET_DIR}',
    'entries': entries_list,
    'total_entries': len(entries_list),
    'files': ${FILE_COUNT},
    'directories': ${DIR_COUNT},
    'symlinks': ${SYMLINK_COUNT}
}
print(json.dumps(output, indent=2))
"
else
    tk_section "capture-perms.sh"
    echo "  Target:       ${TARGET_DIR}"
    if ${USE_RELATIVE}; then
        echo "  Path style:   relative to target"
    fi
    echo "  Files:        ${FILE_COUNT}"
    echo "  Directories:  ${DIR_COUNT}"
    echo "  Symlinks:     ${SYMLINK_COUNT}"
    echo ""
    echo "  Path | Type | Mode | UID:GID | Owner:Group | Size | SymlinkTarget"
    echo "  ---- | ---- | ---- | ------- | ----------- | ---- | ------------"
    echo -e "${ENTRIES}" | while IFS= read -r line; do
        [[ -z "${line}" ]] && continue
        echo "${line}" | tr '|' ' '
    done
fi
exit 0
