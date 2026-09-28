# shellcheck shell=sh disable=SC2016,SC2286,SC2287,SC2288

# bin/check-sanitized.sh against a throwaway tree with planted leaks.

CS_ROOT="/tmp/check_sanitized_spec"

# Planted leaks are assembled from pieces so this spec doesn't trip the very
# guard it tests when the whole tree is scanned.
U='/Users'; C='CHG'; S='Serial'; O='One'

cs_setup() {
    rm -rf "${CS_ROOT}"
    mkdir -p "${CS_ROOT}/docs" "${CS_ROOT}/tests/fixtures" "${CS_ROOT}/reference/autopkg-wiki"
    echo "Nothing to see here." > "${CS_ROOT}/docs/clean.md"
    echo "Copyright (c) 2026 Pat Example" > "${CS_ROOT}/LICENSE"
    echo "Examples use /Users/Shared and /Users/you/Downloads." > "${CS_ROOT}/docs/placeholders.md"
    echo "Page with ${U}/realperson/path" > "${CS_ROOT}/reference/autopkg-wiki/page.md"
    : > "${CS_ROOT}/tests/fixtures/fixture.pkg"
}
cs_teardown() { rm -rf "${CS_ROOT}"; }

plant() { # plant <relpath> <content>
    mkdir -p "$(dirname "${CS_ROOT}/$1")"
    printf '%s\n' "$2" > "${CS_ROOT}/$1"
}

Describe 'check-sanitized.sh'
    BeforeEach 'cs_setup'
    AfterEach 'cs_teardown'

    It 'passes a clean tree and reports the wiki skip'
        When run script bin/check-sanitized.sh --root "${CS_ROOT}"
        The status should be success
        The output should include "clean:"
        The output should include "skipped: reference/autopkg-wiki"
    End

    It 'flags a real home-directory path but not placeholders'
        plant docs/leak.md "see ${U}/jdoe42/Documents"
        When run script bin/check-sanitized.sh --root "${CS_ROOT}"
        The status should be failure
        The output should include "docs/leak.md:1: [home-path] ${U}/jdoe42"
        The output should not include "placeholders.md"
    End

    It 'matches placeholder names whole, so a real name that starts with one is flagged (KI-25)'
        plant docs/prefix.md "see ${U}/melissa/Documents and ${U}/adminbob, not ${U}/me/x or ${U}/you."
        When run script bin/check-sanitized.sh --root "${CS_ROOT}"
        The status should be failure
        The output should include "[home-path] ${U}/melissa"
        The output should include "[home-path] ${U}/adminbob"
        The output should include "2 finding(s)"
    End

    It 'flags ticket numbers, serials and OneDrive paths'
        plant notes.md "approved in ${C}1234567
${S} Number- 1234567890--P
${O}Drive-ExampleCorp/Shared"
        When run script bin/check-sanitized.sh --root "${CS_ROOT}"
        The status should be failure
        The output should include "[ticket]"
        The output should include "[serial]"
        The output should include "[onedrive]"
    End

    It 'flags installers outside tests/fixtures only'
        : > "${CS_ROOT}/docs/App.dmg"
        When run script bin/check-sanitized.sh --root "${CS_ROOT}"
        The status should be failure
        The output should include "docs/App.dmg:0: [binary]"
        The output should not include "fixture.pkg"
    End

    It 'flags files over --max-kb'
        dd if=/dev/zero of="${CS_ROOT}/docs/big.bin" bs=1024 count=3 2>/dev/null
        When run script bin/check-sanitized.sh --root "${CS_ROOT}" --max-kb 2
        The status should be failure
        The output should include "[large-file]"
    End

    It 'applies denylist patterns, exempting LICENSE and --allow files'
        printf '# comment\n\n[Ee]xample[Cc]orp\nPat Example\n' > "${CS_ROOT}/.leak-patterns"
        plant docs/a.md "made by ExampleCorp"
        plant docs/b.md "made by examplecorp too"
        plant docs/c.md "Pat Example wrote this"
        When run script bin/check-sanitized.sh --root "${CS_ROOT}" --allow docs/c.md
        The status should be failure
        The output should include "docs/a.md:1: [denylist:1]"
        The output should include "docs/b.md:1: [denylist:1]"
        The output should not include "LICENSE"
        The output should not include "docs/c.md"
        The output should not include ".leak-patterns:"
    End

    It 'exempts lines matching a ! exemption, but only those lines'
        printf 'Pat Example\n!^# Author: Pat Example <pat@example\\.com>$\n' > "${CS_ROOT}/.leak-patterns"
        plant bin/tool.sh "#!/bin/bash
# Author: Pat Example <pat@example.com>
echo 'Pat Example was here'"
        When run script bin/check-sanitized.sh --root "${CS_ROOT}"
        The status should be failure
        The output should include "bin/tool.sh:3: [denylist:1]"
        The output should not include "bin/tool.sh:2:"
        The output should include "1 denylist pattern(s)"
    End

    It "skips a worktree's .git file, which holds the main repo's path"
        printf 'gitdir: %s/jdoe42/src/kit/.git/worktrees/x\n' "${U}" > "${CS_ROOT}/.git"
        When run script bin/check-sanitized.sh --root "${CS_ROOT}"
        The status should be success
        The output should include "clean:"
    End

    It 'limits the scan with --path'
        plant bin/leak.sh "# ${U}/jdoe42"
        When run script bin/check-sanitized.sh --root "${CS_ROOT}" --path docs
        The status should be success
        The output should include "clean:"
    End

    It 'scans only staged files with --staged'
        git -C "${CS_ROOT}" init -q
        plant docs/staged.md "${C}7654321"
        plant docs/unstaged.md "${C}1111111"
        git -C "${CS_ROOT}" add docs/staged.md
        When run script bin/check-sanitized.sh --root "${CS_ROOT}" --staged
        The status should be failure
        The output should include "docs/staged.md"
        The output should not include "unstaged.md"
    End

    It 'installs a pre-commit hook and refuses to overwrite one'
        git -C "${CS_ROOT}" init -q
        bin/check-sanitized.sh --root "${CS_ROOT}" --install-hook >/dev/null
        When run script bin/check-sanitized.sh --root "${CS_ROOT}" --install-hook
        The status should equal 2
        The stderr should include "already exists"
        The path "${CS_ROOT}/.git/hooks/pre-commit" should be executable
    End

    It 'rejects unknown options'
        When run script bin/check-sanitized.sh --bogus
        The status should equal 2
        The stderr should include "Unknown option"
    End
End
