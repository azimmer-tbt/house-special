---
name: shellspec
description: Write and debug ShellSpec tests for Bash scripts in this project. Use this skill when writing *_spec.sh files, debugging test failures, or adding test coverage for shell script functions. In this repo specs live in tests/*_spec.sh and run under /bin/bash 3.2 via .shellspec; run `shellspec` (or `shellspec tests/<name>_spec.sh`). Tests must pass before merge.
---

# ShellSpec Testing Framework

ShellSpec is a BDD unit testing framework for shell scripts. Use this skill when writing tests for Bash/shell scripts in this project.

## Project Setup (this repository)

```
.shellspec                 # --default-path tests, --helperdir tests, --shell /bin/bash
tests/
├── spec_helper.sh         # global helpers (fixture paths)
├── fixtures/<area>/       # static fixtures — no real org data, ever
└── <tool>_spec.sh         # one spec file per tool or area
```

- `--shell /bin/bash` makes every example run under **stock macOS bash 3.2**, the
  shell the tools must support. Don't change it to a Homebrew bash: that hid a
  real portability bug once.
- Paths in specs are relative to the repo root (`Include bin/recipe-linter.sh`,
  `When run script bin/check-sanitized.sh`).
- Build throwaway trees under `/tmp/<spec_name>` in `BeforeAll`/`BeforeEach` and
  remove them in `AfterAll`/`AfterEach`. Packages can be built on the fly with the
  stock `pkgbuild` (see `tests/analyze_package_spec.sh`).
- A spec that plants "leaks" to test `bin/check-sanitized.sh` must assemble them
  from pieces (`U='/Users'; "${U}/jdoe"`) so the whole-tree scan stays clean.
- Tools that print progress on stderr: assert it (`The stderr should include …`)
  or the example reports a warning.

## Specfile Structure

### Basic Template
```bash
# shellcheck shell=sh disable=SC2016,SC2286,SC2287,SC2288

Describe 'mylib.sh'
    Include lib/mylib.sh  # Source the file to test functions directly

    Describe 'my_function()'
        It 'returns expected output'
            When call my_function "arg1" "arg2"
            The output should eq "expected output"
            The status should be success
        End
    End
End
```

### Testing Functions Directly (Preferred Pattern)

Source the script with `Include` to bring functions into the test namespace, then call them directly:

```bash
Describe 'utils.sh'
    Include lib/utils.sh

    Describe 'is_number()'
        Parameters
            "123"     success
            "-123"    failure
            "12.3"    failure
            ""        failure
        End

        It 'validates numbers'
            When call is_number "$1"
            The status should be "$2"
        End
    End

    Describe 'trim_string()'
        It 'removes leading and trailing whitespace'
            When call trim_string "  hello world  "
            The output should eq "hello world"
        End
    End
End
```

### Preventing Main Execution When Sourcing

Add this guard to scripts so `Include` can source without executing main:

```bash
#!/bin/bash
# myscript.sh

my_function() {
    echo "Hello $1"
}

# Return early if sourced for testing
${__SOURCED__:+return}

# Main execution
my_function "$@"
```

## DSL Reference

### Example Groups
```bash
Describe 'description'    # Groups related tests
Context 'when condition'  # Alias for Describe, used for context
ExampleGroup 'name'       # Alias for Describe
```

### Examples
```bash
It 'does something'       # Single test case
Specify 'behavior'        # Alias for It
Example 'case'            # Alias for It
Todo 'not implemented'    # Pending example placeholder
```

### Evaluation (When)

#### call - Call shell function (no subshell)
```bash
When call my_function arg1 arg2
```

#### run - Run command (in subshell)
```bash
When run my_command arg1 arg2
When run command external_cmd    # External command only
When run script ./myscript.sh    # Run script (ignores shebang)
When run source ./myscript.sh    # Source script (allows mocking)
```

### Expectations (The)

#### Subjects
```bash
The output should eq "value"     # stdout
The stdout should eq "value"     # alias for output
The error should eq "value"      # stderr
The stderr should eq "value"     # alias for error
The status should eq 0           # exit status
The variable VAR should eq "x"   # variable value
The path "/tmp/file" should exist
The value "$var" should eq "x"   # arbitrary value
```

#### Modifiers
```bash
The line 2 of output should eq "second line"
The word 1 of output should eq "first"
The length of output should eq 10
The lines of output should eq 5
The first line of output should eq "header"
The second word of line 3 of output should eq "value"
```

#### Matchers
```bash
# String matchers
The output should eq "exact match"
The output should equal "exact match"    # alias
The output should start with "prefix"
The output should end with "suffix"
The output should include "substring"
The output should match pattern "*glob*"

# Status matchers
The status should be success             # exit 0
The status should be failure             # exit non-zero
The status should eq 0
The status should not eq 0

# Variable matchers
The variable VAR should be defined
The variable VAR should be undefined
The variable VAR should be present       # defined and non-empty
The variable VAR should be blank         # empty or undefined

# File matchers
The path "/tmp/file" should exist
The path "/tmp/file" should be file
The path "/tmp/file" should be directory
The path "/tmp/file" should be empty file
The file "/tmp/file" should be readable
```

#### Negation
```bash
The output should not eq "wrong"
The status should not be success
```

## Parameterized Tests

### Basic Parameters
```bash
Describe 'add()'
    Parameters
        1 2 3
        5 5 10
        0 0 0
    End

    It "adds $1 + $2 = $3"
        When call add "$1" "$2"
        The output should eq "$3"
    End
End
```

### Parameters:value (single values)
```bash
Parameters:value "apple" "banana" "cherry"

It "processes $1"
    When call process "$1"
    The status should be success
End
```

### Parameters:matrix (combinations)
```bash
Parameters:matrix
    "small" "medium" "large"
    "red" "green" "blue"
End
# Generates: small/red, small/green, small/blue, medium/red, ...
```

## Hooks

```bash
Describe 'with hooks'
    BeforeAll 'setup_once'
    AfterAll 'cleanup_once'
    BeforeEach 'setup'          # Before each example
    AfterEach 'cleanup'         # After each example (use Before/After in older versions)

    setup_once() { mkdir -p /tmp/test; }
    cleanup_once() { rm -rf /tmp/test; }
    setup() { touch /tmp/test/file; }
    cleanup() { rm -f /tmp/test/file; }

    It 'runs test'
        # ...
    End
End
```

## Skip and Pending

```bash
Describe 'conditional tests'
    # Skip unconditionally
    Skip "reason"

    # Skip conditionally
    not_on_macos() { [ "$(uname)" != "Darwin" ]; }
    Skip if "not on macOS" not_on_macos

    # Pending (test expected to fail)
    Pending "not implemented yet"

    # Prefix to skip
    xIt 'skipped example'
    End

    # Prefix to focus (run only these with --focus)
    fIt 'focused example'
    End
End
```

## Mocking

### Function-based Mock
```bash
Describe 'with mock'
    # Redefine function within scope
    date() {
        echo "2024-01-01"
    }

    It 'uses mocked date'
        When call get_current_date
        The output should eq "2024-01-01"
    End
End
```

### Command-based Mock
```bash
Describe 'command mock'
    Mock curl
        echo '{"status": "ok"}'
    End

    It 'uses mocked curl'
        When call fetch_data
        The output should include "ok"
    End
End
```

## Data Helper

```bash
Describe 'data input'
    It 'processes stdin'
        Data
            #|line1
            #|line2
            #|line3
        End
        When call process_lines
        The lines of output should eq 3
    End

    It 'uses expandable data'
        Data:expand
            #|value is ${VALUE}
        End
        When call cat
        The output should eq "value is ${VALUE}"
    End
End
```

## Directives

```bash
# Constants (evaluated at translation time)
% FIXTURE: "$SHELLSPEC_HELPERDIR/fixture"
% CONSTANT: "some value"

# Text blocks
output() {
    %text
    #|line 1
    #|line 2
}

# Preserve variables from subshell
AfterRun 'preserve() { %preserve result; }'
```

## spec_helper.sh Template

```bash
#shellcheck shell=sh

set -eu

spec_helper_precheck() {
    minimum_version "0.28.0"
    # Abort if requirements not met
    # if [ "$SHELL_TYPE" != "bash" ]; then
    #     abort "Only bash is supported"
    # fi
}

spec_helper_loaded() {
    # Called after ShellSpec internals loaded
    # Set IFS, shell options, etc.
}

spec_helper_configure() {
    # Import custom matchers
    # import 'support/custom_matcher'

    # Global hooks
    # before_each "global_setup"
    # after_each "global_cleanup"

    # Helper functions available to all specs
    not_on_ci() { [ -z "${CI:-}" ]; }
}
```

## Running Tests

```bash
# Run all tests
shellspec

# Run specific file
shellspec tests/org_config_spec.sh

# Run specific line
shellspec tests/org_config_spec.sh:42

# Run with specific shell
shellspec --shell bash
shellspec --shell zsh

# Run focused tests only
shellspec --focus

# Quick mode (run failed tests first)
shellspec --quick

# Parallel execution
shellspec --jobs 4

# Dry run
shellspec --dry-run

# Syntax check only
shellspec --syntax-check
```

## Best Practices

### Project-specific

- **Look rules up by ID, not list position**, when testing the linter (Python
  tests in `tests/python/test_lint.py` find a rule by its `id`). Rule order in
  `config/checks.yaml` is not an interface.
- **Every shipped example must lint clean** — `tests/examples_lint_spec.sh` is
  parameterized over them; add new examples there.
- Test **your** logic: parameter validation, edge cases, the failure paths. Don't
  re-test `tk_*` logging helpers.

### General Best Practices

1. **Test functions directly**: Use `Include` to source scripts and call functions with `When call function_name`

2. **Use `${__SOURCED__:+return}`** in scripts to prevent main execution when sourced for testing

3. **One spec file per tool or area**: `bin/<tool>.sh` → `tests/<tool>_spec.sh`

4. **Use Parameters for data-driven tests**: Reduce duplication with parameterized examples

5. **Keep spec_helper minimal**: Only global configuration and shared helpers

6. **Use descriptive example names**: `It 'returns error when input is empty'`

7. **One assertion per example when possible**: Makes failures easier to diagnose

8. **Use `Context` for different scenarios**:
```bash
Describe 'process_file()'
    Context 'when file exists'
        # ...
    End
    Context 'when file is missing'
        # ...
    End
End
```
