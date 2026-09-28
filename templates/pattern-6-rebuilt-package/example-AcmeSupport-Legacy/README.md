# AcmeSupport-Legacy — ILLUSTRATIVE EXAMPLE

**This example is synthetic.** Unlike the Pattern 4 and Pattern 5 worked
examples, which are real recipes from the batch, this one was generated from a
hand-written `blueprint.conf` rather than from an actual extracted package. No
`AcmeSupport.pkg` was reverse-engineered to produce it.

It is here to show the *shape* `blueprint-to-recipe.sh` emits — the two-Copier
staging, the `scripts:` argument, the `PKG_ID`/`version` inputs, and the absence
of a `chown` block when extraction ran as root. Do not treat the identifier,
version, or file counts as real.

Replace it with a genuine extraction the first time Pattern 6 is used against a
real package. A real example would also make the "before trusting the result"
checks in `../README.md` demonstrable rather than described.

## What the shape shows

| Element | Why it is there |
|---------|-----------------|
| Two `Copier` steps | The payload and the scripts are separate trees, and both must reach `%RECIPE_CACHE_DIR%` before `PkgCreator` runs |
| `NO_CODE_SIGNATURE_REQUIRED` in `Input` | Rebuilt packages have no signature; the declaration is explicit, not an omission |
| `PKG_ID` as an `Input` | Must match the original's identifier or receipts diverge |
| `version` as an `Input` | `%version%` referenced without an `Input` declaration fails at runtime |
| No `chown` block | The blueprint recorded `ownership_preserved=true`, so ditto carries ownership through |
