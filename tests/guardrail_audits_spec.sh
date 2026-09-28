# shellcheck shell=sh disable=SC2016,SC2286,SC2287,SC2288

# guardrails/audit: the three audits that misread correct recipes (KI-30), on
# small fixture recipes. Spec: specs/guardrail-audits/01-audits.md

GA_TMP="/tmp/guardrail_audits_spec"

ga_setup() { rm -rf "${GA_TMP}"; mkdir -p "${GA_TMP}"; }
ga_teardown() { rm -rf "${GA_TMP}"; }
recipe() { # recipe <name> <yaml>
    printf '%s\n' "$2" > "${GA_TMP}/$1"
}
audit() { guardrails/audit/"$1".py "${GA_TMP}/$2"; }
preflight() { ./bin/autopkg-preflight.py "$@"; }
preflight_acme() { ./bin/autopkg-preflight.py --repo customer/acme/output 2>&1 || true; }
# The vendor-cache audit depends on what is on this machine (a cache at
# /tmp/autopkg/vendor_cache makes Acme's fictional drops FAIL; no cache, SKIP).
preflight_acme_failures() {
    preflight_acme | grep -E '^  \[FAIL\]' | grep -v 'vendor_cache_path' || true
}

Describe 'guardrail audits'
    BeforeEach 'ga_setup'
    AfterEach 'ga_teardown'

    Describe 'check_cert_chain_complete'
        It 'passes a verifier that uses a designated requirement'
            recipe A.download.recipe.yaml 'Process:
  - Processor: CodeSignatureVerifier
    Arguments:
      input_path: "%pathname%/A.app"
      requirement: identifier "com.example.a" and certificate leaf[subject.OU] = "ABCDE12345"'
            When call audit check_cert_chain_complete A.download.recipe.yaml
            The status should be success
            The output should include "PASS"
        End

        It 'fails authority names without the Apple chain, even if a comment names it'
            recipe A.download.recipe.yaml '# Developer ID Certification Authority, Apple Root CA
Process:
  - Processor: CodeSignatureVerifier
    Arguments:
      input_path: "%pathname%"
      expected_authority_names:
        - "Developer ID Installer: Example Vendor (ABCDE12345)"'
            When call audit check_cert_chain_complete A.download.recipe.yaml
            The status should eq 1
            The output should include "FAIL"
        End

        It 'passes authority names with the full chain'
            recipe A.download.recipe.yaml 'Process:
  - Processor: CodeSignatureVerifier
    Arguments:
      input_path: "%pathname%"
      expected_authority_names:
        - "Developer ID Installer: Example Vendor (ABCDE12345)"
        - "Developer ID Certification Authority"
        - "Apple Root CA"'
            When call audit check_cert_chain_complete A.download.recipe.yaml
            The status should be success
            The output should include "PASS"
        End
    End

    Describe 'check_unsigned_declared'
        It 'passes the flag with a reason in the comment above it'
            recipe A.download.recipe.yaml 'Identifier: com.acmefruit.autopkg.download.A
Input:
  # Org-authored scripts: nothing signed to verify.
  NO_CODE_SIGNATURE_REQUIRED: true
Process:
  - Processor: URLDownloader'
            When call audit check_unsigned_declared A.download.recipe.yaml
            The status should be success
            The output should include "PASS"
        End

        It 'fails the flag with no reason'
            recipe A.download.recipe.yaml 'Identifier: com.acmefruit.autopkg.download.A
Input:
  NAME: A
  NO_CODE_SIGNATURE_REQUIRED: true
Process:
  - Processor: URLDownloader'
            When call audit check_unsigned_declared A.download.recipe.yaml
            The status should eq 1
            The output should include "FAIL"
        End

        It 'fails when the flag exists only in a comment'
            recipe A.download.recipe.yaml 'Identifier: com.acmefruit.autopkg.download.A
Input:
  # no CodeSignatureVerifier here
  # NO_CODE_SIGNATURE_REQUIRED: true
  NAME: A
Process:
  - Processor: URLDownloader'
            When call audit check_unsigned_declared A.download.recipe.yaml
            The status should eq 1
            The output should include "FAIL"
        End
    End

    Describe 'check_variables_declared'
        It 'knows URLTextSearcher sets its named groups, and reads Input past a blank line (KI-8c)'
            recipe A.download.recipe.yaml 'Identifier: com.acmefruit.autopkg.download.A
Input:
  NAME: A

  SEARCH_PATTERN: "(?P<url>https://example.com/A-[0-9.]+\\.dmg)"
Process:
  - Processor: URLTextSearcher
    Arguments:
      url: "https://example.com/download"
      re_pattern: "%SEARCH_PATTERN%"
  - Processor: URLDownloader
    Arguments:
      url: "%url%"
  - Processor: Versioner
    Arguments:
      input_plist_path: "%pathname%/A.app/Contents/Info.plist"'
            recipe A.pkg.recipe.yaml 'Identifier: com.acmefruit.autopkg.pkg.A
ParentRecipe: com.acmefruit.autopkg.download.A
Input:
  NAME: A
Process:
  - Processor: PkgCreator
    Arguments:
      pkg_request:
        version: "%version%"'
            When call audit check_variables_declared A.pkg.recipe.yaml
            The status should be success
            The output should include "PASS"
        End

        It 'fails %version% when only URLDownloader runs (it does not set version)'
            recipe A.download.recipe.yaml 'Identifier: com.acmefruit.autopkg.download.A
Input:
  NAME: A
Process:
  - Processor: URLDownloader
    Arguments:
      url: "https://example.com/A.zip"'
            recipe A.pkg.recipe.yaml 'Identifier: com.acmefruit.autopkg.pkg.A
ParentRecipe: com.acmefruit.autopkg.download.A
Input:
  NAME: A
Process:
  - Processor: PkgCreator
    Arguments:
      pkg_request:
        version: "%version%"'
            When call audit check_variables_declared A.pkg.recipe.yaml
            The status should eq 1
            The output should include "%version% is used but nothing declares or sets it"
        End

        It 'ignores %tokens% that appear only in comments'
            recipe A.download.recipe.yaml 'Identifier: com.acmefruit.autopkg.download.A
Input:
  NAME: A
  # was: %OLD_URL%
Process:
  - Processor: URLDownloader
    Arguments:
      url: "https://example.com/A.zip"'
            recipe A.pkg.recipe.yaml 'Identifier: com.acmefruit.autopkg.pkg.A
ParentRecipe: com.acmefruit.autopkg.download.A
Input:
  NAME: A
Process: []'
            When call audit check_variables_declared A.pkg.recipe.yaml
            The status should be success
            The output should include "PASS"
        End
    End

    It 'bin/autopkg-preflight.py fails no check on the Acme repo except, possibly, the machine-dependent vendor cache'
        When call preflight_acme_failures
        The output should eq ""
    End

    It 'bin/autopkg-preflight.py reports a summary and the autopkg-run reminder'
        When call preflight_acme
        The output should include "Result: "
        The output should include "not a substitute for a real"
    End

    It 'bin/autopkg-preflight.py refuses an --app outside the repo (exit 2)'
        When call preflight --repo customer/acme/output --app /tmp
        The status should eq 2
        The stderr should include "outside the repo"
    End

    It 'bin/autopkg-preflight.py finds --app relative to the repo'
        When call preflight --repo customer/acme/output --app recipes/MoonlightGameStreaming/Moonlight --no-lint
        The status should be success
        The output should include "Checking: recipes/MoonlightGameStreaming/Moonlight"
    End
End
