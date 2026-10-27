import base64
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import demo_gallery
from md_resume import ResumeWorkspace
from md_workspace import Workspace
from resume_layout import TEMPLATES


class _VisibleResume(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.capture = False

    def handle_starttag(self, tag, attrs):
        if tag in {"h1", "h2", "h3", "p"}:
            self.capture = True

    def handle_endtag(self, tag):
        if tag in {"h1", "h2", "h3", "p"}:
            self.capture = False

    def handle_data(self, text):
        if self.capture and text.strip():
            self.text.append(text.strip())


class GalleryTests(unittest.TestCase):
    def test_three_avatar_choices_and_six_layouts_do_not_create_extra_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "gallery"
            report = demo_gallery.run(root)
            self.assertTrue(report["fictional_only"])
            self.assertEqual(report["preview_count"], 18)
            page = (root / "index.html").read_text()
            self.assertNotIn("__GALLERY_DATA__", page)
            fixture_counts = {}
            for avatar in demo_gallery.AVATARS:
                fixture = root / "fixtures" / avatar
                ws = Workspace(fixture)
                resumes = ResumeWorkspace(ws)
                self.assertEqual(len(resumes.list("ai-product")["versions"]), 1)
                self.assertEqual(len(resumes.list("ai-product", "starbridge", "starbridge-product")["versions"]), 1)
                fixture_counts[avatar] = ws.validate()["documents_count"]
                expected = ((root / "avatars" / f"{avatar}.png").read_bytes()
                            if avatar != "none" else None)
                content_sets = []
                for identifier in TEMPLATES:
                    preview = (root / "previews" / avatar / f"{identifier}.html").read_text()
                    embedded = (root / "embedded-previews" / avatar / f"{identifier}.html").read_text()
                    self.assertIn('id="print"', preview)
                    self.assertNotIn('id="print"', embedded)
                    self.assertNotIn('<div class="tools">', embedded)
                    self.assertNotIn('<script>', embedded)
                    self.assertEqual(embedded.encode(), demo_gallery.embedded_preview(preview.encode()))
                    photo = re.search(r'<img class="photo"[^>]+src="data:image/png;base64,([A-Za-z0-9+/=]+)"', preview)
                    if expected is None:
                        self.assertIsNone(photo)
                    else:
                        self.assertIsNotNone(photo)
                        self.assertEqual(base64.b64decode(photo.group(1)), expected)
                    parsed = _VisibleResume()
                    parsed.feed(preview)
                    # Section reordering changes the sequence, never the supplied text.
                    content_sets.append(sorted(parsed.text))
                self.assertTrue(all(text == content_sets[0] for text in content_sets))
                for version in resumes.list("ai-product")["versions"]:
                    # Derived sandbox adapters never rewrite a registered version.
                    registered = Path(version["html_path"]).read_bytes()
                    self.assertIn(b'id="print"', registered)
                    self.assertEqual(resumes.inspect(version["relative_path"])["status"], "reviewable")
            self.assertEqual(fixture_counts, {"a": 28, "b": 28, "none": 27})
            self.assertNotEqual((root / "avatars/a.png").read_bytes(), (root / "avatars/b.png").read_bytes())

    def test_sandbox_adapter_refuses_silent_toolbar_drift(self):
        with self.assertRaisesRegex(ValueError, "toolbar changed"):
            demo_gallery.embedded_preview(b"<html><button>new control</button></html>")

    def test_existing_output_is_rejected_before_reading_sources_or_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "private"
            root.mkdir()
            (root / "personal.txt").write_text("leave untouched")
            before = list(root.iterdir())
            with patch.object(demo_gallery, "load_references", side_effect=AssertionError("No source reads expected")):
                with self.assertRaisesRegex(ValueError, "nonexistent"):
                    demo_gallery.run(root)
            self.assertEqual(list(root.iterdir()), before)
            self.assertEqual((root / "personal.txt").read_text(), "leave untouched")

    def test_reference_catalog_rejects_active_urls_and_keeps_html_text_in_json(self):
        item = {
            "id": "reference", "title": '</script><img src=x onerror="alert(1)">',
            "usage": "A public style reference", "license": "MIT",
            "repo_url": "https://github.com/example/resume",
            "license_url": "https://github.com/example/resume/blob/main/LICENSE",
            "preview_url": "https://example.com/resume",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            path.write_text(json.dumps({"items": [item]}))
            references = demo_gallery.load_references(path)
            markup = demo_gallery.render_gallery('<script type="application/json">__GALLERY_DATA__</script>', {"references": references})
            self.assertEqual(markup.count("</script>"), 1)
            self.assertNotIn("<img", markup)
            self.assertIn("\\u003c/script\\u003e", markup)
            for bad in ("javascript:alert(1)", "http://example.com", "https://user:password@example.com/x"):
                item["preview_url"] = bad
                path.write_text(json.dumps({"items": [item]}))
                with self.assertRaises(ValueError):
                    demo_gallery.load_references(path)

    def test_invalid_date_or_catalog_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "new"
            with self.assertRaises(ValueError):
                demo_gallery.run(root, "not-a-date")
            self.assertFalse(root.exists())
            with patch.object(demo_gallery, "load_references", side_effect=ValueError("Bad catalog")):
                with self.assertRaisesRegex(ValueError, "Bad catalog"):
                    demo_gallery.run(root)
            self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
