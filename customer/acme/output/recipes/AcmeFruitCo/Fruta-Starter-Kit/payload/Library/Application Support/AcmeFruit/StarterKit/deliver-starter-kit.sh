#!/bin/bash
#
# deliver-starter-kit.sh — put the new-hire developer starter kit on the
# current user's Desktop, once.
#
# Runs AS THE USER (never root), so the copy is owned by them. Started two ways:
#   - by the package's postinstall, once for every existing account, and
#   - by the LaunchAgent com.acmefruit.starter-kit at login, which covers
#     accounts created after the install.
#
# A marker in the user's Library stops re-delivery: someone who deletes the
# tarball from their Desktop does not get it back at every login.
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT

set -u

readonly KIT="/Library/Application Support/AcmeFruit/StarterKit/Fruta-StarterKit.tar.gz"
readonly MARKER_DIR="${HOME}/Library/Application Support/AcmeFruit"
readonly MARKER="${MARKER_DIR}/.starter-kit-delivered"

if [[ "$(id -u)" -eq 0 ]]; then
    echo "deliver-starter-kit: refusing to run as root; run as the target user" >&2
    exit 1
fi

[[ -e "${MARKER}" ]] && exit 0

if [[ ! -f "${KIT}" ]]; then
    echo "deliver-starter-kit: ${KIT} missing" >&2
    exit 1
fi

/bin/mkdir -p "${HOME}/Desktop" || exit 1
/bin/cp "${KIT}" "${HOME}/Desktop/" || exit 1
/bin/mkdir -p "${MARKER_DIR}" && /usr/bin/touch "${MARKER}"
exit 0
