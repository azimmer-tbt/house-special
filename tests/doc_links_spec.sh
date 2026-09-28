# shellcheck shell=sh disable=SC2016,SC2286,SC2287,SC2288

# bin/check-doc-links.sh — and the kit's own docs must pass it.

DL_TMP="/tmp/doc_links_spec"

dl_setup() {
    rm -rf "${DL_TMP}"
    mkdir -p "${DL_TMP}/docs" "${DL_TMP}/bin"
    : > "${DL_TMP}/bin/tool.sh"
    : > "${DL_TMP}/docs/other.md"
    cat > "${DL_TMP}/docs/page.md" <<'MD'
See [other](other.md) and [tool](../bin/tool.sh) and `bin/tool.sh`.
Placeholders are ignored: `bin/<tool>.sh`, [x](https://example.com).

```bash
bin/not-checked-inside-code-fence.sh
```
MD
}
dl_teardown() { rm -rf "${DL_TMP}"; }

Describe 'check-doc-links.sh'
    BeforeEach 'dl_setup'
    AfterEach 'dl_teardown'

    It 'passes when every reference resolves'
        When run script bin/check-doc-links.sh --root "${DL_TMP}"
        The status should be success
        The output should include "links ok: 3 reference(s)"
    End

    It 'reports a broken relative link with file and line'
        echo "Broken [link](missing.md)" >> "${DL_TMP}/docs/page.md"
        When run script bin/check-doc-links.sh --root "${DL_TMP}"
        The status should be failure
        The output should include "docs/page.md:7: missing missing.md"
    End

    It 'reports a broken backticked repo path'
        echo 'Run `bin/gone.sh` first.' >> "${DL_TMP}/docs/other.md"
        When run script bin/check-doc-links.sh --root "${DL_TMP}"
        The status should be failure
        The output should include "docs/other.md:1: missing bin/gone.sh"
    End

    It 'lets a line marked (planned) name a path that does not exist yet'
        echo 'The model will live in `bin/future.sh` (planned).' >> "${DL_TMP}/docs/other.md"
        When run script bin/check-doc-links.sh --root "${DL_TMP}"
        The status should be success
        The output should include "links ok: 3 reference(s)"
    End

    It 'skips a backticked local-only file but reports a link to it'
        echo 'Your registry is `config/customers.yaml`; see `reference/autopkg-wiki/FAQ.md`.' >> "${DL_TMP}/docs/other.md"
        echo 'See [registry](../config/customers.yaml).' >> "${DL_TMP}/docs/other.md"
        When run script bin/check-doc-links.sh --root "${DL_TMP}"
        The status should be failure
        The output should include "docs/other.md:2: missing ../config/customers.yaml"
        The output should not include "docs/other.md:1:"
    End
End
