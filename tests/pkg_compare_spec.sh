# shellcheck shell=sh disable=SC2016,SC2286,SC2287,SC2288

# bin/pkg-compare.sh as a command: arguments, exit codes and work-dir cleanup, on
# packages built here with pkgbuild. Each mismatch kind is unit-tested in
# tests/python/test_pkg.py. Spec: specs/pkg-compare/01-pkg-compare.md

PC_TMP="/tmp/pkg_compare_spec"

pc_setup() {
    rm -rf "${PC_TMP}"
    mkdir -p "${PC_TMP}/root/Library/My Dir"
    echo "hi" > "${PC_TMP}/root/Library/My Dir/a file.txt"
    pkgbuild --quiet --root "${PC_TMP}/root" --identifier com.example.a --version 1 "${PC_TMP}/a.pkg"
    pkgbuild --quiet --root "${PC_TMP}/root" --identifier com.example.a --version 2 "${PC_TMP}/b.pkg"
    pkgbuild --quiet --root "${PC_TMP}/root" --identifier com.example.a --version 1 \
        --ownership preserve "${PC_TMP}/mine.pkg"
}
pc_teardown() {
    [ -f "${PC_TMP}/log" ] && rm -rf "$(work_dir)"
    rm -rf "${PC_TMP}"
}
pc() { /bin/bash bin/pkg-compare.sh "$@"; }
work_dir() { sed -n 's/^  work dir left for inspection: //p' "${PC_TMP}/log"; }

Describe 'pkg-compare.sh'
    It 'AC-1.1: requires both packages'
        When call pc --old-pkg /tmp/x.pkg
        The status should eq 2
        The stderr should include "--new-pkg is required"
    End

    It 'rejects unknown options'
        When call pc --bogus
        The status should eq 2
        The stderr should include "Unknown option: --bogus"
    End

    Describe 'on real packages'
        BeforeEach 'pc_setup'
        AfterEach 'pc_teardown'

        It 'AC-3.1: a version difference is reported but passes'
            When call pc --old-pkg "${PC_TMP}/a.pkg" --new-pkg "${PC_TMP}/b.pkg"
            The status should be success
            The output should include "MISMATCH: version differs"
            The output should include "Packages are equivalent"
        End

        It 'AC-5.2: directory ownership and spaced paths are compared (KI-4)'
            When call pc --old-pkg "${PC_TMP}/a.pkg" --new-pkg "${PC_TMP}/mine.pkg" --work-dir "${PC_TMP}/w"
            The status should eq 2
            The output should include "    Library/My Dir
      old: drwxr-xr-x:0:0"
            The output should include "Library/My Dir/a file.txt"
            The output should include "work dir kept: /private${PC_TMP}/w"
        End

        It 'AC-7.1: keeps its own work dir on failure'
            pc --old-pkg "${PC_TMP}/a.pkg" --new-pkg "${PC_TMP}/mine.pkg" > "${PC_TMP}/log" 2>&1 || true
            When call work_dir
            The output should start with "/"
            The path "$(work_dir)" should be directory
        End
    End
End
