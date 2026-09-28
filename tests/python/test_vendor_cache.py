# test_vendor_cache.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""recipekit.vendor_cache (specs/vendor-cache/): normalize (KI-7: type checks,
protected files, relocation, --dry-run) and sync (timestamps, unsafe entries,
--dry-run)."""

import contextlib
import io
import os
import unittest
from pathlib import Path

from helpers import KIT_ROOT, FixtureCase
from recipekit.vendor_cache import file_type, load_registry, main

REGISTRY = """ignored_subdirs: ["scripts"]
protected_files: ["scripts.zip"]
canonical_filenames:
  A/InPlace: "App.dmg"
  A/Stale: "App.dmg"
  A/Rename: "App.pkg"
  A/Sidecar: "payload.zip"
  A/Protected: "payload.zip"
  A/Empty: "x.pkg"
  A/Gone: "x.pkg"
  A/Unsafe: "Safe.dmg"
"""


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CacheCase(FixtureCase):
    def put(self, rel: str, text: str = "x", when: int | None = None) -> Path:
        path = self.cache / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        if when is not None:
            os.utime(path, (when, when))
        return path

    def files(self) -> list[str]:
        return sorted(
            str(p.relative_to(self.cache)) for p in self.cache.rglob("*") if p.is_file()
        )


class NormalizeTest(CacheCase):
    def setUp(self):
        super().setUp()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        (self.repo / "vendor-drop-registry.yaml").write_text(REGISTRY)
        self.cache = self.root / "cache"
        self.put("A/InPlace/App.dmg")
        self.put("A/Stale/App.dmg")
        self.put("A/Stale/App 1.2.dmg", when=1_600_000_000)  # an older version
        self.put("A/Stale/README.txt")
        self.put("A/Rename/Old-1.0.pkg", when=1_700_000_000)
        self.put("A/Rename/New-2.0.pkg", when=1_760_000_000)
        (self.cache / "A/Rename/scripts").mkdir()
        self.put("A/Sidecar/Vendor_Payload.zip", when=1_700_000_000)
        self.put("A/Sidecar/notes.txt", when=1_760_000_000)
        self.put("A/Protected/scripts.zip")
        (self.cache / "A/Empty").mkdir()
        self.put("A/Unsafe/Safe App (v2).dmg")
        self.relocated = self.root / "relocated"

    def normalize(self, *extra):
        return run(
            "normalize",
            "--repo",
            str(self.repo),
            "--vendor-cache",
            str(self.cache),
            "--relocate-dir",
            str(self.relocated),
            *extra,
        )

    def test_ki_7_types_protection_and_relocation(self):
        code, out, err = self.normalize()
        self.assertEqual(code, 0, err)
        self.assertEqual(
            self.files(),
            [
                "A/InPlace/App.dmg",
                "A/Protected/scripts.zip",  # protected: never renamed
                "A/Rename/App.pkg",  # the newest .pkg
                "A/Rename/Old-1.0.pkg",
                "A/Sidecar/notes.txt",  # not a .zip: left alone
                "A/Sidecar/payload.zip",
                "A/Stale/App.dmg",
                "A/Stale/README.txt",  # different type: kept
                "A/Unsafe/Safe.dmg",
            ],
        )
        self.assertTrue((self.relocated / "A/Stale/App 1.2.dmg").is_file())
        lines = out.splitlines()
        self.assertIn("SKIP\tA/InPlace\tApp.dmg\t\tAlready in place", lines)
        self.assertIn(
            "RENAME\tA/Unsafe\tSafe App (v2).dmg\tSafe.dmg\tDONE|UNSAFE_CHARS", lines
        )
        self.assertIn(
            "SKIP\tA/Protected\tscripts.zip\tpayload.zip\tProtected — kept", lines
        )
        self.assertIn(
            "IGNORE\tA/Rename\tscripts\t\tSkipping scripts/ subdirectory (ignored)",
            lines,
        )
        self.assertTrue(any(line.startswith("MISSING\tA/Gone") for line in lines))
        self.assertIn("1 extra file(s) remain after rename: Old-1.0.pkg", err)

    def test_a_newer_drop_replaces_the_canonical_file(self):
        # The vendor shipped 3.0 while last cycle's App.dmg is still there.
        self.put("A/InPlace/App.dmg", "old", when=1_700_000_000)
        self.put("A/InPlace/App 2.0.dmg", "older", when=1_600_000_000)
        self.put("A/InPlace/App 3.0.dmg", "new", when=1_760_000_000)
        code, out, _ = self.normalize()
        self.assertEqual(code, 0)
        self.assertEqual((self.cache / "A/InPlace/App.dmg").read_text(), "new")
        self.assertEqual(
            sorted(p.name for p in (self.relocated / "A/InPlace").iterdir()),
            ["App 2.0.dmg", "App.dmg"],
        )
        self.assertIn(
            "RENAME\tA/InPlace\tApp 3.0.dmg\tApp.dmg\tDONE|REPLACED|UNSAFE_CHARS", out
        )
        self.assertIn("Superseded by App 3.0.dmg; Relocated to", out)
        # Idempotent: the next run finds it in place.
        _, out, _ = self.normalize()
        self.assertIn("SKIP\tA/InPlace\tApp.dmg\t\tAlready in place", out)

    def test_dry_run_changes_nothing(self):
        before = self.files()
        code, out, _ = self.normalize("--dry-run")
        self.assertEqual((code, self.files()), (0, before))
        self.assertIn("RENAME\tA/Rename\tNew-2.0.pkg\tApp.pkg\tDRY RUN", out)
        self.assertIn("DRY RUN: would relocate to", out)
        self.assertFalse(self.relocated.exists())

    def test_default_relocate_folder_mirrors_the_tree(self):
        args = (
            "normalize",
            "--repo",
            str(self.repo),
            "--vendor-cache",
            str(self.cache),
        )
        self.assertEqual(run(*args)[0], 0)
        moved = self.cache / "relocated/A/Stale/App 1.2.dmg"
        self.assertTrue(moved.is_file())
        # Another stale copy of the same name later: never overwritten.
        self.put("A/Stale/App 1.2.dmg", "again", when=1_600_000_000)
        self.assertEqual(run(*args)[0], 0)
        self.assertTrue(moved.is_file())
        self.assertEqual(
            (self.cache / "relocated/A/Stale/App 1.2-2.dmg").read_text(), "again"
        )

    def test_a_vendor_named_like_the_relocate_folder_is_refused(self):
        (self.repo / "vendor-drop-registry.yaml").write_text(
            'canonical_filenames:\n  "relocated/App": "x.pkg"\n'
        )
        args = (
            "normalize",
            "--repo",
            str(self.repo),
            "--vendor-cache",
            str(self.cache),
        )
        code, _, err = run(*args)
        self.assertEqual(code, 1)
        self.assertIn("clashes with the relocate folder", err)

    def test_bad_keys_and_names_are_errors(self):
        (self.repo / "vendor-drop-registry.yaml").write_text(
            'canonical_filenames:\n  "A/../B": "x.pkg"\n'
            '  "A/Ok": "../x.pkg"\n  NoSlash: "y.pkg"\n'
        )
        code, _, err = self.normalize()
        self.assertEqual(code, 1)
        self.assertEqual(err.count("ERROR\t"), 3)

    def test_config_errors_exit_1(self):
        (self.repo / "vendor-drop-registry.yaml").write_text("canonical_filenames: [\n")
        self.assertEqual(self.normalize()[0], 1)
        self.assertEqual(run("normalize", "--repo", str(self.repo))[0], 1)
        self.assertEqual(run("normalize", "--bogus")[0], 1)

    def test_acme_registry_loads(self):
        reg = load_registry(KIT_ROOT / "customer/acme/output/vendor-drop-registry.yaml")
        self.assertEqual(reg.canonical["AcmeFruitCo/AcmeSupport"], "payload.zip")
        self.assertIn("scripts.zip", reg.protected_files)

    def test_file_types(self):
        cases = {"a.PKG": ".pkg", "a.tar.gz": ".tar.gz", "a.1.2.dmg": ".dmg", "a": ""}
        for name, kind in cases.items():
            with self.subTest(name):
                self.assertEqual(file_type(name), kind)


class SyncTest(CacheCase):
    def setUp(self):
        super().setUp()
        self.cache = self.root / "src"
        self.put("V/App/App.pkg", "pkg", when=1_700_000_000)
        self.put("V/App/payload/f", "payload")
        self.index = self.root / "files_to_copy.yaml"
        self.index.write_text(
            'files:\n  - "V/App/App.pkg"\n  - "V/App/payload"\n'
            '  - "V/Missing/x.pkg"\n  - "../escape.pkg"\n  - "/etc/hosts"\n'
        )
        self.dst = self.root / "dst"

    def sync(self, *extra):
        return run("sync", *extra, str(self.index), str(self.cache), str(self.dst))

    def test_copies_keep_timestamps_so_reruns_skip(self):
        code, out, err = self.sync()
        self.assertEqual(code, 1)  # the missing and unsafe entries
        self.assertEqual((self.dst / "V/App/App.pkg").stat().st_mtime, 1_700_000_000)
        self.assertTrue((self.dst / "V/App/payload/f").is_file())
        self.assertIn("Errors: 3", out)
        self.assertEqual(err.count("outside the vendor cache"), 2)
        self.assertFalse((self.root / "escape.pkg").exists())
        _, out, _ = self.sync()
        self.assertIn("SKIP  V/App/App.pkg", out)

    def test_dry_run_writes_nothing(self):
        code, out, _ = self.sync("--dry-run")
        self.assertIn("COPY  V/App/App.pkg  (dry run)", out)
        self.assertIn("(dry run: nothing copied)", out)
        self.assertFalse(self.dst.exists())

    def test_usage_errors_exit_2(self):
        empty = self.root / "empty.yaml"
        empty.write_text("files: []\n")
        cases = [
            ("sync",),
            ("sync", "--bogus", str(self.index), "a", "b"),
            ("sync", str(self.root / "nope.yaml"), str(self.cache), str(self.dst)),
            ("sync", str(self.index), str(self.root / "nope"), str(self.dst)),
            ("sync", str(empty), str(self.cache), str(self.dst)),
            ("nothing",),
        ]
        for argv in cases:
            with self.subTest(argv):
                self.assertEqual(run(*argv)[0], 2)

    def test_acme_manifest_loads(self):
        from recipekit.vendor_cache import load_index

        files = load_index(KIT_ROOT / "customer/acme/output/files_to_copy.yaml")
        self.assertIn("AcmeFruitCo/AcmeSupport/scripts.zip", files)


if __name__ == "__main__":
    unittest.main()
