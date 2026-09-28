# shellcheck shell=sh disable=SC2016,SC2286,SC2287,SC2288

# The worked examples are teaching material: every one must pass the linter
# the kit ships. A rule change that breaks an example fails here first.

Describe 'shipped examples lint clean'
    Parameters
        "templates/pattern-4-vendor-drop/example-Xerox-Drivers"
        "templates/pattern-4b-distribution-package/example-Xerox-Drivers"
        "templates/pattern-4d-vendor-drop-dmg-ridealong/example-Kiwi-Capture"
        "templates/pattern-5-vendor-pkg-url/example-Microsoft-Word"
        "templates/pattern-6-rebuilt-package/example-AcmeSupport-Legacy"
        "templates/pattern-6b-rebuilt-payload-scripts/example-QuarantineHelper"
        "templates/pattern-6c-rebuilt-single-file/example-Audit-Control-Expiry"
        "templates/pattern-6d-rebuilt-payloadless/example-UninstallAgent"
        "templates/pattern-7-faux-vendor-dmg/example-Pomelo-Studio"
    End

    It "lints $1"
        When run script bin/recipe-linter.sh --dir "$1" --pair-check
        The output should include "passed lint checks"
        The status should be success
    End
End

Describe 'customer/acme recipe repo'
    It 'lints clean with the pair check'
        When run script bin/recipe-linter.sh --repo customer/acme/output --pair-check
        The output should include "recipe(s) passed lint checks"
        The status should be success
    End
End
