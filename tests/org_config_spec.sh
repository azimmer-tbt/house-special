# shellcheck shell=sh disable=SC2016,SC2286,SC2287,SC2288

# Org naming: config/org.yaml → ORG_* globals → {{TOKEN}} rendering → linter.

ORG_TMP="/tmp/org_config_spec"

make_org() {
    # make_org <name> <identifier_prefix> <pkgname_prefix>
    mkdir -p "${ORG_TMP}"
    {
        echo "org_name: \"Example Org\"   # trailing comment ignored"
        echo "identifier_prefix: $2"
        echo "pkgname_prefix: '$3'"
        echo "internal_domain: example.test"
    } > "${ORG_TMP}/$1.yaml"
}
org_setup() {
    make_org good "com.example.test" "Ex_"
    make_org badprefix "not a prefix" "Ex_"
    make_org emptypkg "com.example.test" ""
    make_org badmacos "com.example.test" "Ex_"
    echo 'fleet_min_macos: "Sonoma"' >> "${ORG_TMP}/badmacos.yaml"
}
org_teardown() { rm -rf "${ORG_TMP}"; }

Describe 'org config'
    Include lib/toolkit-common.sh
    BeforeAll 'org_setup'
    AfterAll 'org_teardown'

    reset_org() { ORG_CONFIG_FILE=""; }

    Describe 'read_org_config()'
        It 'loads the kit default (Acme)'
            reset_org
            unset AUTOPKG_TOOLKIT_ORG
            read_org_config
            When call printf '%s|%s|%s|%s|%s' "${ORG_NAME}" "${ORG_IDENTIFIER_PREFIX}" "${ORG_PKGNAME_PREFIX}" "${ORG_VENDOR_DIR}" "${ORG_FLEET_MIN_MACOS}"
            The output should eq "Acme Fruit Co.|com.acmefruit.autopkg|Acme_|AcmeFruitCo|14"
        End

        It 'strips quotes and trailing comments'
            read_org_config "${ORG_TMP}/good.yaml"
            When call printf '%s|%s|%s' "${ORG_NAME}" "${ORG_PKGNAME_PREFIX}" "${ORG_VENDOR_DIR}"
            The output should eq "Example Org|Ex_|Ex"
        End

        It 'escapes dots in the regex form'
            read_org_config "${ORG_TMP}/good.yaml"
            When call printf '%s' "${ORG_IDENTIFIER_PREFIX_RE}"
            The output should eq 'com\.example\.test'
        End

        It 'honours $AUTOPKG_TOOLKIT_ORG'
            reset_org
            AUTOPKG_TOOLKIT_ORG="${ORG_TMP}/good.yaml"
            read_org_config
            When call printf '%s' "${ORG_IDENTIFIER_PREFIX}"
            The output should eq "com.example.test"
        End

        It 'rejects a non reverse-DNS identifier_prefix'
            When call read_org_config "${ORG_TMP}/badprefix.yaml"
            The status should be failure
            The stderr should include "must be reverse-DNS"
        End

        It 'rejects an empty pkgname_prefix'
            When call read_org_config "${ORG_TMP}/emptypkg.yaml"
            The status should be failure
            The stderr should include "pkgname_prefix"
        End

        It 'leaves fleet_min_macos empty when not set (it is optional)'
            read_org_config "${ORG_TMP}/good.yaml"
            When call printf '[%s]' "${ORG_FLEET_MIN_MACOS}"
            The output should eq "[]"
        End

        It 'rejects a fleet_min_macos that is not a version'
            When call read_org_config "${ORG_TMP}/badmacos.yaml"
            The status should be failure
            The stderr should include "fleet_min_macos"
        End

        It 'fails on a missing file'
            When call read_org_config "${ORG_TMP}/nope.yaml"
            The status should be failure
            The stderr should include "org config not found"
        End
    End

    Describe 'org_render()'
        It 'substitutes every token'
            read_org_config "${ORG_TMP}/good.yaml"
            When call org_render '{{ORG_NAME}} {{IDENTIFIER_PREFIX}} {{PKGNAME_PREFIX}} {{INTERNAL_DOMAIN}} {{VENDOR_DIR}}'
            The output should eq "Example Org com.example.test Ex_ example.test Ex"
        End

        It 'renders the regex forms with single and doubled backslashes'
            read_org_config "${ORG_TMP}/good.yaml"
            When call org_render '{{IDENTIFIER_PREFIX_RE}} {{IDENTIFIER_PREFIX_RE_YAML}}'
            The output should eq 'com\.example\.test com\\.example\\.test'
        End

        It 'passes token-free text through unchanged'
            When call org_render 'plain text \\. with {braces}'
            The output should eq 'plain text \\. with {braces}'
        End
    End
End

Describe 'recipe-linter.sh --org'
    BeforeAll 'org_setup'
    AfterAll 'org_teardown'

    # The bare fixtures lack .overrides/.autopkg_config companions, so the run
    # exits non-zero regardless; assert on the naming rules only.
    It 'passes the naming rules on the Acme fixtures under the default org'
        When run script bin/recipe-linter.sh tests/fixtures/linter/ExampleApp.download.recipe.yaml tests/fixtures/linter/ExampleApp.pkg.recipe.yaml
        The output should include "org naming from:"
        The output should not include "IDN-001"
        The output should not include "IDN-002"
        The output should not include "PKG-002"
        The status should be failure
    End

    It 'fails IDN-001 on the Acme fixtures under a different org'
        When run script bin/recipe-linter.sh --org "${ORG_TMP}/good.yaml" tests/fixtures/linter/ExampleApp.download.recipe.yaml
        The output should include "IDN-001"
        The status should be failure
    End

    It 'fails PKG-002 on the Acme pkg fixture under a different org'
        When run script bin/recipe-linter.sh --org "${ORG_TMP}/good.yaml" tests/fixtures/linter/ExampleApp.pkg.recipe.yaml
        The output should include "PKG-002"
        The status should be failure
    End

    It 'lists rules with the org values filled in'
        When run script bin/recipe-linter.sh --org "${ORG_TMP}/good.yaml" --list-rules
        The output should include "com.example.test.download.AppName"
        The output should not include "{{"
    End
End
