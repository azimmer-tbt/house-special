# Acme Fruit Co. — recipe repo

This folder is laid out the way a real recipe repo is, so every toolkit front end
accepts it as `--repo customer/acme/output`:

```text
output/
├── recipes/<Vendor>/<App>/     download + pkg recipe pair, README.md
├── vendor-drop-registry.yaml   canonical names for vendor-drop files (bin/normalize-vendor-cache.sh)
├── files_to_copy.yaml          what the vendor cache must hold (bin/sync-vendor-cache.sh)
├── build/                      local build output (gitignored)
└── vendor_cache/               local vendor-drop files (gitignored)
```

Each recipe directory's `README.md` says what the recipe does, its pattern, its
signature status and how to update it. Standards for all of the above:
[`reference/recipe-standards.md`](../../../reference/recipe-standards.md).

```bash
bin/recipe-linter.sh --repo customer/acme/output --pair-check   # lint everything
bin/classify-recipe.sh customer/acme/output/recipes/MoonlightGameStreaming/Moonlight
bin/normalize-vendor-cache.sh --repo customer/acme/output --vendor-cache /tmp/autopkg/vendor_cache --dry-run
```
