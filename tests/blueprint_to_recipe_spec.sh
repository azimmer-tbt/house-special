# shellcheck shell=sh disable=SC2016,SC2286,SC2287,SC2288

# bin/blueprint-to-recipe.sh: a blueprint from pkg-reverse.sh becomes a recipe pair
# that lints clean. Spec: specs/pkg-reverse/01-pkg-reverse.md (FR-15)

BP_TMP="/tmp/blueprint_to_recipe_spec"

bp_write() { # bp_write <name> <scripts>
    printf '%s\n' "app_name=TestApp" "source_pkg=/tmp/TestApp.pkg" \
        "source_pkg_basename=TestApp.pkg" "pkg_kind=component" "component_count=1" \
        "pkg_id=com.example.test" "version=1.0.0" "install_location=/" \
        "signature_status=unsigned" "signature_authority=" "payload_files=5" \
        "payload_dirs=2" "payload_size=1M" "scripts=$2" \
        "ownership_preserved=true" "chown_block_needed=false" > "${BP_TMP}/$1.conf"
}
bp_setup() {
    rm -rf "${BP_TMP}"; mkdir -p "${BP_TMP}"
    bp_write flat ""
    bp_write scripted "preinstall postinstall"
}
bp_teardown() { rm -rf "${BP_TMP}"; }
generate() { # generate <blueprint> -> recipe dir on stdout
    out="${BP_TMP}/$1/Acme/TestApp"
    bin/blueprint-to-recipe.sh --blueprint "${BP_TMP}/$1.conf" --out "${out}" >/dev/null 2>&1 || return 1
    printf '%s' "${out}"
}
lint() { bin/recipe-linter.sh --dir "$(generate "$1")" --pair-check 2>&1; }
download_input_version() {
    grep -A4 '^Input:' "$(generate flat)/TestApp.download.recipe.yaml" | grep -c 'version: "1.0.0"'
}
sidecars() { ls -A "$(generate flat)" | tr '\n' ' '; }
comments() { grep -h '^Comment: Pattern' "$(generate "$1")"/*.yaml | cut -d' ' -f1-3 | sort -u; }

Describe 'blueprint-to-recipe.sh'
    BeforeEach 'bp_setup'
    AfterEach 'bp_teardown'

    It 'writes a pair that lints clean'
        When call lint flat
        The status should be success
        The output should include "passed lint checks"
    End

    It 'pins version in the download recipe Input (VER-001)'
        When call download_input_version
        The output should eq "1"
    End

    It 'writes no .overrides or .autopkg_config'
        When call sidecars
        The output should eq "README.md TestApp.download.recipe.yaml TestApp.pkg.recipe.yaml "
    End

    It 'labels a flat payload 6a'
        When call comments flat
        The output should eq "Comment: Pattern 6a"
    End

    It 'labels a payload with scripts 6b'
        When call comments scripted
        The output should eq "Comment: Pattern 6b"
    End
End
