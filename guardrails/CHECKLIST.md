# Checklist: AutoPkg Recipe — Vendor-Drop / Stable-URL

Run `bin/autopkg-preflight.py --app <app-folder>` before considering any recipe
done — it checks the must-haves below automatically, except the manifest, which
`bin/verify-manifest.sh` checks. A SKIP means the audit could not check on this
machine (for example, the vendor cache isn't there); it is not a pass.
Good-to-haves and footguns need a human/agent eye.

## Must-Haves (audit-enforced — bin/autopkg-preflight.py checks these)
- [ ] Every recipe parses, and the pkg recipe's `ParentRecipe` is its sibling download recipe
- [ ] No `PathDeleter` before anything is staged (a clean-up at the end is fine)
- [ ] `vendor_cache` path arithmetic (`LOCAL_*PATH` and `file://` URLs) resolves to a real, existing file/directory
- [ ] No `%pathname%` before a step that sets it (`Copier` doesn't)
- [ ] `expected_authority_names` has the full 3-entry chain, if `CodeSignatureVerifier` is used
- [ ] `NO_CODE_SIGNATURE_REQUIRED: true` + comment, if no `CodeSignatureVerifier`
- [ ] Every `%variable%` is declared in `Input` or set by an earlier step
- [ ] Every `Copier` that copies a folder (`.app` bundle, trailing `/`, `LOCAL_DIR_PATH`) includes `overwrite: true`
- [ ] App folder has a non-empty `README.md`

## Must-Haves (checked by bin/verify-manifest.sh, not preflight)
- [ ] `manifest.sha256` exists at repo root and verifies clean

## Good-to-Haves (checklist only, not audited)
- [ ] Recipe filenames match `AppName.{download,pkg}.recipe.yaml` exactly
- [ ] Identifiers use `com.acmefruit.autopkg.{download,pkg}.AppName` — no `.pkg.download.` bug
- [ ] `PKG_ID` documented as invented/not-vendor-confirmed where applicable
- [ ] README records the publisher's Team ID (or says there is none)
- [ ] Any `.overrides` holding a secret or deployment detail is generated or gitignored, not committed
- [ ] Actually ran `autopkg run` for real, not just passed the audit

## Footguns (not audit-enforced — read before debugging)
- ⚠️ AutoPkg's cache persists across separate runs — a genuinely-fixed recipe can
  still fail on cached stale state. Clear the cache before assuming a fix didn't work.
- ⚠️ Cloud-sync folders (OneDrive/iCloud) can cause misleading file-visibility
  failures that look like a real bug but aren't.
- ⚠️ A "known-working" example recipe is only a valid template if it's actually the
  same pattern (1–5) — verify before copying its shape.
- ⚠️ Silent handoff drift (a file not actually landing as intended) is a bigger
  time-sink than any individual recipe bug — always verify, never assume.
