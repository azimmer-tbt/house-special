# shellcheck shell=sh disable=SC2016,SC2286,SC2287,SC2288

# bin/analyze-materials.sh target matching: separator-insensitive names, no
# version-only matches, and symlinked material followed.

AM_TMP="/tmp/analyze_materials_spec"

am_setup() {
    rm -rf "${AM_TMP}"
    mkdir -p "${AM_TMP}/src/Orchard" "${AM_TMP}/elsewhere"
    : > "${AM_TMP}/src/Orchard/Orchard Analytics 7.2.dmg"
    : > "${AM_TMP}/src/Unrelated-Tool-3.1.4.dmg"
    : > "${AM_TMP}/elsewhere/Pearcleaner.dmg"
    ln -s "${AM_TMP}/elsewhere/Pearcleaner.dmg" "${AM_TMP}/src/Pearcleaner.dmg"
    cat > "${AM_TMP}/targets.yaml" <<'YAML'
recipes:
- app_name: Orchard-Analytics
  vendor: OrchardLabs
  pattern: "4d"
- app_name: Pearcleaner
  vendor: Alienator88
  pattern: "2b"
YAML
}
am_teardown() { rm -rf "${AM_TMP}"; }

Describe 'analyze-materials.sh matching'
    BeforeAll 'am_setup'
    AfterAll 'am_teardown'

    It 'matches a hyphenated app name to a spaced filename'
        When run script bin/analyze-materials.sh "${AM_TMP}/src" --targets "${AM_TMP}/targets.yaml"
        The stderr should include "Scanning"
        The output should include "Orchard Analytics 7.2.dmg"
        The output should include "OrchardLabs/Orchard-Analytics (1 candidate)"
    End

    It 'does not offer a file whose only signal is a version number'
        When run script bin/analyze-materials.sh "${AM_TMP}/src" --targets "${AM_TMP}/targets.yaml"
        The stderr should include "Scanning"
        The output should not include "] Unrelated-Tool-3.1.4.dmg"
    End

    It 'follows symlinked material'
        When run script bin/analyze-materials.sh "${AM_TMP}/src" --targets "${AM_TMP}/targets.yaml"
        The stderr should include "Scanning"
        The output should include "Alienator88/Pearcleaner (1 candidate)"
    End
End
