# shellcheck shell=sh disable=SC2016,SC2286,SC2287,SC2288

# Runs the Python unit tests (tests/python/test_*.py) under AutoPkg's Python, so
# `shellspec` stays the single test entry point (specs/recipekit/01-recipe-model.md FR-11).
#
# The run is verbose (one line per test). When it fails, the full output is also
# saved to $TMPDIR/house-special-python-tests-<timestamp>.log together with the
# disk images mounted at that moment (hdiutil info), since the package and DMG
# tests share the machine with anything else running; the path is printed last.

run_unittest() { # run_unittest [tests-dir]
    # shellcheck source=../lib/toolkit-common.sh
    . lib/toolkit-common.sh
    ut_out="$(tk_python -m unittest discover -v -s "${1:-tests/python}" 2>&1)"
    ut_rc=$?
    printf '%s\n' "${ut_out}"
    if [ "${ut_rc}" -ne 0 ]; then
        ut_log="${TMPDIR:-/tmp}/house-special-python-tests-$(date +%Y%m%d-%H%M%S).log"
        {
            printf '%s\n' "${ut_out}"
            echo ""
            echo "--- hdiutil info at $(date '+%Y-%m-%d %H:%M:%S')"
            hdiutil info 2>&1 || true
        } > "${ut_log}"
        echo "Full log: ${ut_log}"
    fi
    return "${ut_rc}"
}

ut_fail_setup() {
    UT_TMP="$(mktemp -d "${TMPDIR:-/tmp}/ut_spec.XXXXXX")"
    mkdir -p "${UT_TMP}/tests"
    printf 'import unittest\n\n\nclass T(unittest.TestCase):\n    def test_breaks(self):\n        self.assertEqual(1, 2)\n' \
        > "${UT_TMP}/tests/test_breaks.py"
}
ut_fail_teardown() {
    [ -n "${ut_log:-}" ] && rm -f "${ut_log}"
    rm -rf "${UT_TMP}"
}
saved_log() { sed -n 's/^Full log: //p' "${UT_TMP}/out.txt"; }
run_failing() {
    run_unittest "${UT_TMP}/tests" > "${UT_TMP}/out.txt"
    ut_log="$(saved_log)"
    [ -f "${ut_log}" ] && grep -q "test_breaks" "${ut_log}" && grep -q "hdiutil info" "${ut_log}"
}

Describe 'Python unit tests'
    It 'pass under AutoPkg Python'
        When call run_unittest
        The status should be success
        The output should include "OK"
    End

    Describe 'on failure'
        BeforeEach 'ut_fail_setup'
        AfterEach 'ut_fail_teardown'

        It 'saves the named failure and the mounted images to a log'
            When call run_failing
            The status should be success
        End
    End
End
