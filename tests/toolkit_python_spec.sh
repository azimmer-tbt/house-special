# shellcheck shell=sh disable=SC2016,SC2286,SC2287,SC2288

# lib/toolkit-common.sh: toolkit_python_path / tk_python — the toolkit runs
# AutoPkg's bundled Python (which always has PyYAML) unless overridden.

Describe 'toolkit Python'
    Include lib/toolkit-common.sh

    reset_python() { TOOLKIT_PYTHON=""; unset AUTOPKG_TOOLKIT_PYTHON; }
    BeforeEach 'reset_python'

    Skip if 'AutoPkg is not installed' test ! -x /usr/local/autopkg/python

    It "defaults to AutoPkg's interpreter"
        When call toolkit_python_path
        The output should eq "/usr/local/autopkg/python"
    End

    It 'has PyYAML available through tk_python'
        When call tk_python -c 'import yaml; print("yaml ok")'
        The output should eq "yaml ok"
    End

    It 'honours AUTOPKG_TOOLKIT_PYTHON'
        AUTOPKG_TOOLKIT_PYTHON=/usr/bin/python3
        When call toolkit_python_path
        The output should eq "/usr/bin/python3"
    End

    It 'fails clearly when the override is not executable'
        AUTOPKG_TOOLKIT_PYTHON=/nonexistent/python
        When call tk_python -c 'pass'
        The status should eq 127
        The stderr should include "AUTOPKG_TOOLKIT_PYTHON is set but not executable"
    End
End
