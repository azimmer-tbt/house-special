#!/bin/bash
#
# apply-screensaver.sh — make Fruit the current user's screensaver, once.
#
# Runs AS THE USER (never root): screensaver choice is a per-user, per-host
# preference (defaults -currentHost). Started two ways:
#   - by the LaunchAgent com.acmefruit.fruit-screensaver at every login, and
#   - by the package's postinstall for whoever is logged in at install time.
#
# Once applied, a marker in the user's Library stops it re-applying, so a user
# who later picks a different screensaver keeps their choice.
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT

set -u

readonly SAVER_PATH="/Library/Screen Savers/Fruit.saver"
readonly MARKER_DIR="${HOME}/Library/Application Support/AcmeFruit"
readonly MARKER="${MARKER_DIR}/.fruit-screensaver-applied"

if [[ "$(id -u)" -eq 0 ]]; then
    echo "apply-screensaver: refusing to run as root; run as the target user" >&2
    exit 1
fi

[[ -e "${MARKER}" ]] && exit 0

if [[ ! -d "${SAVER_PATH}" ]]; then
    echo "apply-screensaver: ${SAVER_PATH} not installed" >&2
    exit 1
fi

/usr/bin/defaults -currentHost write com.apple.screensaver moduleDict \
    -dict moduleName -string "Fruit" \
          path -string "${SAVER_PATH}" \
          type -int 0 || exit 1

/bin/mkdir -p "${MARKER_DIR}" && /usr/bin/touch "${MARKER}"
exit 0
