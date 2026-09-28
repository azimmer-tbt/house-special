# shellcheck shell=sh disable=SC2016,SC2286,SC2287,SC2288

# Repository hygiene that is easy to lose in a copy or a merge.

Describe 'kit hygiene'
    non_executable_frontends() {
        find bin -maxdepth 1 -type f \( -name '*.sh' -o -name '*.py' \) ! -perm -u+x -print
    }
    org_literals_in_kit() {
        # Kit logic must stay org-neutral; config/org.yaml is the one exception.
        # Comments and help text may use the Acme example values.
        grep -rnE 'com\.acmefruit|Acme_' bin lib config \
            --include='*.sh' --include='*.py' --include='checks.yaml' 2>/dev/null \
            | grep -vE '^[^:]+:[0-9]+:[[:space:]]*#'
    }

    python_shebangs() {
        # Python tools run AutoPkg's bundled interpreter (it always has PyYAML).
        for f in bin/*.py guardrails/audit/*.py; do
            [ "$(head -1 "$f")" = "#!/usr/local/autopkg/python" ] || echo "$f"
        done
    }
    bare_python_calls() {
        # Shell scripts go through tk_python, never a bare python3 from PATH.
        grep -nE '(^|[^A-Za-z_./-])python3 ' bin/*.sh lib/*.sh | grep -vE '^[^:]+:[0-9]+:[[:space:]]*#'
    }

    python_style() {
        # .devagent/standards/python-code-standards.md: black, isort, flake8,
        # all bundled with AutoPkg's Python.
        set -- bin/*.py guardrails/audit
        [ -d lib/python ] && set -- "$@" lib/python
        [ -d tests/python ] && set -- "$@" tests/python
        . lib/toolkit-common.sh
        tk_python -m black --check -q "$@" 2>&1 || echo "black: run tk_python -m black on the files above"
        tk_python -m isort --check-only -q --profile black "$@" 2>&1
        tk_python -m flake8 --max-line-length 88 --extend-ignore E203 "$@" 2>&1
    }

    It 'Python code passes black, isort and flake8'
        When call python_style
        The output should eq ""
    End

    env_bash_shebangs() {
        # Bash scripts target the system bash 3.2; env would pick whatever bash
        # is first on PATH (often Homebrew's 5.x).
        find bin lib customer templates -type f \
            -exec grep -l '^#!/usr/bin/env bash' {} + 2>/dev/null || true
    }

    It 'bash scripts use #!/bin/bash, not env'
        When call env_bash_shebangs
        The output should eq ""
    End

    It 'every Python tool uses the AutoPkg Python shebang'
        When call python_shebangs
        The output should eq ""
    End

    It 'no shell script calls a bare python3'
        When call bare_python_calls
        The output should eq ""
        The status should be failure
    End

    It 'every bin/ front end is executable'
        When call non_executable_frontends
        The output should eq ""
    End

    It 'scripts and checks.yaml carry no literal org naming outside comments'
        When call org_literals_in_kit
        The output should eq ""
        The status should be failure
    End
End
