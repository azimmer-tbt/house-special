# shellcheck shell=sh disable=SC2016,SC2286,SC2287,SC2288

# bin/run-recipes.sh with a stub `autopkg` that only records its arguments.
# Spec: specs/run-recipes/01-run-recipes.md

RR_TMP="/tmp/run_recipes_spec"
RR_REPO="${RR_TMP}/repo"

rr_setup() {
    rm -rf "${RR_TMP}"
    mkdir -p "${RR_TMP}/stub" "${RR_REPO}/recipes/Acme/NoOverrides" "${RR_REPO}/recipes/Acme/WithOverrides"
    for app in NoOverrides WithOverrides; do
        printf 'Identifier: "com.acmefruit.autopkg.download.%s"\n' "${app}" \
            > "${RR_REPO}/recipes/Acme/${app}/${app}.download.recipe.yaml"
        printf 'Identifier: com.acmefruit.autopkg.pkg.%s\n' "${app}" \
            > "${RR_REPO}/recipes/Acme/${app}/${app}.pkg.recipe.yaml"
    done
    # No trailing newline on the last line.
    printf 'teamid=ABCDE12345\nversion=1.2.3' > "${RR_REPO}/recipes/Acme/WithOverrides/.overrides"
    cat > "${RR_TMP}/stub/autopkg" <<'STUB'
#!/bin/bash
echo "autopkg $*" >> /tmp/run_recipes_spec/calls.log
STUB
    chmod +x "${RR_TMP}/stub/autopkg"
}
rr_teardown() { rm -rf "${RR_TMP}"; }
rr() { PATH="${RR_TMP}/stub:${PATH}" /bin/bash bin/run-recipes.sh --repo "${RR_REPO}" "$@"; }
calls() { cat "${RR_TMP}/calls.log"; }

Describe 'run-recipes.sh'
    BeforeEach 'rr_setup'
    AfterEach 'rr_teardown'

    It 'runs an app that has no .overrides under bash 3.2 (KI-27)'
        When call rr NoOverrides
        The status should be success
        The output should include "Results: 1 passed, 0 failed, 0 skipped"
        The result of function calls should include "NoOverrides.download.recipe.yaml -v"
        The result of function calls should include "NoOverrides.pkg.recipe.yaml -v"
    End

    It 'passes every .overrides line, including a last line without a newline'
        When call rr WithOverrides
        The status should be success
        The output should include "Results: 1 passed, 0 failed, 0 skipped"
        The result of function calls should include "--key=teamid=ABCDE12345 --key=version=1.2.3 -v"
    End

    It 'runs every app and prints a summary'
        When call rr
        The status should be success
        The output should include "Results: 2 passed, 0 failed, 0 skipped"
    End
End
