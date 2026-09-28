# shellcheck shell=sh disable=SC2016,SC2286,SC2287,SC2288

# bin/pkg-reverse.sh as a command: arguments, exit codes and the output tree, on
# packages built here with pkgbuild/productbuild (no root needed). The logic (BOM
# parsing, the chown rollup, name sanitising) is unit-tested in
# tests/python/test_pkg.py. Spec: specs/pkg-reverse/01-pkg-reverse.md

PR_TMP="/tmp/pkg_reverse_spec"

pr_setup() {
    rm -rf "${PR_TMP}"
    mkdir -p "${PR_TMP}/root/Applications/Example.app/Contents" "${PR_TMP}/scripts"
    echo "test" > "${PR_TMP}/root/Applications/Example.app/Contents/Info.plist"
    printf '#!/bin/sh\nexit 0\n' > "${PR_TMP}/scripts/postinstall"
    chmod 644 "${PR_TMP}/scripts/postinstall"   # pkg-reverse makes it executable
    pkgbuild --quiet --root "${PR_TMP}/root" --scripts "${PR_TMP}/scripts" \
        --identifier com.example.test --version 1.0.0 --install-location / \
        "${PR_TMP}/My Test_App.pkg"
    pkgbuild --quiet --root "${PR_TMP}/root" --identifier com.example.two \
        --version 1 "${PR_TMP}/two.pkg"
    productbuild --quiet --package "${PR_TMP}/My Test_App.pkg" \
        --package "${PR_TMP}/two.pkg" "${PR_TMP}/multi.pkg"
}
pr_teardown() { rm -rf "${PR_TMP}"; }
pr() { /bin/bash bin/pkg-reverse.sh "$@"; }
reverse() { pr "${PR_TMP}/My Test_App.pkg" --dest "${PR_TMP}/out" --allow-unprivileged "$@"; }
out() { echo "${PR_TMP}/out/My-Test-App"; }
blueprint_keys() { grep -v '^#' "$(out)/blueprint.conf" | grep . | cut -d= -f1 | tr '\n' ' '; }

Describe 'pkg-reverse.sh'
    Describe 'arguments'
        It 'AC-01.6: --help prints the usage block'
            When call pr --help
            The status should be success
            The output should include "Usage:"
            The output should include "--dest"
        End

        It 'AC-01.7: rejects unknown options'
            When call pr --bogus-flag
            The status should eq 2
            The stderr should include "Unknown option: --bogus-flag"
        End

        It 'AC-01.2: requires --dest'
            When call pr /tmp/some.pkg
            The status should eq 2
            The stderr should include "--dest is required"
        End

        It 'AC-01.3: requires a package'
            When call pr --dest /tmp/out
            The status should eq 2
            The stderr should include "No package specified"
        End

        It 'AC-14.2 / AC-02.3: rejects a missing file or a bundle-style directory'
            When call pr /tmp --dest /tmp/out
            The status should eq 2
            The stderr should include "Not a file: /tmp"
        End

        It 'AC-13.6 / AC-13.7: flags without a value exit 2'
            When call pr /tmp/x.pkg --dest /tmp/out --name
            The status should eq 2
            The stderr should include "--name requires a value"
        End
    End

    Describe 'on real packages'
        BeforeEach 'pr_setup'
        AfterEach 'pr_teardown'

        It 'AC-01.5 / AC-04.3: refuses to run unprivileged without the override'
            Skip if "running as root" [ "$(id -u)" -eq 0 ]
            When call pr "${PR_TMP}/two.pkg" --dest "${PR_TMP}/out"
            The status should eq 2
            The stderr should include "sudo"
            The stderr should include "--allow-unprivileged"
        End

        It 'AC-13.1 / AC-12: builds the tree and prints the summary'
            When call reverse
            The status should be success
            The stderr should include "ownership NOT preserved"
            The output should include "payload/"
            The output should include "chown-entries.txt"
            The output should include "bin/blueprint-to-recipe.sh --blueprint $(out)/blueprint.conf"
            The path "$(out)/payload/Applications/Example.app/Contents/Info.plist" should be file
            The path "$(out)/scripts/postinstall" should be executable
            The path "$(out)/.expanded" should not be exist
        End

        It 'AC-10.3: chown entries carry numeric uid:gid (KI-4)'
            reverse >/dev/null 2>&1
            When call grep -c '^OWN	Applications	0:0$' "$(out)/chown-entries.txt"
            The output should eq 1
        End

        It 'AC-15.2 / AC-15.3: blueprint.conf has exactly the documented keys'
            reverse >/dev/null 2>&1
            When call blueprint_keys
            The output should eq "app_name source_pkg source_pkg_basename pkg_kind component_count pkg_id version install_location signature_status signature_authority payload_files payload_dirs payload_size scripts ownership_preserved chown_block_needed "
        End

        It 'AC-01.4: --name picks the output folder'
            When call reverse --name Custom
            The status should be success
            The stderr should be present
            The output should include "${PR_TMP}/out/Custom/"
            The path "${PR_TMP}/out/Custom/blueprint.conf" should be file
        End

        It 'AC-14.1: an existing output folder exits 2'
            reverse >/dev/null 2>&1
            When call reverse
            The status should eq 2
            The output should include "Reverse-engineering"
            The stderr should include "Output already exists"
        End

        It 'AC-03.3 / AC-13.5: a multi-component distribution exits 3'
            When call pr "${PR_TMP}/multi.pkg" --dest "${PR_TMP}/out" --allow-unprivileged
            The status should eq 3
            The output should include "My Test_App.pkg"
            The stderr should include "2 components"
        End
    End
End
