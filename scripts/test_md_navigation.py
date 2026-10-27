"""Navigation tests use only newly created fictional workspaces."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import md_navigation as navigation
from md_navigation import NavigationWorkspace, CACHE
from md_workspace import Workspace, StoreError, dump_document, digest


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="luji-navigation-fictional-")
        self.ws = Workspace(Path(self.temp.name) / "workspace")
        self.ws.initialize()
        self.nav = NavigationWorkspace(self.ws)

    def tearDown(self):
        self.temp.cleanup()

    def raw(self, path="past/materials/虚构简历.pdf", content=b"Fictional PDF content, not parsed"):
        target = self.ws.path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return path

    def record(self, path="past/work/经历.md", source=None, **extra):
        source = source or self.raw()
        metadata = {"id": "fictional-work", "type": "work", "title": "虚构经历",
                    "sources": [source], "source_revisions": {source: digest(self.ws.path(source).read_bytes())}, **extra}
        target = self.ws.path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(dump_document(metadata, "A fictional body that discovery must never read."), encoding="utf-8")
        return path

    def maps(self):
        return {p: self.ws.path(p).read_bytes() for p in ("MAP.md", "AGENT-MAP.md", "navigation/past.md", "navigation/present.md", "navigation/future.md", "navigation/inbox.md", CACHE)}

    def test_refresh_materials_reads_no_bodies_or_raw_hashes(self):
        source = self.raw()
        note = self.raw("past/materials/普通笔记.md", b"No frontmatter required.")
        self.record(source=source)
        with mock.patch.object(self.ws, "read", side_effect=AssertionError("body read")), mock.patch.object(self.ws, "_bytes", side_effect=AssertionError("raw hash")), mock.patch.object(self.ws, "index", side_effect=AssertionError("global index")):
            result = self.nav.refresh("past")
        by_path = {e["path"]: e for e in result["entries"]}
        self.assertEqual(by_path[source]["state"], "pending")
        self.assertEqual(by_path[note]["kind"], "material")
        self.assertEqual(by_path["past/work/经历.md"]["metadata"]["id"], "fictional-work")
        self.assertNotIn("A fictional body", json.dumps(result))
        self.assertTrue(result["not_a_write_baseline"])
        self.assertFalse(result["read_bodies"])

    def test_narrow_scope_does_not_open_other_company_or_area(self):
        # A regenerated catalog has no memory of which areas were previously
        # inspected; derived maps can be rebuilt without inventing coverage.
        self.ws.path(CACHE).unlink(missing_ok=True)
        selected = self.raw("future/roles/产品/companies/甲/机会/materials/JD.md", b"Fictional JD")
        self.raw("future/roles/产品/companies/乙/机会/materials/其他.md", b"Other JD")
        self.ws.path("past/work/损坏.md").write_text("This should not be read for a company scope.")
        result = self.nav.refresh("future/roles/产品/companies/甲/机会")
        self.assertEqual([e["path"] for e in result["entries"]], [selected])
        self.assertEqual(self.nav.catalog("past")["entries"], [])
        self.assertIn("整区上次检查：未检查", self.ws.path("navigation/past.md").read_text())

    def test_explicit_link_then_change_requires_recheck(self):
        source = self.raw()
        record = self.record(source=source)
        before = self.ws.path(record).read_bytes()
        result = self.nav.link(source, [record])
        self.assertEqual(result["entry"]["state"], "processed")
        self.assertEqual(self.nav.refresh("past/materials")["entries"][0]["state"], "processed")
        self.ws.path(source).write_bytes(b"A changed fictional PDF")
        self.assertEqual(self.nav.refresh("past/materials")["entries"][0]["state"], "changed")
        with self.assertRaises(StoreError) as caught:
            self.nav.link(source, [record])
        self.assertEqual(caught.exception.code, "conflict")
        self.assertEqual(self.ws.path(record).read_bytes(), before)

    def test_reference_without_reviewed_revision_cannot_mark_processed(self):
        source = self.raw()
        record = self.record(source=source, source_revisions={})
        self.nav.refresh("past")
        before = self.maps()
        with self.assertRaises(StoreError):
            self.nav.link(source, [record])
        self.assertEqual(before, self.maps())
        self.assertEqual(self.nav.catalog("past/materials")["entries"][0]["state"], "pending")

    def test_missing_file_keeps_historical_entry_and_link(self):
        source = self.raw()
        record = self.record(source=source)
        self.nav.link(source, [record])
        self.ws.path(source).unlink()
        entry = self.nav.refresh("past/materials")["entries"][0]
        self.assertEqual(entry["state"], "missing")
        self.assertEqual(entry["link"]["records"], [record])
        self.assertIn("文件已不在原位置", self.ws.path("navigation/past.md").read_text())

    def test_directory_read_failure_preserves_all_old_outputs(self):
        self.raw();self.nav.refresh("past")
        before = self.maps()
        real = os.scandir
        def fail(path):
            if Path(path) == self.ws.path("past/materials"):
                raise PermissionError("fictional directory denied")
            return real(path)
        with mock.patch.object(navigation.os, "scandir", side_effect=fail), self.assertRaises(StoreError) as caught:
            self.nav.refresh("past")
        self.assertEqual(caught.exception.code, "navigation_read")
        self.assertEqual(before, self.maps())

    def test_broken_formal_markdown_is_not_a_false_empty_record(self):
        self.nav.refresh("past");before = self.maps()
        self.ws.path("past/work/broken.md").write_text("No header", encoding="utf-8")
        with self.assertRaises(StoreError):
            self.nav.refresh("past")
        self.assertEqual(before, self.maps())

    def test_cache_read_creates_no_lock_and_never_refreshes_files(self):
        self.raw();self.nav.refresh("past")
        lock = self.ws.path(".luji/write.lock");lock.unlink()
        before = self.maps()
        self.raw("past/materials/后来放入.txt", b"Later file")
        real = os.scandir
        def cache_only(path):
            if Path(path).is_relative_to(self.ws.root / "past"):
                raise AssertionError("No career directory scan during a cache read")
            return real(path)
        with mock.patch.object(navigation.os, "scandir", side_effect=cache_only):
            result = self.nav.catalog("past")
        self.assertEqual(result["freshness"], "cached_not_refreshed")
        self.assertNotIn("后来放入", json.dumps(result, ensure_ascii=False))
        self.assertFalse(lock.exists())
        self.assertEqual(before, self.maps())

    def test_both_maps_share_catalog_and_escape_document_labels(self):
        source = self.raw("inbox/看起来像[链接].md", b"A plain note")
        item = self.ws.path("present/items/作品.md")
        item.write_text(dump_document({"id": "sample-item", "type": "item", "title": "<img src=x>作品"}, "PRIVATE BODY MUST NOT APPEAR"), encoding="utf-8")
        result = self.nav.refresh("all")
        self.assertEqual(len(result["entries"]), 2)
        self.assertEqual(set(result["maps"]), {"MAP.md", "AGENT-MAP.md", "navigation/inbox.md", "navigation/past.md", "navigation/present.md", "navigation/future.md"})
        human = self.ws.path("MAP.md").read_text()
        agent = self.ws.path("AGENT-MAP.md").read_text()
        self.assertIn("navigation/inbox.md", human)
        self.assertIn("navigation/inbox.md", agent)
        self.assertIn("派生简历", human)
        self.assertIn("md_resume.py list", agent)
        self.assertIn("present/items/", agent)
        self.assertIn("&lt;img src=x&gt;", agent)
        self.assertNotIn("PRIVATE BODY", agent)
        self.assertIn("待整理", self.ws.path("navigation/inbox.md").read_text())
        self.assertEqual(self.ws.read([str(item.relative_to(self.ws.root))])["documents"][0]["metadata"]["id"], "sample-item")
        self.assertEqual(source, result["entries"][0]["path"])

    def test_unowned_map_and_foreign_cache_are_not_overwritten(self):
        self.ws.path("MAP.md").write_text("# My own map\n")
        with self.assertRaises(StoreError) as caught:
            self.nav.refresh("past")
        self.assertEqual(caught.exception.code, "navigation_owned")
        self.assertEqual(self.ws.path("MAP.md").read_text(), "# My own map\n")
        self.ws.path("MAP.md").unlink()
        self.nav.refresh("past")
        cache = json.loads(self.ws.path(CACHE).read_text())
        cache["workspace_id"] = "a-foreign-workspace"
        self.ws.path(CACHE).write_text(json.dumps(cache))
        with self.assertRaises(StoreError) as caught:
            self.nav.catalog()
        self.assertEqual(caught.exception.code, "navigation_identity")

    def test_scope_escape_symlink_and_special_file_rejected(self):
        for scope in ("../outside", ".luji", "future/roles/a/common/resumes", "/tmp"):
            with self.subTest(scope=scope), self.assertRaises(StoreError):
                self.nav.refresh(scope)
        outside = Path(self.temp.name) / "outside.txt";outside.write_text("Do not read")
        self.ws.path("past/materials/link.txt").symlink_to(outside)
        with self.assertRaises(StoreError):
            self.nav.refresh("past/materials")
        (self.ws.root / "past/materials/link.txt").unlink()
        if hasattr(os, "mkfifo"):
            os.mkfifo(self.ws.path("inbox/pipe"))
            with self.assertRaises(StoreError):
                self.nav.refresh("inbox")

    def test_publish_io_failure_rolls_back_existing_maps(self):
        self.nav.refresh("all");before = self.maps();self.raw()
        original = navigation.atomic_write
        def fail_once(path, value):
            if Path(path) == self.ws.path("navigation/present.md") and value != before["navigation/present.md"]:
                # The area document could legitimately be byte-identical; fail
                # at the catalog, whose checked timestamp always changes.
                raise OSError("fictional publish failure")
            if Path(path) == self.ws.path(CACHE) and value != before[CACHE]:
                raise OSError("fictional publish failure")
            return original(path, value)
        with mock.patch.object(navigation, "atomic_write", side_effect=fail_once), self.assertRaises(OSError):
            self.nav.refresh("past")
        self.assertEqual(before, self.maps())

    def test_cli_refresh_and_read_are_explicit_and_portable(self):
        source = self.raw()
        script = str(Path(__file__).with_name("md_navigation.py"))
        result = subprocess.run([sys.executable, script, "--workspace", str(self.ws.root), "refresh", "--scope", "past"], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn(source, [e["path"] for e in json.loads(result.stdout)["entries"]])
        result = subprocess.run([sys.executable, script, "--workspace", str(self.ws.root), "catalog", "--scope", "present"], capture_output=True, text=True, timeout=20)
        self.assertEqual(json.loads(result.stdout)["freshness"], "cached_not_refreshed")
        result = subprocess.run([sys.executable, script, "catalog"], capture_output=True, text=True, timeout=20)
        self.assertNotEqual(result.returncode, 0)

    def test_user_receipt_named_file_is_a_material_only_tool_receipts_are_skipped(self):
        source = self.raw("past/materials/用户.receipt.json", b"A fictional user document")
        self.raw("past/originals/legacy.receipt.json", b"A legacy tool receipt")
        paths = [e["path"] for e in self.nav.refresh("past")["entries"]]
        self.assertIn(source, paths)
        self.assertNotIn("past/originals/legacy.receipt.json", paths)

    def test_linked_record_edit_or_deletion_is_visible_without_reading_its_body(self):
        source = self.raw();record = self.record(source=source)
        self.nav.link(source, [record])
        self.ws.path(record).write_text(self.ws.path(record).read_text() + "\nManual edit.")
        with mock.patch.object(self.ws, "read", side_effect=AssertionError("No body read on refresh")):
            self.assertEqual(self.nav.refresh("past/materials")["entries"][0]["state"], "changed")
        self.nav.link(source, [record])
        self.ws.path(record).unlink()
        self.assertEqual(self.nav.refresh("past/materials")["entries"][0]["state"], "changed")

    def test_damaged_cache_is_not_accepted_as_a_document_database(self):
        self.raw();self.nav.refresh("past")
        data = json.loads(self.ws.path(CACHE).read_text())
        first = next(iter(data["entries"].values()))
        first["body"] = "Unexpected career body in a metadata cache"
        self.ws.path(CACHE).write_text(json.dumps(data))
        with self.assertRaises(StoreError) as caught:
            self.nav.catalog()
        self.assertEqual(caught.exception.code, "navigation_catalog")

    def test_identity_change_during_scan_does_not_publish_foreign_maps(self):
        self.nav.refresh("all");before = self.maps()
        original = self.nav._scan
        def changed(scope, checked):
            found = original(scope, checked)
            identity = json.loads(self.ws.path("manifest.json").read_text())
            import uuid
            identity["workspace_id"] = str(uuid.uuid4())
            self.ws.path("manifest.json").write_text(json.dumps(identity))
            return found
        with mock.patch.object(self.nav, "_scan", side_effect=changed), self.assertRaises(StoreError) as caught:
            self.nav.refresh("past")
        self.assertEqual(caught.exception.code, "navigation_identity")
        self.assertEqual(before, self.maps())

    def test_raw_folder_named_resumes_is_discovered_but_generated_resume_is_excluded(self):
        source = self.raw("past/materials/resumes/old.pdf", b"Fictional old resume")
        nested = self.raw("future/roles/产品/companies/甲/机会/materials/resumes/JD.pdf", b"Fictional JD")
        generated = self.raw("future/roles/产品/common/resumes/v-test/resume.html", b"Derived artifact")
        self.assertEqual([e["path"] for e in self.nav.refresh("past/materials/resumes")["entries"]], [source])
        result = self.nav.refresh("all")
        paths = [e["path"] for e in result["entries"]]
        self.assertIn(source, paths)
        self.assertIn(nested, paths)
        self.assertNotIn(generated, paths)
        with self.assertRaises(StoreError):
            self.nav.refresh("future/roles/产品/common/resumes")

    def test_link_rejects_a_source_or_record_edit_after_its_final_hash_verification(self):
        for kind in ("source", "record"):
            with self.subTest(kind=kind):
                source = self.raw("past/materials/" + kind + "-race.pdf", b"Fictional reviewed source")
                record = self.record("past/work/" + kind + "-race.md", source=source, id="work-" + kind)
                self.nav.refresh("past")
                before = self.maps()
                original = self.ws._verify_base
                calls = []
                def change_after_verification(base):
                    result = original(base)
                    calls.append(True)
                    if len(calls) == 2:
                        target = source if kind == "source" else record
                        self.ws.path(target).write_bytes(self.ws.path(target).read_bytes() + b" changed after verification")
                    return result
                with mock.patch.object(self.ws, "_verify_base", side_effect=change_after_verification), self.assertRaises(StoreError) as caught:
                    self.nav.link(source, [record])
                self.assertEqual(caught.exception.code, "conflict")
                self.assertEqual(len(calls), 2)
                self.assertEqual(before, self.maps())

    def test_post_replace_fsync_failure_recovers_the_attempted_destination(self):
        self.nav.refresh("all")
        before = self.maps()
        self.raw()
        original = navigation.atomic_write
        failed = []
        def replaced_then_failed(path, value):
            original(path, value)
            if Path(path) == self.ws.path("navigation/past.md") and value != before["navigation/past.md"] and not failed:
                failed.append(True)
                raise OSError("fictional directory fsync failed after replace")
        with mock.patch.object(navigation, "atomic_write", side_effect=replaced_then_failed), self.assertRaises(OSError):
            self.nav.refresh("past")
        self.assertTrue(failed)
        self.assertEqual(before, self.maps())

    def test_post_replace_failure_removes_only_the_newly_created_map(self):
        self.nav.refresh("all")
        for relative in self.maps():
            self.ws.path(relative).unlink()
        original = navigation.atomic_write
        failed = []
        def replaced_then_failed(path, value):
            original(path, value)
            if Path(path) == self.ws.path("MAP.md") and not failed:
                failed.append(True)
                raise OSError("fictional first-map fsync failed")
        with mock.patch.object(navigation, "atomic_write", side_effect=replaced_then_failed), self.assertRaises(OSError):
            self.nav.refresh("past")
        self.assertFalse(self.ws.path("MAP.md").exists())
        self.assertFalse(self.ws.path(CACHE).exists())

    def test_human_maps_show_minutes_in_utc_while_catalog_keeps_exact_timestamp(self):
        result = self.nav.refresh("past/materials")
        before = self.ws.path(CACHE).read_bytes()
        exact = result["checked_scopes"]["past/materials"]
        readable = navigation.display_time(exact)
        self.assertRegex(readable, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC$")
        self.assertIn(readable, self.ws.path("navigation/past.md").read_text())
        self.assertNotIn(exact, self.ws.path("navigation/past.md").read_text())
        self.assertIn(readable, self.ws.path("MAP.md").read_text())
        self.assertEqual(self.nav.catalog()["checked_scopes"]["past/materials"], exact)
        self.assertEqual(self.ws.path(CACHE).read_bytes(), before)
        self.assertEqual(navigation.display_time(None), "未检查")
        self.assertEqual(navigation.display_time("unknown"), "未检查")
        self.assertEqual(navigation.display_time("2026-10-26T08:12:33.123456"), "未检查")
        self.assertEqual(navigation.display_time("2026-10-26T08:12:33.123456+08:00"), "2026-10-26 00:12 UTC")


    def test_user_material_readmes_are_discovered_even_with_tool_guide_names(self):
        root = self.raw("past/materials/README.md", b"# My own evidence index\nA user material, not a tool guide.")
        nested = self.raw("past/materials/learning/README.md", b"# Learning material\nNo frontmatter")
        marked = self.raw("past/materials/another/README.md", navigation.guide_marker(self.ws.manifest()["workspace_id"]).encode() + b"user content")
        found = {e["path"]: e for e in self.nav.refresh("past")["entries"]}
        for path in (root, nested, marked):
            self.assertEqual(found[path]["kind"], "material")
        self.assertNotIn("past/README.md", found)

    def test_legacy_fixed_guides_skip_only_exact_known_locations_and_bytes(self):
        legacy = navigation.legacy_guide("past/materials/README.md")
        self.raw("past/materials/README.md", legacy.encode())
        nested = self.raw("past/materials/learning/README.md", legacy.encode())
        found = {e["path"] for e in self.nav.refresh("past")["entries"]}
        self.assertNotIn("past/materials/README.md", found)
        self.assertIn(nested, found)
        self.raw("past/materials/README.md", (legacy + "User addition\n").encode())
        self.assertIn("past/materials/README.md", {e["path"] for e in self.nav.refresh("past")["entries"]})

    def test_new_workspaces_have_resolvable_skill_candidates_and_real_commands(self):
        settings = json.loads(self.ws.path(navigation.SETTINGS).read_text())
        self.assertEqual(settings["language"], "zh")
        for candidate in (self.ws.root / settings["skill"]["relative_path"], Path(settings["skill"]["absolute_path"])):
            self.assertTrue((candidate / "SKILL.md").is_file())
        for path in ("AGENTS.md", "MAP.md", "AGENT-MAP.md"):
            body = self.ws.path(path).read_text()
            self.assertIn("SKILL.md", body)
            self.assertNotIn("<Skill根>", body)
        self.assertTrue(self.ws.path("从这里开始.md").exists())
        self.assertIn("scheduled_for", self.ws.path("从这里开始.md").read_text())
        self.assertEqual(set(self.ws.manifest()), {"schema_version", "workspace_id", "created_at"})
        import shlex
        command = next(line for line in self.ws.path("AGENT-MAP.md").read_text().splitlines() if line.startswith("python3 ") and " refresh " in line)
        result = subprocess.run(shlex.split(command), text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["scope"], "present")

    def test_english_initialization_localizes_guides_without_renaming_data_paths(self):
        english = Workspace(Path(self.temp.name) / "english")
        english.initialize(language="en")
        self.assertTrue(english.path("START-HERE.md").is_file())
        self.assertFalse(english.path("从这里开始.md").exists())
        for path in ("START-HERE.md", "MAP.md", "AGENT-MAP.md", "AGENTS.md", "past/README.md", "present/README.md", "future/README.md", "inbox/README.md"):
            body = english.path(path).read_text()
            # Local Skill paths can contain the host's Chinese directory name.
            prose = "\n".join(line for line in body.splitlines() if "求职页面" not in line)
            self.assertFalse(any("\u4e00" <= ch <= "\u9fff" for ch in prose), path)
        self.assertIn("past/materials/", english.path("START-HERE.md").read_text())
        self.assertIn("notes/", english.path("present/README.md").read_text())
        self.assertIn("companies/<company>/<opportunity>", english.path("future/README.md").read_text())
        self.assertEqual(set(english.manifest()), {"schema_version", "workspace_id", "created_at"})
        self.assertTrue(english.path("past/materials").is_dir())
        self.assertTrue(english.path("present/stages").is_dir())

    def test_standalone_checkpoints_are_directly_discoverable_without_items_or_body_reads(self):
        for language in ("zh", "en"):
            with self.subTest(language=language):
                ws = Workspace(Path(self.temp.name) / (language + "-notes-only"))
                ws.initialize(language=language)
                paths = {"present/notes/idea.md": "note", "present/stages/review.md": "stage-summary"}
                for path, kind in paths.items():
                    target = ws.path(path)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(dump_document({"id": kind, "type": kind, "title": kind,
                                                     "recorded_on": "2026-10-27"}, "Private body must not enter a map."))
                with mock.patch.object(ws, "read", side_effect=AssertionError("discovery must not read bodies")):
                    NavigationWorkspace(ws).refresh("present")
                entry = ws.path("AGENT-MAP.md").read_text()
                for path in paths:
                    self.assertIn("](" + path + ")", entry)
                self.assertNotIn("Private body", entry)

    def test_setup_relinks_only_owned_navigation_without_scanning_or_touching_records(self):
        record = self.record()
        original = self.ws.path(record).read_bytes()
        identity = self.ws.path("manifest.json").read_bytes()
        with mock.patch.object(self.nav, "_scan", side_effect=AssertionError("setup is not a rescan")), mock.patch.object(self.ws, "read", side_effect=AssertionError("setup reads no career bodies")):
            result = self.nav.setup(language="en", skill_root=Path(navigation.__file__).resolve().parent.parent)
        self.assertFalse(result["career_records_changed"])
        self.assertFalse(result["manifest_changed"])
        self.assertFalse(result["scan_performed"])
        self.assertEqual(self.ws.path(record).read_bytes(), original)
        self.assertEqual(self.ws.path("manifest.json").read_bytes(), identity)
        self.assertTrue(self.ws.path("START-HERE.md").is_file())
        self.assertTrue(self.ws.path("从这里开始.md").is_file())
        self.assertIn("Agent reading map", self.ws.path("AGENT-MAP.md").read_text())

    def test_setup_preserves_user_authored_guides_and_refuses_foreign_map(self):
        self.ws.path("AGENTS.md").write_text("# User-owned routing\n")
        self.ws.path("present/README.md").write_text("# User-owned area guide\n")
        result = self.nav.setup(language="en")
        self.assertEqual(set(result["preserved_user_guides"]), {"AGENTS.md", "present/README.md"})
        self.assertEqual(self.ws.path("AGENTS.md").read_text(), "# User-owned routing\n")
        self.assertEqual(self.ws.path("present/README.md").read_text(), "# User-owned area guide\n")
        self.ws.path("MAP.md").write_text("# User map\n")
        before = self.ws.path(navigation.SETTINGS).read_bytes()
        with self.assertRaises(StoreError) as caught:
            self.nav.setup(language="zh")
        self.assertEqual(caught.exception.code, "navigation_owned")
        self.assertEqual(self.ws.path(navigation.SETTINGS).read_bytes(), before)

    def test_move_and_explicit_relink_update_candidates_without_changing_identity(self):
        import shutil
        package = Path(self.temp.name) / "original-package"
        (package / "scripts").mkdir(parents=True)
        (package / "SKILL.md").write_text("# Fictional skill package\n")
        for name in ("md_navigation.py", "md_workspace.py"):
            shutil.copyfile(Path(navigation.__file__).with_name(name), package / "scripts" / name)
        self.nav.setup(skill_root=package)
        identity = self.ws.path("manifest.json").read_bytes()
        new_package = package.with_name("moved-package")
        package.rename(new_package)
        moved = self.ws.root.with_name("moved-workspace")
        self.ws.root.rename(moved)
        current = Workspace(moved)
        nav = NavigationWorkspace(current)
        nav.refresh("present")
        self.assertIn("候选目前不可用", current.path("AGENT-MAP.md").read_text())
        nav.setup(skill_root=new_package, language="en")
        self.assertEqual(current.path("manifest.json").read_bytes(), identity)
        settings = json.loads(current.path(navigation.SETTINGS).read_text())
        self.assertEqual(Path(settings["skill"]["absolute_path"]), new_package.resolve())
        self.assertEqual((moved / settings["skill"]["relative_path"]).resolve(), new_package.resolve())
        self.assertIn(str(new_package.resolve() / "SKILL.md"), current.path("AGENT-MAP.md").read_text())

    def test_setup_rejects_bad_language_or_skill_before_publication(self):
        before = self.maps()
        for language, root in (("fr", None), ("zh", Path(self.temp.name) / "not-a-skill")):
            with self.subTest(language=language), self.assertRaises(StoreError):
                self.nav.setup(language=language, skill_root=root)
            self.assertEqual(before, self.maps())
        empty = Workspace(Path(self.temp.name) / "bad-new")
        with self.assertRaises(StoreError):
            empty.initialize(language="fr")
        self.assertFalse(empty.root.exists())


if __name__ == "__main__":
    unittest.main()
