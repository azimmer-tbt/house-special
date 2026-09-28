# shellcheck shell=sh disable=SC2016,SC2286,SC2287,SC2288

# bin/scan-placeholders.sh on a throwaway recipe repo.
# Spec: specs/scan-placeholders/01-scan-placeholders.md

SP_REPO="/tmp/scan_placeholders_spec"

sp_app() { # sp_app <App> <input-lines> <process-lines>
    mkdir -p "${SP_REPO}/recipes/Acme/$1"
    printf 'Identifier: com.acmefruit.autopkg.download.%s\nInput:\n  NAME: %s\n%s\nProcess:\n%s\n' \
        "$1" "$1" "$2" "$3" > "${SP_REPO}/recipes/Acme/$1/$1.download.recipe.yaml"
}
sp_setup() {
    rm -rf "${SP_REPO}"
    sp_app Unfilled '  DOWNLOAD_URL: "REPLACE_WITH_URL"' '  - Processor: URLDownloader'
    sp_app AdHoc '  teamid: "UNSIGNED_NO_TEAMID"' '  - Processor: CodeSignatureVerifier
    Arguments:
      requirement: identifier "io.example.adhoc"'
    sp_app LeafOnly '  X: y' '  - Processor: CodeSignatureVerifier
    Arguments:
      expected_authority_names:
        - "Developer ID Installer: Example Vendor (ABCDE12345)"'
}
sp_teardown() { rm -rf "${SP_REPO}"; }
scan() { bin/scan-placeholders.sh --repo "${SP_REPO}" "$@" 2>&1; }

Describe 'scan-placeholders.sh'
    BeforeEach 'sp_setup'
    AfterEach 'sp_teardown'

    It 'finds an unfilled placeholder'
        When call scan Unfilled
        The status should be failure
        The output should include "REPLACE_WITH_URL"
    End

    It 'does not flag a deliberate teamid: UNSIGNED_NO_TEAMID, or a requirement-based verifier (KI-28)'
        When call scan AdHoc
        The status should be success
        The output should include "No placeholders found."
    End

    It 'flags an authority-name list with only the leaf certificate'
        When call scan LeafOnly
        The status should be failure
        The output should include "[CHAIN] LeafOnly.download.recipe.yaml"
    End
End
