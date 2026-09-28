# shellcheck shell=sh disable=SC2016,SC2286,SC2287,SC2288

# bin/classify-recipe.sh is a front end for recipekit.classify: it must always reach
# a verdict, pass its arguments through, and keep the exit codes. Classification
# accuracy is tested in tests/python/test_classify.py (AC-5.1, AC-5.2).

Describe 'classify-recipe.sh'
    Parameters
        "templates/pattern-4-vendor-drop/example-Xerox-Drivers"
        "templates/pattern-6d-rebuilt-payloadless/example-UninstallAgent"
        "templates/pattern-7-faux-vendor-dmg/example-Pomelo-Studio"
        "customer/acme/output/recipes/MoonlightGameStreaming/Moonlight"
        "customer/acme/output/recipes/Corkscrews/Fruit-Screensaver"
    End

    It "prints a classification for $1"
        When run script bin/classify-recipe.sh "$1"
        The output should include "Classification: Pattern"
        The status should be success
    End

    It 'classifies a GitHub release DMG recipe as 2b'
        When run script bin/classify-recipe.sh customer/acme/output/recipes/MoonlightGameStreaming/Moonlight
        The output should include "Classification: Pattern 2b"
    End

    It 'passes --output json through (AC-5.3)'
        When run script bin/classify-recipe.sh --output json customer/acme/output/recipes/OrchardLabs/Orchard-Analytics-License
        The output should include '"classification": "6c"'
        The output should include '"matches_claim": true'
        The status should be success
    End

    It 'exits 1 for a folder without a recipe pair'
        When run script bin/classify-recipe.sh templates
        The status should eq 1
        The stderr should include "no download/pkg recipe pair"
    End

    It 'exits 2 on a usage error'
        When run script bin/classify-recipe.sh
        The status should eq 2
        The stderr should include "usage"
    End
End
