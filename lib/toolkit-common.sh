#!/bin/bash
#
# toolkit-common.sh
#
# Shared library for every House Special frontend. Sourced, never
# executed directly.
#
# THE FRONTEND CONTRACT
# ---------------------
# Toolkit assets resolve from the script's own location. Work targets resolve
# from --repo. The current working directory is never load-bearing.
#
#   TOOLKIT_ROOT  where config/, guardrails/, reference/ live. Derived from
#                 this library's own path. Not overridable, never guessed.
#   REPO_ROOT     the AutoPkg recipe repo being operated on. Resolved from
#                 --repo, then $AUTOPKG_TOOLKIT_REPO, then the CWD but only
#                 if it actually looks like a recipe repo.
#
# Every frontend that touches a recipe repo must call resolve_repo_root before
# doing any work. Frontends that touch nothing outside the toolkit (or that
# are deliberately repo-independent, like clear-autopkg-cache.sh) must not.
#
# Compatible with bash 3.2 — the stock macOS bash. No associative arrays, no
# mapfile, no ${var,,}. See specs/recipe-linter/00-constitution.md section 6.
#
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
set -uo pipefail

# ── Toolkit root ──────────────────────────────────────────────────────────────
# This file lives at $TOOLKIT_ROOT/lib/toolkit-common.sh, so the toolkit root is
# one level up. Resolved physically (-P) so a symlinked bin/ entry still lands
# in the right place.
_TOOLKIT_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
TOOLKIT_ROOT="$(cd "${_TOOLKIT_LIB_DIR}/.." && pwd -P)"
readonly TOOLKIT_ROOT

# Canonical toolkit asset paths. Frontends reference these rather than building
# their own relative paths.
TOOLKIT_CONFIG_DIR="${TOOLKIT_ROOT}/config"
TOOLKIT_DEFAULT_CHECKS="${TOOLKIT_CONFIG_DIR}/checks.yaml"
TOOLKIT_GUARDRAILS_DIR="${TOOLKIT_ROOT}/guardrails"
TOOLKIT_AUDIT_DIR="${TOOLKIT_GUARDRAILS_DIR}/audit"
TOOLKIT_REFERENCE_DIR="${TOOLKIT_ROOT}/reference"
TOOLKIT_WIKI_DIR="${TOOLKIT_REFERENCE_DIR}/autopkg-wiki"
TOOLKIT_BIN_DIR="${TOOLKIT_ROOT}/bin"
readonly TOOLKIT_CONFIG_DIR TOOLKIT_DEFAULT_CHECKS TOOLKIT_GUARDRAILS_DIR
readonly TOOLKIT_AUDIT_DIR TOOLKIT_REFERENCE_DIR TOOLKIT_WIKI_DIR TOOLKIT_BIN_DIR

# REPO_ROOT is set by resolve_repo_root. Declared here so `set -u` doesn't trip
# on frontends that reference it before resolution.
REPO_ROOT=""

# ── Logging ───────────────────────────────────────────────────────────────────

tk_err() {
    echo "ERROR: $*" >&2
}

tk_warn() {
    echo "WARN:  $*" >&2
}

tk_info() {
    echo "$*" >&2
}

# Section marker for pasteable command sequences. Comments break when a block is
# pasted into a shell; echoed markers do not.
tk_section() {
    echo "=== $* ==="
}

tk_die() {
    tk_err "$@"
    exit 2
}

# ── Repo resolution ───────────────────────────────────────────────────────────

# looks_like_recipe_repo <dir>
#
# A recipe repo is identified by containing a recipes/ directory. This is the
# same signal AutoPkg's own layout conventions use, and the same one
# autopkg-preflight.py keys on.
#
# Inputs:  $1 -- candidate directory
# Outputs: exit 0 if it looks like a recipe repo, 1 otherwise
# has_customer_registry — true if a customer registry exists.
has_customer_registry() {
    [[ -f "${AUTOPKG_TOOLKIT_CUSTOMERS:-${TOOLKIT_CONFIG_DIR}/customers.yaml}" ]]
}

looks_like_recipe_repo() {
    local candidate="$1"
    [[ -n "${candidate}" && -d "${candidate}/recipes" ]]
}

# resolve_repo_root <explicit_repo_arg>
#
# Resolves REPO_ROOT following the precedence in the frontend contract:
#   1. --repo (passed in as $1; empty string if the flag was not given)
#   2. $AUTOPKG_TOOLKIT_REPO
#   3. the current working directory, but ONLY if it contains recipes/
#
# An explicit --repo or $AUTOPKG_TOOLKIT_REPO that does not exist, or does not
# look like a recipe repo, is a hard error -- silently falling back to the CWD
# would mean operating on a different tree than the caller named, which is
# exactly the class of mistake this contract exists to prevent.
#
# Inputs:  $1 -- value of --repo, or "" if not supplied
# Outputs: sets REPO_ROOT (absolute, physical). Exits 2 on failure.
resolve_repo_root() {
    local explicit="${1:-}"
    local source_desc=""
    local candidate=""

    if [[ -n "${explicit}" ]]; then
        candidate="${explicit}"
        source_desc="--repo"
    elif [[ -n "${AUTOPKG_TOOLKIT_REPO:-}" ]]; then
        candidate="${AUTOPKG_TOOLKIT_REPO}"
        source_desc="\$AUTOPKG_TOOLKIT_REPO"
    else
        candidate="$(pwd -P)"
        source_desc="current directory"
        if ! looks_like_recipe_repo "${candidate}"; then
            tk_err "No recipe repo specified, and the current directory is not one."
            tk_err "  (a recipe repo is a directory containing recipes/)"
            tk_err ""
            tk_err "Specify one of:"
            tk_err "  --repo /path/to/recipe-repo"
            tk_err "  export AUTOPKG_TOOLKIT_REPO=/path/to/recipe-repo"
            tk_err "  cd into the recipe repo before running"
            exit 2
        fi
    fi

    if [[ ! -d "${candidate}" ]]; then
        tk_die "Repo path from ${source_desc} does not exist: ${candidate}"
    fi

    candidate="$(cd "${candidate}" && pwd -P)"

    if ! looks_like_recipe_repo "${candidate}"; then
        tk_err "Repo path from ${source_desc} does not look like an AutoPkg recipe repo:"
        tk_err "  ${candidate}"
        tk_err "  (expected a recipes/ directory inside it)"
        tk_err ""
        tk_err "Refusing to guess. If this really is the repo, create recipes/ first."
        exit 2
    fi

    REPO_ROOT="${candidate}"
    export REPO_ROOT
}

# repo_recipes_dir
#
# The recipes/ directory of the resolved repo. Frontends that default to
# "everything in the repo" use this rather than assembling the path themselves.
#
# Outputs: prints the path
repo_recipes_dir() {
    echo "${REPO_ROOT}/recipes"
}

# ── Prerequisite checks ───────────────────────────────────────────────────────

# require_command <command> <remediation message>
#
# Verifies a command exists, failing with actionable remediation rather than a
# bare "command not found" from three call frames down.
#
# Inputs:  $1 -- command name
#          $2 -- what the user should do about it
# Outputs: exit 2 if absent
require_command() {
    local cmd="$1"
    local remedy="$2"
    if ! command -v "${cmd}" >/dev/null 2>&1; then
        tk_err "Required command not found: ${cmd}"
        tk_err "  ${remedy}"
        exit 2
    fi
}

# require_macos
#
# Several frontends wrap macOS-only tooling (autopkg, pkgutil). Fail early and
# clearly rather than midway through a run.
require_macos() {
    if [[ "$(uname -s)" != "Darwin" ]]; then
        tk_err "This tool requires macOS (it wraps autopkg/pkgutil, which are macOS-only)."
        exit 2
    fi
}

# ── Python interpreter ────────────────────────────────────────────────────────
#
# Python-using front ends run AutoPkg's own bundled interpreter. Every Mac this
# toolkit is useful on has AutoPkg, and AutoPkg's Python always carries PyYAML
# (AutoPkg needs it to read YAML recipes) — so there is exactly one interpreter
# and no "which python3 is first on PATH" guessing. The linter never uses
# Python at all.
#
# Resolution: $AUTOPKG_TOOLKIT_PYTHON (explicit override, e.g. a venv), then
# AutoPkg's interpreter via its stable symlink, then the framework path the
# symlink points at.

readonly TOOLKIT_AUTOPKG_PYTHON="/usr/local/autopkg/python"
readonly TOOLKIT_AUTOPKG_PYTHON_FW="/Library/AutoPkg/Python3/Python.framework/Versions/Current/bin/python3"
TOOLKIT_PYTHON=""

# toolkit_python_path — prints the interpreter to use; 1 (with an error) if none.
toolkit_python_path() {
    if [[ -n "${TOOLKIT_PYTHON}" ]]; then
        printf '%s\n' "${TOOLKIT_PYTHON}"
        return 0
    fi
    local candidate
    if [[ -n "${AUTOPKG_TOOLKIT_PYTHON:-}" ]]; then
        if [[ -x "${AUTOPKG_TOOLKIT_PYTHON}" ]]; then
            TOOLKIT_PYTHON="${AUTOPKG_TOOLKIT_PYTHON}"
            printf '%s\n' "${TOOLKIT_PYTHON}"
            return 0
        fi
        tk_err "AUTOPKG_TOOLKIT_PYTHON is set but not executable: ${AUTOPKG_TOOLKIT_PYTHON}"
        return 1
    fi
    for candidate in "${TOOLKIT_AUTOPKG_PYTHON}" "${TOOLKIT_AUTOPKG_PYTHON_FW}"; do
        if [[ -x "${candidate}" ]]; then
            TOOLKIT_PYTHON="${candidate}"
            printf '%s\n' "${TOOLKIT_PYTHON}"
            return 0
        fi
    done
    tk_err "AutoPkg's Python not found (${TOOLKIT_AUTOPKG_PYTHON})."
    tk_err "Install AutoPkg (https://github.com/autopkg/autopkg/releases), or set"
    tk_err "AUTOPKG_TOOLKIT_PYTHON to a Python 3.10+ that has PyYAML."
    return 1
}

# tk_python <python args...> — run the toolkit's interpreter. Drop-in for
# `python3` in pipelines, command substitutions and here-docs.
tk_python() {
    local py
    py="$(toolkit_python_path)" || return 127
    # The kit's own Python packages (lib/python/recipekit, …) are found from the
    # kit's location, never an installed site-packages (constitution P-1, P-9).
    PYTHONPATH="${TOOLKIT_ROOT}/lib/python${PYTHONPATH:+:${PYTHONPATH}}" "${py}" "$@"
}

# ── Org naming config ─────────────────────────────────────────────────────────
#
# config/org.yaml holds the handful of values that make the kit one org's kit:
# the identifier namespace, the pkgname prefix, and the names that appear in
# generated recipes and lint messages. Everything org-specific reads from here,
# so a fork changes one file instead of patching scripts.
#
# Deliberately parsed in pure bash (flat `key: value` lines only) because the
# linter consumes it and must not depend on python3 or PyYAML.

ORG_CONFIG_FILE=""
ORG_NAME=""
ORG_IDENTIFIER_PREFIX=""
ORG_IDENTIFIER_PREFIX_RE=""
ORG_PKGNAME_PREFIX=""
ORG_INTERNAL_DOMAIN=""
ORG_VENDOR_DIR=""
ORG_FLEET_MIN_MACOS=""

# Set by resolve_customer (specs/toolkit/02-customers.md); read by the scripts
# that call it.
# shellcheck disable=SC2034
CUSTOMER_NAME="" CUSTOMER_ROOT="" CUSTOMER_REPO="" CUSTOMER_LEAK_PATTERNS=""

# resolve_customer [name]
#
# Loads one customer (specs/toolkit/02-customers.md): CUSTOMER_NAME, CUSTOMER_ROOT,
# CUSTOMER_REPO, CUSTOMER_LEAK_PATTERNS, and the customer's org naming (its
# org.yaml laid over config/org.yaml) into the ORG_* globals, so a later
# read_org_config keeps it. The name is the argument, else $AUTOPKG_TOOLKIT_CUSTOMER,
# else the registry's default. The registry is read by recipekit.customers; with no
# registry, a name still means customer/<name> in the kit. Returns 1, with the error
# printed, if it can't resolve.
resolve_customer() {
    local name="${1:-${AUTOPKG_TOOLKIT_CUSTOMER:-}}" assignments
    assignments="$(tk_python -m recipekit.customers show ${name:+"${name}"} --output env)" \
        || return 1
    # recipekit.customers quotes every value with shlex.quote.
    eval "${assignments}"
    ORG_IDENTIFIER_PREFIX_RE="$(_org_escape_dots "${ORG_IDENTIFIER_PREFIX}" 1)"
    return 0
}

# _org_yaml_value <file> <key>
#
# Prints the value of a top-level `key: value` line. Handles double-quoted,
# single-quoted and bare values, and strips trailing `# comments` from bare
# values. Prints nothing if the key is absent.
_org_yaml_value() {
    local file="$1" key="$2" line val
    line="$(grep -E "^${key}:" "${file}" 2>/dev/null | head -1)" || true
    [[ -n "${line}" ]] || return 0
    val="${line#*:}"
    val="${val#"${val%%[![:space:]]*}"}"
    if [[ "${val}" =~ ^\"([^\"]*)\" ]]; then
        val="${BASH_REMATCH[1]}"
    elif [[ "${val}" =~ ^\'([^\']*)\' ]]; then
        val="${BASH_REMATCH[1]}"
    else
        val="${val%%#*}"
        val="${val%"${val##*[![:space:]]}"}"
    fi
    printf '%s' "${val}"
}

# _org_escape_dots <text> <n>
#
# Prints text with each "." preceded by n backslashes. Done with a loop rather
# than ${var//./\\.} because bash 3.2 and bash 5.2+ treat backslashes in a
# pattern-substitution replacement differently.
_org_escape_dots() {
    local in="$1" n="$2" out="" c i bs=""
    for ((i = 0; i < n; i++)); do bs="${bs}\\"; done
    for ((i = 0; i < ${#in}; i++)); do
        c="${in:i:1}"
        if [[ "${c}" == "." ]]; then out="${out}${bs}."; else out="${out}${c}"; fi
    done
    printf '%s' "${out}"
}

# read_org_config [org_file]
#
# Loads org naming into the ORG_* globals. Resolution order: the explicit
# argument (a frontend's --org flag), then $AUTOPKG_TOOLKIT_ORG, then the
# toolkit's config/org.yaml. Idempotent: a second call with no argument is a
# no-op once loaded.
#
# Sets: ORG_CONFIG_FILE ORG_NAME ORG_IDENTIFIER_PREFIX ORG_IDENTIFIER_PREFIX_RE
#       ORG_PKGNAME_PREFIX ORG_INTERNAL_DOMAIN ORG_VENDOR_DIR
# Returns 0 on success, 1 (with an error printed) if missing or invalid.
read_org_config() {
    local file="${1:-}"
    if [[ -z "${file}" && -n "${ORG_CONFIG_FILE}" ]]; then
        return 0
    fi
    file="${file:-${AUTOPKG_TOOLKIT_ORG:-${TOOLKIT_CONFIG_DIR}/org.yaml}}"

    if [[ ! -f "${file}" ]]; then
        tk_err "org config not found: ${file}"
        return 1
    fi

    ORG_NAME="$(_org_yaml_value "${file}" org_name)"
    ORG_IDENTIFIER_PREFIX="$(_org_yaml_value "${file}" identifier_prefix)"
    ORG_PKGNAME_PREFIX="$(_org_yaml_value "${file}" pkgname_prefix)"
    ORG_INTERNAL_DOMAIN="$(_org_yaml_value "${file}" internal_domain)"
    ORG_VENDOR_DIR="$(_org_yaml_value "${file}" vendor_dir)"
    ORG_FLEET_MIN_MACOS="$(_org_yaml_value "${file}" fleet_min_macos)"

    if [[ ! "${ORG_IDENTIFIER_PREFIX}" =~ ^[A-Za-z0-9]+(\.[A-Za-z0-9-]+)+$ ]]; then
        tk_err "${file}: identifier_prefix '${ORG_IDENTIFIER_PREFIX}' must be reverse-DNS, e.g. com.example.autopkg"
        return 1
    fi
    if [[ ! "${ORG_PKGNAME_PREFIX}" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
        tk_err "${file}: pkgname_prefix '${ORG_PKGNAME_PREFIX}' must be non-empty and filename-safe, e.g. Example_"
        return 1
    fi
    if [[ -n "${ORG_FLEET_MIN_MACOS}" && ! "${ORG_FLEET_MIN_MACOS}" =~ ^[0-9]+(\.[0-9]+){0,2}$ ]]; then
        tk_err "${file}: fleet_min_macos '${ORG_FLEET_MIN_MACOS}' must be a macOS version, e.g. 14 or 14.6"
        return 1
    fi
    [[ -n "${ORG_NAME}" ]] || ORG_NAME="${ORG_IDENTIFIER_PREFIX}"
    [[ -n "${ORG_VENDOR_DIR}" ]] || ORG_VENDOR_DIR="${ORG_PKGNAME_PREFIX%_}"

    # The prefix is validated to contain only [A-Za-z0-9.-], so escaping the
    # dots is enough to make it a literal in an ERE.
    ORG_IDENTIFIER_PREFIX_RE="$(_org_escape_dots "${ORG_IDENTIFIER_PREFIX}" 1)"
    ORG_CONFIG_FILE="${file}"
    return 0
}

# org_render <text>
#
# Replaces {{ORG_*}} tokens in text with the loaded org values. Used for
# config files (checks.yaml) and generated-recipe templates. Tokens:
#   {{ORG_NAME}} {{IDENTIFIER_PREFIX}} {{IDENTIFIER_PREFIX_RE}}
#   {{IDENTIFIER_PREFIX_RE_YAML}} {{PKGNAME_PREFIX}} {{INTERNAL_DOMAIN}}
#   {{VENDOR_DIR}}
# The _RE_YAML form doubles each backslash, for regexes inside YAML
# double-quoted strings (checks.yaml stores `\\.` for a literal dot).
org_render() {
    local s="$1"
    case "${s}" in
        *'{{'*) ;;
        *) printf '%s\n' "${s}"; return 0 ;;
    esac
    s="$(_org_replace "${s}" '{{ORG_NAME}}' "${ORG_NAME}")"
    s="$(_org_replace "${s}" '{{IDENTIFIER_PREFIX_RE_YAML}}' "$(_org_escape_dots "${ORG_IDENTIFIER_PREFIX}" 2)")"
    s="$(_org_replace "${s}" '{{IDENTIFIER_PREFIX_RE}}' "${ORG_IDENTIFIER_PREFIX_RE}")"
    s="$(_org_replace "${s}" '{{IDENTIFIER_PREFIX}}' "${ORG_IDENTIFIER_PREFIX}")"
    s="$(_org_replace "${s}" '{{PKGNAME_PREFIX}}' "${ORG_PKGNAME_PREFIX}")"
    s="$(_org_replace "${s}" '{{INTERNAL_DOMAIN}}' "${ORG_INTERNAL_DOMAIN}")"
    s="$(_org_replace "${s}" '{{VENDOR_DIR}}' "${ORG_VENDOR_DIR}")"
    printf '%s\n' "${s}"
}

# _org_replace <text> <token> <value>
#
# Replaces every literal occurrence of token with value. Uses prefix/suffix
# removal instead of ${s//token/value}: in bash 5.2+ the replacement half of
# that expansion interprets backslashes and "&", which would corrupt regex
# values and org names like "Fruit & Veg".
_org_replace() {
    local s="$1" tok="$2" val="$3" out=""
    while [[ "${s}" == *"${tok}"* ]]; do
        out="${out}${s%%"${tok}"*}${val}"
        s="${s#*"${tok}"}"
    done
    printf '%s' "${out}${s}"
}

# temp_dir
#
# Creates a temporary directory and prints its path. The caller should clean it
# up with rm -rf when done. Uses $TMPDIR if set, otherwise /tmp.
#
# Outputs: prints the temporary directory path
temp_dir() {
    mktemp -d "${TMPDIR:-/tmp}/toolkit.XXXXXXXX"
}

# ── Application version extraction ────────────────────────────────────────────

# ── Wiki lookup helper ────────────────────────────────────────────────────────

# wiki_page_for_processor <ProcessorName>
#
# Prints the path to the upstream wiki page for a processor, if the wiki is
# present. The wiki is excluded from dist builds, so callers must treat a
# non-zero return as "resource not available here", not as an error.
#
# Inputs:  $1 -- exact processor name, e.g. Copier
# Outputs: prints path and returns 0 if present; returns 1 if not
wiki_page_for_processor() {
    local processor="$1"
    local page="${TOOLKIT_WIKI_DIR}/Processor-${processor}.md"
    if [[ -f "${page}" ]]; then
        echo "${page}"
        return 0
    fi
    return 1
}
