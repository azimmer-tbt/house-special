# shellcheck shell=sh

set -eu

spec_helper_precheck() {
    : minimum_version "0.28.1"
}

spec_helper_loaded() {
    :
}

spec_helper_configure() {
    :
}

# Helper: path to a fixture file
fixture() {
    echo "${SHELLSPEC_HELPERDIR:-tests}/fixtures/linter/$1"
}