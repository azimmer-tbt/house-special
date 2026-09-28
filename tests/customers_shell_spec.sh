# shellcheck shell=sh disable=SC2016,SC2286,SC2287,SC2288

# Customers in the shell tools (specs/toolkit/02-customers.md FR-05): the leak
# guard, analyze-materials and run-recipes, with a throwaway registry
# ($AUTOPKG_TOOLKIT_CUSTOMERS) whose customers live inside and outside a scanned tree.

CU_TMP="/tmp/customers_shell_spec"
CU_KIT="${CU_TMP}/kit"
CU_WID="${CU_KIT}/customer/widgets"   # inside the scanned tree
CU_GAD="${CU_TMP}/elsewhere/gadgets"  # outside it

# Customer names are assembled so the kit's own scan doesn't see them whole.
W='Widg''etco'; G='Gadg''etworks'

cu_setup() {
    rm -rf "${CU_TMP}"
    mkdir -p "${CU_KIT}/docs" "${CU_WID}/output/recipes/Wid/Tool" "${CU_GAD}" "${CU_TMP}/stub"
    printf '%s\n' "${W}" > "${CU_WID}/.leak-patterns"
    printf '%s\n' "${G}" > "${CU_GAD}/.leak-patterns"
    : > "${CU_TMP}/empty-patterns"
    printf 'default: widgets\ncustomers:\n  widgets: %s\n  gadgets: %s\n' \
        "${CU_WID}" "${CU_GAD}" > "${CU_TMP}/customers.yaml"
    printf 'identifier_prefix: com.example.widgets\npkgname_prefix: "Wid_"\n' > "${CU_WID}/org.yaml"
    printf 'recipes:\n- app_name: Tool\n  vendor: Wid\n  pattern: "2b"\n' > "${CU_GAD}/end_result.yaml"
    printf 'Identifier: com.example.widgets.download.Tool\n' \
        > "${CU_WID}/output/recipes/Wid/Tool/Tool.download.recipe.yaml"
    printf 'Identifier: com.example.widgets.pkg.Tool\n' \
        > "${CU_WID}/output/recipes/Wid/Tool/Tool.pkg.recipe.yaml"
    printf '#!/bin/bash\necho "autopkg $*" >> %s/calls.log\n' "${CU_TMP}" > "${CU_TMP}/stub/autopkg"
    chmod +x "${CU_TMP}/stub/autopkg"
}
cu_teardown() { rm -rf "${CU_TMP}"; }
cu_plant() { mkdir -p "$(dirname "$1")"; printf '%s\n' "$2" > "$1"; }

cu_env() { AUTOPKG_TOOLKIT_CUSTOMERS="${CU_TMP}/customers.yaml" AUTOPKG_TOOLKIT_CUSTOMER= AUTOPKG_TOOLKIT_REPO= "$@"; }
scan() { cu_env /bin/bash bin/check-sanitized.sh --patterns "${CU_TMP}/empty-patterns" "$@"; }
resolve() {
    cu_env /bin/bash -c '. lib/toolkit-common.sh; resolve_customer "$1" \
        && echo "${CUSTOMER_NAME}|${CUSTOMER_ROOT}|${CUSTOMER_REPO}|${ORG_IDENTIFIER_PREFIX}|${ORG_PKGNAME_PREFIX}"' _ "$@"
}
rr_customer() { PATH="${CU_TMP}/stub:${PATH}" cu_env /bin/bash bin/run-recipes.sh "$@"; }
calls() { cat "${CU_TMP}/calls.log"; }

Describe 'customers in the shell tools'
    BeforeEach 'cu_setup'
    AfterEach 'cu_teardown'

    Describe 'resolve_customer'
        It 'sets the customer folder, repo and layered org naming'
            When call resolve widgets
            The status should be success
            The output should equal "widgets|${CU_WID}|${CU_WID}/output|com.example.widgets|Wid_"
        End

        It 'falls back to the default with no name'
            When call resolve ""
            The output should start with "widgets|"
        End

        It 'fails on an unknown name, listing the registered ones'
            When call resolve nope
            The status should be failure
            The stderr should include "registered: gadgets, widgets"
        End

        It 'with no registry, finds customer/<name> in the kit (a fresh clone)'
            rm "${CU_TMP}/customers.yaml"
            When call resolve acme
            The status should be success
            The output should start with "acme|$(pwd -P)/customer/acme|"
        End
    End

    Describe 'check-sanitized.sh'
        It "flags a customer's name outside its own folder, not inside it"
            cu_plant "${CU_WID}/README.md" "${W} house notes"
            cu_plant "${CU_KIT}/docs/leak.md" "made for ${W}"
            When call scan --root "${CU_KIT}"
            The status should be failure
            The output should include "docs/leak.md:1: [customer:widgets:1]"
            The output should not include "customer/widgets/README.md"
            The output should include "1 finding(s)"
        End

        It "applies an outside customer's patterns to the kit"
            cu_plant "${CU_KIT}/docs/leak.md" "see ${G}"
            When call scan --root "${CU_KIT}"
            The status should be failure
            The output should include "docs/leak.md:1: [customer:gadgets:1]"
        End

        It "never flags a customer's own .leak-patterns file"
            When call scan --root "${CU_KIT}"
            The status should be success
            The output should include "clean:"
        End

        It "--customer scans that folder with every other customer's patterns"
            cu_plant "${CU_GAD}/notes.md" "${G} only, and a mention of ${W}"
            When call scan --customer gadgets
            The status should be failure
            The output should include "notes.md:1: [customer:widgets:1]"
            The output should not include "[customer:gadgets"
        End

        It '--all-customers scans each in turn and exits with the worst code'
            cu_plant "${CU_GAD}/notes.md" "a mention of ${W}"
            When call scan --all-customers
            The status should equal 1
            The output should include "=== Customer: gadgets"
            The output should include "=== Customer: widgets"
            The output should include "[customer:widgets:1]"
        End

        It 'exits 2 for an unknown customer'
            When call scan --customer nope
            The status should equal 2
            The stderr should include "registered: gadgets, widgets"
        End
    End

    Describe 'analyze-materials.sh'
        It "reads the targets of a customer outside the kit"
            : > "${CU_TMP}/Tool-2.0.dmg"
            When call cu_env /bin/bash bin/analyze-materials.sh "${CU_TMP}" --customer gadgets
            The stderr should include "Scanning"
            The output should include "Wid/Tool (1 candidate)"
        End
    End

    Describe 'run-recipes.sh'
        It "--customer runs that customer's recipe repo"
            When call rr_customer --customer widgets
            The status should be success
            The output should include "Results: 1 passed, 0 failed, 0 skipped"
            The result of function calls should include "${CU_WID}/output/recipes/Wid/Tool/Tool.download.recipe.yaml"
        End

        It 'uses the default customer when no repo is given'
            When call rr_customer
            The status should be success
            The output should include "Results: 1 passed"
        End

        It '--repo beats the customer'
            When call rr_customer --customer widgets --repo "${CU_TMP}/elsewhere"
            The status should be failure
            The stderr should be present
        End
    End
End
