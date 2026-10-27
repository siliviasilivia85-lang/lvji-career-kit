"""Portable demo checks use only newly generated fictional fixtures."""
import json
from hashlib import sha256
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import demo_site
from resume_layout import TEMPLATES


class PublicDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="lvji-public-demo-test-")
        cls.root = Path(cls.temp.name) / "site"
        cls.report = demo_site.run(cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_dialogue_first_and_four_readonly_result_views(self):
        self.assertFalse(self.report["published"])
        self.assertTrue(self.report["fictional_only"])
        self.assertTrue(self.report["read_only"])
        intro = (self.root / "index.html").read_text()
        self.assertIn("编排示例", intro)
        self.assertIn("先找回已有的积累", intro)
        self.assertIn("方向可以慢慢形成", intro)
        self.assertIn("本周只能拿出五小时", intro)
        self.assertIn("初筛反馈", intro)
        for page in [self.root / "index.html", *(self.root / "workbench").glob("*.html")]:
            content = page.read_text()
            self.assertNotIn("<script", content)
            self.assertNotIn("<button", content)
            self.assertNotIn("data-request", content)
            self.assertNotIn("navigator.clipboard", content)
            self.assertIn("不连接模型或 Agent", content)
        self.assertEqual(len(list((self.root / "workbench").glob("*.html"))), 4)

    def test_every_gallery_combination_and_source_link_is_portable(self):
        page = (self.root / "gallery/index.html").read_text()
        matched = re.search(r'<script id="gallery-data" type="application/json">([\s\S]*?)</script>', page)
        data = json.loads(matched.group(1))
        self.assertEqual(len(data["templates"]), 6)
        self.assertEqual(len(data["avatars"]), 3)
        count = 0
        for template in data["templates"]:
            for avatar in ("a", "b", "none"):
                for kind in ("variants", "embedded_variants"):
                    sample = self.root / "gallery" / template[kind][avatar]
                    self.assertTrue(sample.is_file())
                    html = sample.read_text()
                    self.assertNotIn("<script", html)
                    self.assertNotIn('id="print"', html)
                    self.assertNotIn("content.json", html)
                    self.assertNotIn("data:image/", html)
                    self.assertEqual(html.count('<img class="photo"'), 0 if avatar == "none" else 1)
                    if kind == "embedded_variants":
                        self.assertNotIn('<a ', html)
                count += 1
        self.assertEqual(count, 18)
        self.assertIn('sandbox=""', page)
        self.assertEqual(demo_site.validate_public_site(self.root), self.report["files"])
        # The same exact files also work beneath a project prefix.
        prefixed = Path(self.temp.name) / "pages-prefix" / "lvji-career-kit"
        shutil.copytree(self.root, prefixed)
        self.assertEqual(demo_site.validate_public_site(prefixed), self.report["files"])

    def test_no_workspace_identity_history_or_machine_path_is_published(self):
        paths = [p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file()]
        self.assertFalse(any(p.endswith((".json", ".md", ".pdf")) or ".luji" in p or "fixtures/" in p for p in paths))
        for path in self.root.rglob("*.html"):
            text = path.read_text()
            for token in ("file://", "/Users/", "/home/", "/var/folders/", "workspace_id", "workspace_path", "manifest.json", "approval_token", "generated_at", "checked_at", str(self.temp.name)):
                self.assertNotIn(token, text)
        for avatar, filename in demo_site.AVATAR_ASSETS.items():
            self.assertEqual((self.root / "assets" / ("avatar-" + avatar + ".png")).read_bytes(),
                             (demo_site.PACKAGE / "assets" / filename).read_bytes())
        # Pictures are shared local assets, not repeated inline in 36 pages.
        size = sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file())
        self.assertLess(size, 8 * 1024 * 1024)

    def test_source_text_stays_inert_and_does_not_create_active_markup(self):
        hostile = '<script>fetch("https://example.invalid")</script><img src=x onerror=alert(1)>'
        document = {"path": "present/notes/idea.md", "metadata": {"title": hostile}, "body": hostile}
        card = demo_site._card(document)
        self.assertNotIn("<script", card)
        self.assertNotIn("<img", card)
        self.assertIn("&lt;script&gt;", card)

    def test_repeated_build_contains_no_new_identity_or_run_time(self):
        repeated = Path(self.temp.name) / "repeated"
        demo_site.run(repeated)
        first = {p.relative_to(self.root).as_posix(): sha256(p.read_bytes()).hexdigest() for p in self.root.rglob("*") if p.is_file()}
        second = {p.relative_to(repeated).as_posix(): sha256(p.read_bytes()).hexdigest() for p in repeated.rglob("*") if p.is_file()}
        self.assertEqual(first, second)

    def test_existing_or_symlink_output_is_rejected_before_source_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private = root / "personal"
            private.mkdir()
            (private / "keep.txt").write_text("never overwrite")
            (root / "linked").symlink_to(private, target_is_directory=True)
            (root / "dangling").symlink_to(root / "missing")
            with patch.object(demo_site, "build_gallery", side_effect=AssertionError("must not build")):
                for output in (private, root / "linked", root / "linked" / "new", root / "dangling"):
                    with self.subTest(output=output):
                        with self.assertRaises(ValueError):
                            demo_site.run(output)
            self.assertEqual((private / "keep.txt").read_text(), "never overwrite")
            self.assertEqual(len(list(private.iterdir())), 1)

    def test_leak_or_broken_reference_failure_never_creates_public_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for text in ('<p>file:///private/tmp/a</p>', '<a href="/rooted.html">bad base</a>', '<a href="missing.html">missing</a>', '<img src="https://example.invalid/avatar.png">'):
                stage = root / "bad"
                stage.mkdir()
                (stage / "index.html").write_text(text)
                with self.assertRaises(ValueError):
                    demo_site.validate_public_site(stage)
                shutil.rmtree(stage)
            def broken(stage, unused):
                (stage / "index.html").write_text('<a href="missing.html">bad</a>')
                return {}
            with patch.object(demo_site, "build_gallery", return_value={}), patch.object(demo_site, "_build", side_effect=broken):
                with self.assertRaises(ValueError):
                    demo_site.run(root / "output")
            self.assertFalse((root / "output").exists())
            self.assertFalse(list(root.glob(".lvji-demo-build-*")))

    def test_cli_documents_no_publish_and_refuses_existing_directory(self):
        result = subprocess.run([sys.executable, "-B", str(Path(demo_site.__file__)), "--output", str(self.root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["ok"])
        self.assertIn("nonexistent", result.stdout)


if __name__ == "__main__":
    unittest.main()
