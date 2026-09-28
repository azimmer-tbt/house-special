# Orange Data Mining

**Pattern 3c — scraped direct URL.** The vendor publishes versioned DMGs on its own
download page, not on GitHub, so the recipe reads the current link from that page.

| | |
|---|---|
| Source | `https://orangedatamining.com/download/` → `https://download.biolab.si/download/files/Orange3-<ver>-Python<pyver>-arm64.dmg` |
| License | GPL-3.0 |
| Signature | Developer ID Application: Univerza v Ljubljani, Fakulteta za racunalnistvo (`556DY3FJ29`) |
| Architecture | Apple silicon (`arm64`). For Intel, change `arm64` to `x86_64` in `SEARCH_PATTERN`. |
| Version | Read from the app bundle |
| Output | `Acme_Orange-Data-Mining.pkg`, installs `/Applications/Orange.app` (~400 MB download) |
| Last live run | 3.40.0 |

## How it works

`URLTextSearcher` fetches the download page and applies `SEARCH_PATTERN`; the named group
`(?P<url>...)` becomes `%url%` for `URLDownloader`. The filename embeds both the Orange
and the bundled Python versions, so a hard-coded URL would work once and then break
(lint rule SRC-002; Standards §6.7 item 2).

## When it breaks

Scraped recipes break when the vendor redesigns the page. Symptom: `URLTextSearcher`
reports no match. Fix: re-read the page source and adjust `SEARCH_PATTERN` — keep it
anchored to the vendor's download host so an ad or mirror link can't match.
