# shellcheck shell=sh disable=SC2016,SC2286,SC2287,SC2288

# bin/analyze-package.sh against small packages built on the fly with the stock
# pkgbuild. Covers the payload expansion (--expand-full) and the reverse-domain
# identifier check (mixed case, non-com TLDs).

AP_TMP="/tmp/analyze_package_spec"

ap_setup() {
    rm -rf "${AP_TMP}"
    mkdir -p "${AP_TMP}/root/Applications/Demo.app/Contents"
    printf '<?xml version="1.0" encoding="UTF-8"?>\n<plist version="1.0"><dict><key>CFBundleShortVersionString</key><string>1.0</string></dict></plist>\n' \
        > "${AP_TMP}/root/Applications/Demo.app/Contents/Info.plist"
    pkgbuild --quiet --root "${AP_TMP}/root" --identifier io.example.DemoApp \
        --version 1.0 "${AP_TMP}/Demo.pkg"
    pkgbuild --quiet --root "${AP_TMP}/root" --identifier demoinhouse2019 \
        --version 1.0 "${AP_TMP}/Legacy.pkg"
}
ap_teardown() { rm -rf "${AP_TMP}"; }

Describe 'analyze-package.sh'
    BeforeAll 'ap_setup'
    AfterAll 'ap_teardown'

    It 'finds .app bundles inside the payload'
        When run script bin/analyze-package.sh "${AP_TMP}/Demo.pkg"
        The output should include "Apps found:   Demo.app"
        The status should be success
    End

    It 'treats a mixed-case, non-com identifier as reverse-domain'
        When run script bin/analyze-package.sh "${AP_TMP}/Demo.pkg"
        The output should include "Identifier 'io.example.DemoApp' matches reverse-domain pattern"
        The status should be success
    End

    It 'flags a single-token legacy identifier as not reverse-domain'
        When run script bin/analyze-package.sh "${AP_TMP}/Legacy.pkg"
        The output should include "is NOT reverse-domain"
        The status should be success
    End
End

Describe 'analyze-package.sh org namespace'
    org_pkg_setup() {
        mkdir -p "${AP_TMP}/orgroot/Applications/Demo.app/Contents"
        pkgbuild --quiet --root "${AP_TMP}/orgroot" --identifier com.acmefruit.pkg.Demo \
            --version 1.0 "${AP_TMP}/Acme_Demo.pkg"
    }
    BeforeAll 'ap_setup' 'org_pkg_setup'
    AfterAll 'ap_teardown'

    It "treats the org's own identifier namespace as in-house"
        When run script bin/analyze-package.sh "${AP_TMP}/Acme_Demo.pkg"
        The output should include "in the org's own namespace (com.acmefruit)"
        The status should be success
    End
End
