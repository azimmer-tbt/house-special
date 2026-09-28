# shellcheck shell=sh disable=SC2016,SC2286,SC2287,SC2288

# bin/rr-batch.sh as a command, with a fake recipe-robot that behaves like the
# real one (2.5.0): it writes <App>.<type>.recipe.yaml under a developer folder
# and prints each path after "Generating <type> recipe...". The parsing and
# renaming logic is unit-tested in tests/python/test_rr_batch.py.
# Spec: specs/rr-batch/01-batch-definitions.md

RB_TMP="/tmp/rr_batch_spec"
export RR_BIN="${RB_TMP}/recipe-robot"
export RR_PREFS="${RB_TMP}/no-prefs.plist"   # the preferences check always warns

batch_fixture() { echo "tests/fixtures/batch/$1"; }

rb_setup() {
    rm -rf "${RB_TMP}"
    mkdir -p "${RB_TMP}"
    cat > "${RR_BIN}" <<'MOCK'
#!/bin/bash
# Fake Recipe Robot: the app's bundle name is the URL's last path part with
# spaces, the developer folder is fixed. RB_FAIL makes it fail.
echo "recipe-robot $*" >> /tmp/rr_batch_spec/calls.log
[ -n "${RB_FAIL:-}" ] && { echo "Unable to process"; exit 1; }
url="${!#}"; app="$(basename "${url}" .dmg | tr '-' ' ')"
out="/tmp/rr_batch_spec/rr-output/Some Developer"; mkdir -p "${out}"
for type in download pkg; do
    f="${out}/${app}.${type}.recipe.yaml"
    parent=""; [ "${type}" = pkg ] && parent="ParentRecipe: com.example.rr.download.${app// /}"
    printf 'Identifier: com.example.rr.%s.%s\nInput:\n  NAME: %s\n%s\nProcess: []\n' \
        "${type}" "${app// /}" "${app}" "${parent}" > "${f}"
    printf 'Generating %s recipe...\033[0m\n    %s\033[0m\n' "${type}" "${f}"
done
MOCK
    chmod +x "${RR_BIN}"
}
rb_teardown() { rm -rf "${RB_TMP}"; }
rb() { /bin/bash bin/rr-batch.sh "$@"; }
batch() { rb -i "$(batch_fixture example-4col.csv)" --log-dir "${RB_TMP}/logs" -o "${RB_TMP}/out" "$@"; }
calls() { cat "${RB_TMP}/calls.log"; }
teams() { echo "${RB_TMP}/out/recipes/microsoft/Microsoft Teams"; }

Describe 'rr-batch.sh'
    BeforeEach 'rb_setup'
    AfterEach 'rb_teardown'

    Describe 'arguments'
        It 'prints usage on --help'
            When call rb --help
            The status should be success
            The output should include "Usage:"
        End

        It 'exits 2 on an unknown option'
            When call rb --bogus-flag
            The status should eq 2
            The stderr should include "Unknown option: --bogus-flag"
        End

        It 'exits 2 without an input file, a log dir, or an existing input'
            When call rb --log-dir "${RB_TMP}/logs"
            The status should eq 2
            The stderr should include "-i input file is required"
        End

        It 'exits 2 when the input file does not exist'
            When call rb -i /nonexistent.csv --log-dir "${RB_TMP}/logs"
            The status should eq 2
            The stderr should include "Input file not found"
        End

        It 'AC-4.3: exits 2 when Recipe Robot is missing'
            When call env RR_BIN=/nonexistent/recipe-robot /bin/bash bin/rr-batch.sh -i "$(batch_fixture example-4col.csv)" --log-dir "${RB_TMP}/logs"
            The status should eq 2
            The stderr should include "Recipe Robot not found"
        End

        It 'FR-9: rejects smart quotes'
            When call rb -i "$(batch_fixture malformed-smartquotes.csv)" --log-dir "${RB_TMP}/logs"
            The status should eq 2
            The stderr should include "Smart quotes detected"
        End
    End

    Describe 'a run'
        It 'processes blank and TEST rows (3), skips DONE and SKIP, and warns about preferences'
            When call batch -e
            The status should be success
            The stderr should include "WARNING: Recipe Robot preferences not found"
            The output should include "Total: 3  |  Pass: 3  |  Fail: 0  |  Skip: 2"
            The result of function calls should include "recipe-robot --ignore-existing https://office.com/download/teams.dmg"
        End

        It 'FR-5: files the recipes under Vendor/AppName with the CSV name and org prefix'
            batch >/dev/null 2>&1
            When call cat "$(teams)/Microsoft Teams.pkg.recipe.yaml"
            The output should include "Identifier: com.acmefruit.autopkg.pkg.Microsoft Teams"
            The output should include "ParentRecipe: com.acmefruit.autopkg.download.Microsoft Teams"
            The output should include "  NAME: Microsoft Teams"
        End

        It "AC-5.7: leaves Recipe Robot's own output in place"
            batch >/dev/null 2>&1
            The path "${RB_TMP}/rr-output/Some Developer/teams.download.recipe.yaml" should be file
        End

        It 'OQ-4: does not overwrite without --force'
            batch >/dev/null 2>&1
            When call batch
            The status should be success
            The stderr should be present
            The output should include "Target exists, skipping"
            The output should include "SKIP  [TEST-existing] [Microsoft Teams]"
        End

        It 'FR-7: reports a Recipe Robot failure and exits 1'
            When call env RB_FAIL=1 /bin/bash bin/rr-batch.sh -i "$(batch_fixture example-4col.csv)" --log-dir "${RB_TMP}/logs" -o "${RB_TMP}/out"
            The status should eq 1
            The stderr should be present
            The output should include "FAIL  [Microsoft Teams] exit 1"
            The output should include "Failed packages:"
        End
    End
End
