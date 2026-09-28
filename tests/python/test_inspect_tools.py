# test_inspect_tools.py
#
# Author: Andrew Zimmer <andrew.zimmer@tigerbeetletechnology.com>
# SPDX-License-Identifier: MIT
"""recipekit.inspect_tools (specs/analysis/inspect-tools/01-inspect-tools.md): an
app bundle, a disk image built with hdiutil (macOS only) and archives built with
zipfile/tarfile, including names with spaces and a helper app inside an app."""

import contextlib
import io
import json
import os
import plistlib
import shutil
import subprocess
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from helpers import FixtureCase
from recipekit.inspect_tools import main


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


def make_app(parent: Path, name: str, ident: str, version: str, sign=True) -> Path:
    app = parent / f"{name}.app"
    (app / "Contents" / "MacOS").mkdir(parents=True)
    info = {
        "CFBundleName": name,
        "CFBundleIdentifier": ident,
        "CFBundleShortVersionString": version,
        "CFBundleVersion": "42",
        "CFBundleExecutable": name,
        "LSUIElement": True,  # a non-string value elsewhere in the plist
    }
    with open(app / "Contents" / "Info.plist", "wb") as f:
        plistlib.dump(info, f, fmt=plistlib.FMT_BINARY)
    shutil.copy("/usr/bin/true", app / "Contents" / "MacOS" / name)
    if sign:
        (app / "Contents" / "_CodeSignature").mkdir()
    return app


class AppTest(FixtureCase):
    def test_ac_t2_1_fields_from_a_binary_plist(self):
        app = make_app(self.root, "My App", "com.example.myapp", "2.1.0")
        code, out, _ = run("app", str(app), "--output", "json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["identifier"], "com.example.myapp")
        self.assertEqual(data["version"], "2.1.0")
        self.assertEqual(data["build"], "42")
        self.assertEqual(data["display_name"], "")  # AC-T2.2: optional, empty
        self.assertTrue(data["has_code_signature"])  # AC-T2.4
        self.assertTrue(data["architectures"])

    def test_text_output(self):
        app = make_app(self.root, "Plain", "com.example.plain", "1.0", sign=False)
        _, out, _ = run("app", str(app))
        self.assertIn("  Display name: (not set)", out)
        self.assertIn("  Code signed:  false", out)

    def test_ac_t2_3_not_a_bundle(self):
        self.assertEqual(run("app", str(self.root))[0], 2)
        self.assertEqual(run("app", str(self.root / "missing.app"))[0], 2)


class ArchiveTest(FixtureCase):
    NAMES = ["Kit/", "Kit/My  File.txt", "Kit/a|b.txt", "Other it's.txt"]

    def make_zip(self) -> Path:
        path = self.root / "kit.zip"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for name in self.NAMES:
                z.writestr(name, "" if name.endswith("/") else "x" * 1000)
        return path

    def make_tar(self, mode: str, name: str) -> Path:
        src = self.root / "src"
        (src / "Kit").mkdir(parents=True, exist_ok=True)
        (src / "Kit" / "My  File.txt").write_text("hello")
        path = self.root / name
        with tarfile.open(path, mode) as tar:
            tar.add(src / "Kit", arcname="Kit")
        return path

    def test_ac_t3_1_zip_with_awkward_names(self):
        code, out, _ = run("archive", str(self.make_zip()), "--output", "json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual([e["path"] for e in data["entries"]], self.NAMES)
        self.assertEqual(data["top_level_items"], ["Kit", "Other it's.txt"])
        self.assertLess(data["entries"][1]["compressed_size"], 1000)
        self.assertFalse(data["truncated"])

    def test_ac_t3_2_and_3_tar_variants(self):
        for mode, name, kind in (
            ("w:gz", "kit.tar.gz", "tar.gz"),
            ("w:bz2", "kit.tbz2", "tar.bz2"),
            ("w", "kit.tar", "tar"),
            ("w:gz", "kit-no-extension", "tar.gz"),  # detected by content
        ):
            with self.subTest(name):
                code, out, _ = run(
                    "archive", str(self.make_tar(mode, name)), "--output", "json"
                )
                data = json.loads(out)
                self.assertEqual((code, data["archive_type"]), (0, kind))
                self.assertIn("Kit/My  File.txt", [e["path"] for e in data["entries"]])
                self.assertIn("Kit/", [e["path"] for e in data["entries"]])

    def test_ac_t3_5_max_entries(self):
        code, out, _ = run(
            "archive", str(self.make_zip()), "--max-entries", "2", "--output", "json"
        )
        data = json.loads(out)
        self.assertEqual((data["entry_count"], len(data["entries"])), (4, 2))
        self.assertTrue(data["truncated"])
        _, text, _ = run("archive", str(self.make_zip()))
        self.assertIn("Entries:      4\n", text)  # not "truncated" when it isn't

    def test_ac_t3_4_unknown_and_corrupt(self):
        plain = self.root / "notes.txt"
        plain.write_text("just text\n")
        code, _, err = run("archive", str(plain))
        self.assertEqual(code, 2)
        self.assertIn("Detected type:", err)
        broken = self.root / "broken.zip"
        broken.write_bytes(b"PK\x03\x04 not really")
        self.assertEqual(run("archive", str(broken))[0], 2)
        self.assertEqual(run("archive", str(plain), "--max-entries", "0")[0], 2)


@unittest.skipUnless(shutil.which("hdiutil"), "macOS only")
class DmgTest(FixtureCase):
    @classmethod
    def setUpClass(cls):
        cls._dmg_tmp = tempfile.TemporaryDirectory()
        root = Path(cls._dmg_tmp.name)
        src = root / "src"
        src.mkdir()
        app = make_app(src, "Main App", "com.example.main", "3.0")
        make_app(app / "Contents" / "Helpers", "Helper", "com.example.helper", "3.0")
        os.symlink("/Applications", src / "Applications")
        (src / "README.txt").write_text("read me\n")
        cls.dmg = root / "Main App 3.0.dmg"
        subprocess.run(
            ["hdiutil", "create", "-quiet", "-srcfolder", str(src), "-volname", "Main"]
            + ["-format", "UDZO", str(cls.dmg)],
            check=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls._dmg_tmp.cleanup()

    def mounted(self) -> str:
        return subprocess.run(
            ["hdiutil", "info"], capture_output=True, text=True
        ).stdout

    def test_ac_t1_1_to_4_apps_structure_and_no_orphan_mount(self):
        code, out, _ = run("dmg", str(self.dmg), "--output", "json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual([a["name"] for a in data["apps"]], ["Main App.app"])
        self.assertEqual(data["apps"][0]["version"], "3.0")
        self.assertIn("Applications", data["top_level_items"])
        self.assertNotIn(data["mount_point"], self.mounted())

    def test_ac_t1_3_keep_mounted(self):
        code, out, _ = run("dmg", str(self.dmg), "--keep-mounted")
        mount = out.split("DMG left mounted at: ")[1].split("\n")[0]
        try:
            self.assertEqual(code, 0)
            self.assertIn(mount, self.mounted())
        finally:
            subprocess.run(["hdiutil", "detach", mount, "-quiet"], check=False)

    def test_ac_t1_5_not_a_dmg(self):
        text = self.root / "fake.dmg"
        text.write_text("nope\n")
        code, _, err = run("dmg", str(text))
        self.assertEqual(code, 2)
        self.assertIn("Failed to mount", err)


if __name__ == "__main__":
    unittest.main()
