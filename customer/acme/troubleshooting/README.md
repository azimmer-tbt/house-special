# troubleshooting/

The drop point for evidence while debugging a recipe or an install: installer
logs (`/var/log/install.log` excerpts), `autopkg run -vvv` output, screenshots of
installer dialogs, vendor packages being compared with `bin/pkg-compare.sh`.

Everything here except this README is gitignored. Screenshots can be read with
`bin/analyze-screenshot.sh` if you have a local vision model configured
(`config/screenshot-analyzer.yaml`). Before sharing anything from here, run
`bin/check-sanitized.sh --path customer/acme/troubleshooting`.
