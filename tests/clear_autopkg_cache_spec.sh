# shellcheck shell=sh disable=SC2016,SC2286,SC2287,SC2288

# bin/clear-autopkg-cache.sh against a throwaway HOME, so no real cache is touched.
# Spec: specs/clear-autopkg-cache/01-clear-autopkg-cache.md

CC_HOME="/tmp/clear_autopkg_cache_spec"
CC_ROOT="${CC_HOME}/Library/AutoPkg/Cache"

cc_setup() {
    rm -rf "${CC_HOME}"
    mkdir -p "${CC_ROOT}/com.acmefruit.autopkg.pkg.Moonlight" \
             "${CC_ROOT}/com.acmefruit.autopkg.pkg.Pearcleaner"
    : > "${CC_ROOT}/com.acmefruit.autopkg.pkg.Moonlight/Acme_Moonlight.pkg"
}
cc_teardown() { rm -rf "${CC_HOME}"; }
cc() { HOME="${CC_HOME}" bin/clear-autopkg-cache.sh "$@"; }
entries() { ls "${CC_ROOT}" | tr '\n' ' '; }

Describe 'clear-autopkg-cache.sh'
    BeforeEach 'cc_setup'
    AfterEach 'cc_teardown'

    It 'removes only the named identifier'
        When call cc com.acmefruit.autopkg.pkg.Moonlight
        The status should be success
        The output should include "removed:"
        The result of function entries should eq "com.acmefruit.autopkg.pkg.Pearcleaner "
    End

    It 'refuses an empty identifier and leaves the cache intact (KI-24)'
        When call cc ""
        The status should eq 1
        The error should include "REFUSED"
        The result of function entries should eq "com.acmefruit.autopkg.pkg.Moonlight com.acmefruit.autopkg.pkg.Pearcleaner "
    End

    It 'refuses "." and paths'
        When call cc . ../x a/b
        The status should eq 1
        The error should include "REFUSED: '.'"
        The error should include "REFUSED: '../x'"
        The error should include "REFUSED: 'a/b'"
        The result of function entries should eq "com.acmefruit.autopkg.pkg.Moonlight com.acmefruit.autopkg.pkg.Pearcleaner "
    End

    It 'removes nothing with --dry-run'
        When call cc --dry-run com.acmefruit.autopkg.pkg.Moonlight
        The status should be success
        The output should include "[DRY RUN] would remove"
        The result of function entries should eq "com.acmefruit.autopkg.pkg.Moonlight com.acmefruit.autopkg.pkg.Pearcleaner "
    End

    It 'empties the cache root, but keeps the root, with --all'
        When call cc --all
        The status should be success
        The output should include "Cache root emptied."
        The result of function entries should eq ""
        The path "${CC_ROOT}" should be directory
    End

    It 'reports an identifier with nothing cached'
        When call cc com.acmefruit.autopkg.pkg.Absent
        The status should be success
        The output should include "nothing to clear"
    End
End
