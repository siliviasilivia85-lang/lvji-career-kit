"""Isolated, wholly fictional store tests. Never use a personal workspace."""
import copy
import builtins
import errno
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

import md_workspace as store
from md_workspace import Workspace, StoreError, dump_document, parse_document, digest, atomic_write, json_bytes


class MarkdownTests(unittest.TestCase):
    def test_roundtrip_preserves_body_and_custom_metadata(self):
        metadata = {"id": "fictional", "type": "personal", "title": "虚构人物",
                    "custom": {"preferred": ["plain", 3, None, True]}}
        body = "\n# 一段资料\n\nNormal Markdown <script> is data.\n"
        self.assertEqual(parse_document(dump_document(metadata, body)), (metadata, body))

    def test_bare_strings_and_single_quotes(self):
        result, body = parse_document("---\nid: fictional\ntitle: 'A: person''s title'\nactive: true\n---\ntext\n")
        self.assertEqual(result["title"], "A: person's title")
        self.assertTrue(result["active"])
        self.assertEqual(body, "text\n")

    def test_unsafe_or_ambiguous_yaml_rejected(self):
        for header in ("a: &anchor x", "a: !python x", "a: |\n  multiline", "a: [invalid]", "a: 1\na: 2", "a:", "a: NaN"):
            with self.subTest(header=header), self.assertRaises(StoreError):
                parse_document("---\n" + header + "\n---\n")

    def test_missing_frontmatter_is_not_empty_data(self):
        for text in ("hello", "---\na: 1\n"):
            with self.assertRaises(StoreError):
                parse_document(text)


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="luji-fictional-test-")
        self.root = Path(self.temp.name) / "workspace"
        self.ws = Workspace(self.root)
        self.identity = self.ws.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def content(self, identifier, kind, title="虚构记录", **metadata):
        return dump_document({"id": identifier, "type": kind, "title": title, **metadata}, "\nA wholly fictional test record.\n")

    def draft(self, writes, extra=()):
        paths = list(writes) + list(extra)
        base = self.ws.read(list(dict.fromkeys(paths)))["draft_base"]
        return {"title": "虚构资料的具体草稿", "base": base,
                "writes": [{"path": p, "content": v} for p, v in writes.items()]}

    def save(self, writes, extra=()):
        proposal = self.ws.propose(self.draft(writes, extra))
        return self.ws.apply(proposal["proposal_id"], confirmed=True)

    def test_goal_decision_is_explicit_without_creating_execution(self):
        path="future/roles/探索/goal.md"
        self.save({path:self.content("explore", "goal", decision_status="exploring")})
        self.assertEqual(self.ws.read([path])["documents"][0]["metadata"]["decision_status"],"exploring")
        self.assertEqual(self.ws.index(types=["action"])["documents"],[])
        metadata,body=parse_document(self.ws.path(path).read_text())
        metadata["decision_status"]="adopted"
        self.save({path:dump_document(metadata,body)})
        self.assertEqual(self.ws.index(types=["action"])["documents"],[])

    def test_goal_decision_rejects_ambiguous_reserved_value(self):
        with self.assertRaises(StoreError):
            self.save({"future/roles/探索/goal.md":self.content("explore", "goal", decision_status=True)})

    def goal(self):
        path = "future/roles/产品目标/goal.md"
        self.save({path: self.content("product", "goal", "虚构产品方向")})
        return path

    def interview_fixture(self):
        goal = self.goal()
        work = "past/work/fictional-project.md"
        first = "future/roles/产品目标/companies/虚构甲/产品岗"
        second = "future/roles/产品目标/companies/虚构乙/产品岗"
        writes = {work: self.content("fictional-work", "work")}
        for name, location in (("first", first), ("second", second)):
            writes[location + "/jd.md"] = self.content("jd-" + name, "jd", role_id="product", company_id=name,
                                                      company_name="虚构" + name, opportunity_id="pm", collected_on="2026-10-23", requirements=["说明项目取舍"])
        writes[first + "/application.md"] = self.content("application-first", "application", role_id="product", company_id="first",
                                                        company_name="虚构甲", opportunity_id="pm", stage="preparing", updated_on="2026-10-23",
                                                        next_action="准备项目故事", history=[{"date": "2026-10-23", "stage": "preparing", "note": "虚构测试"}])
        self.save(writes)
        return {"goal": goal, "work": work, "first": first, "second": second,
                "common": "future/roles/产品目标/common/interviews", "application": first + "/application.md"}

    def interview_content(self, identifier, kind, source, **metadata):
        dated = {"interview-story": "updated_on", "interview-prep": "prepared_on", "interview-practice": "practiced_on"}
        return self.content(identifier, kind, role_id="product", sources=[source],
                            source_revisions={source: self.ws._revision(source)},
                            **{dated[kind]: "2026-10-23"}, **metadata)

    def test_interview_common_and_round_files_share_sources_without_changing_actions_or_stage(self):
        fixture = self.interview_fixture()
        story = fixture["common"] + "/stories/decision.md"
        common = fixture["common"] + "/prep-v1.md"
        first = fixture["first"] + "/interviews/round-1/prep-v1.md"
        second = fixture["second"] + "/interviews/round-2/prep-v1.md"
        practice = fixture["first"] + "/interviews/round-1/practice-1.md"
        application_before = self.ws.path(fixture["application"]).read_bytes()
        contents = {story: self.interview_content("story-decision", "interview-story", fixture["work"]),
                    common: self.interview_content("common-prep", "interview-prep", fixture["work"], interview_on=None),
                    first: self.interview_content("first-prep", "interview-prep", fixture["first"] + "/jd.md", company_id="first", opportunity_id="pm", round_id="round-1", interview_on="2026-10-25"),
                    second: self.interview_content("second-prep", "interview-prep", fixture["second"] + "/jd.md", company_id="second", opportunity_id="pm", round_id="round-2"),
                    practice: self.interview_content("first-practice", "interview-practice", fixture["work"], company_id="first", opportunity_id="pm", round_id="round-1")}
        draft = self.draft(contents, [fixture["work"], fixture["first"] + "/jd.md", fixture["second"] + "/jd.md"])
        proposal = self.ws.propose(draft)
        self.assertTrue(all(not self.ws.path(p).exists() for p in contents))
        with self.assertRaises(StoreError) as denied:
            self.ws.apply(proposal["proposal_id"])
        self.assertEqual(denied.exception.code, "confirmation_required")
        self.ws.apply(proposal["proposal_id"], True)
        read = self.ws.read(list(contents))
        self.assertEqual({d["path"] for d in read["documents"]}, set(contents))
        self.assertEqual(self.ws.path(fixture["application"]).read_bytes(), application_before)
        self.assertEqual(self.ws.index(types=["action"])["documents"], [])
        self.assertEqual(self.ws.manifest()["schema_version"], "luji-markdown-0.1")
        self.assertEqual(self.ws.validate()["warnings"], [])

    def test_interview_material_rejects_mixed_company_scope_and_unknown_opportunity(self):
        fixture = self.interview_fixture()
        target = fixture["first"] + "/interviews/round-1/prep.md"
        for metadata in ({"company_id": "first"}, {"opportunity_id": "pm"},
                         {"company_id": "second", "opportunity_id": "pm", "round_id": "round-1"},
                         {"company_id": "first", "opportunity_id": "missing", "round_id": "round-1"}):
            with self.subTest(metadata=metadata), self.assertRaises(StoreError) as error:
                self.save({target: self.interview_content("interview", "interview-prep", fixture["work"], **metadata)}, [fixture["work"]])
            self.assertEqual(error.exception.code, "invalid_scope")
        self.assertFalse(self.ws.path(target).exists())

    def test_interview_role_directory_resolves_real_goal_path_instead_of_assuming_id(self):
        fixture = self.interview_fixture()
        self.save({"future/roles/另一个目录/goal.md": self.content("another", "goal")})
        misplaced = "future/roles/另一个目录/common/interviews/prep.md"
        with self.assertRaises(StoreError) as error:
            self.save({misplaced: self.interview_content("misplaced-prep", "interview-prep", fixture["work"])}, [fixture["work"]])
        self.assertEqual(error.exception.code, "invalid_scope")
        correct = fixture["common"] + "/prep.md"
        self.save({correct: self.interview_content("correct-prep", "interview-prep", fixture["work"])}, [fixture["work"]])
        self.assertTrue(self.ws.validate()["ok"])

    def test_interview_dates_rounds_and_story_location_are_validated(self):
        fixture = self.interview_fixture()
        valid = {"id": "prep", "type": "interview-prep", "title": "虚构准备", "role_id": "product", "prepared_on": "2026-10-23", "sources": [fixture["work"]]}
        cases = [(fixture["common"] + "/prep.md", {**valid, "prepared_on": "2026-02-30"}),
                 (fixture["common"] + "/prep.md", {**valid, "interview_on": "next Friday"}),
                 (fixture["common"] + "/prep.md", {**valid, "round_id": "round-1"}),
                 (fixture["first"] + "/interviews/round-1/prep.md", {**valid, "company_id": "first", "opportunity_id": "pm"}),
                 (fixture["first"] + "/interviews/round-1/prep.md", {**valid, "company_id": "first", "opportunity_id": "pm", "round_id": "../bad"}),
                 (fixture["common"] + "/story.md", {"id": "story", "type": "interview-story", "title": "虚构故事", "role_id": "product", "updated_on": "2026-10-23", "sources": [fixture["work"]]}),
                 (fixture["common"] + "/prep.md", {**valid, "sources": []})]
        for path, metadata in cases:
            with self.subTest(path=path, metadata=metadata), self.assertRaises(StoreError):
                self.save({path: dump_document(metadata, "A fictional draft")}, [fixture["work"]])
        practice = fixture["common"] + "/practice.md"
        self.save({practice: self.interview_content("common-practice", "interview-practice", fixture["work"])}, [fixture["work"]])
        self.assertEqual(self.ws.read([practice])["documents"][0]["metadata"]["practiced_on"], "2026-10-23")

    def test_interview_source_conflict_keeps_preparation_unwritten_and_application_unchanged(self):
        fixture = self.interview_fixture()
        target = fixture["first"] + "/interviews/round-1/prep.md"
        content = self.interview_content("prep", "interview-prep", fixture["work"], company_id="first", opportunity_id="pm", round_id="round-1")
        proposal = self.ws.propose(self.draft({target: content}, [fixture["work"]]))
        application = self.ws.path(fixture["application"]).read_bytes()
        atomic_write(self.ws.path(fixture["work"]), self.content("fictional-work", "work", title="手动更新的真实来源").encode())
        with self.assertRaises(StoreError) as error:
            self.ws.apply(proposal["proposal_id"], True)
        self.assertEqual(error.exception.code, "conflict")
        self.assertFalse(self.ws.path(target).exists())
        self.assertEqual(self.ws.path(fixture["application"]).read_bytes(), application)

    def test_interview_revision_warnings_and_context_follow_shared_story_provenance(self):
        fixture = self.interview_fixture()
        story = fixture["common"] + "/stories/decision.md"
        self.save({story: self.interview_content("story", "interview-story", fixture["work"])}, [fixture["work"]])
        target = fixture["common"] + "/prep.md"
        content = self.interview_content("prep", "interview-prep", story)
        base = self.ws.context([target, story])["draft_base"]
        proposal = self.ws.propose({"title": "虚构准备稿", "base": base, "writes": [{"path": target, "content": content}]})
        self.ws.apply(proposal["proposal_id"], True)
        self.assertEqual(set(self.ws.context([target])["source_paths"]), {story, fixture["work"]})
        atomic_write(self.ws.path(fixture["work"]), self.content("fictional-work", "work", title="更新来源").encode())
        validation = self.ws.validate()
        self.assertTrue(validation["ok"])
        self.assertTrue(any(w["code"] == "stale_sources" and w["path"] == story for w in validation["warnings"]))
        meta, body = parse_document(self.ws.path(target).read_text())
        meta.pop("source_revisions")
        atomic_write(self.ws.path(target), dump_document(meta, body).encode())
        self.assertTrue(any(w["code"] == "untracked_sources" and w["path"] == target for w in self.ws.validate()["warnings"]))

    def test_interview_story_cannot_be_promoted_to_resume_fact_by_reference(self):
        from md_resume import ResumeWorkspace
        fixture = self.interview_fixture()
        person = "past/personal.md"
        self.save({person: self.content("person", "personal")})
        story = fixture["common"] + "/stories/decision.md"
        self.save({story: self.interview_content("story", "interview-story", fixture["work"])}, [fixture["work"]])
        resume = ResumeWorkspace(self.ws)
        self.assertNotIn(story, [d["path"] for d in resume.context("product")["candidates"]])
        content = {"person": {"name": "虚构人物", "headline": "产品方向", "contacts": []},
                   "summary": {"text": "仅从练习稿摘出的断言", "source_paths": [story]}, "sections": [], "source_paths": [person, story]}
        with self.assertRaises(StoreError) as error:
            resume.build(content, "product")
        self.assertEqual(error.exception.code, "invalid_claim_source")

    def test_initialize_identity_only_and_no_fake_facts(self):
        self.assertEqual(set(self.ws.manifest()), {"schema_version", "workspace_id", "created_at"})
        self.assertEqual(self.ws.index()["documents"], [])
        self.assertTrue((self.root / "present/items").is_dir())
        self.assertTrue(self.ws.validate()["ok"])
        with self.assertRaises(StoreError):
            self.ws.initialize()

    def test_nonempty_or_old_formats_never_migrated(self):
        other = Path(self.temp.name) / "old"
        other.mkdir()
        (other / "manifest.json").write_text('{"schema_version":"luji-kit-0.1"}')
        old = Workspace(other)
        with self.assertRaises(StoreError):
            old.initialize()
        with self.assertRaises(StoreError) as error:
            old.manifest()
        self.assertEqual(error.exception.code, "unsupported_workspace")

    def test_path_safety(self):
        for path in ("/etc/passwd", "../x", "past/../x", "past\\x", "past//x", "C:/x", "", "past/./x", "past/x\x00.md"):
            with self.subTest(path=path), self.assertRaises(StoreError):
                self.ws.path(path)
        (self.root / "past/link").symlink_to(self.temp.name, target_is_directory=True)
        with self.assertRaises(StoreError):
            self.ws.path("past/link/file.md")
        with self.assertRaises(StoreError):
            self.ws.index()

    def test_material_path_contract_is_additive_and_does_not_capture_records(self):
        accepted = ["inbox/resume.pdf", "inbox/sub/普通笔记.md", "past/materials/简历.docx",
                    "present/materials/课程.pdf", "present/items/作品/materials/结果.csv",
                    "future/materials/招聘.png", "future/roles/产品/materials/方向.md",
                    "future/roles/产品/companies/星桥/机会/materials/JD.pdf"]
        rejected = [None, "", "inbox", "past/materials", "../inbox/x", "/inbox/x",
                    "C:/inbox/x", "past\\materials\\x", "past/materials/../x",
                    "past/work/经历.md", "present/items/作品.md", "future/roles/产品/goal.md",
                    "future/roles/产品/common/materials/x.pdf", "present/items/materials/x.pdf"]
        for path in accepted:
            with self.subTest(path=path):
                self.assertTrue(store.is_material_path(path))
        for path in rejected:
            with self.subTest(path=path):
                self.assertFalse(store.is_material_path(path))
        for location in ("inbox", "past/materials", "present/materials", "future/materials"):
            self.assertTrue(self.ws.path(location + "/README.md").is_file())
        self.assertEqual(self.ws.manifest()["schema_version"], "luji-markdown-0.1")

    def test_directly_dropped_sources_need_no_frontmatter_and_do_not_create_facts(self):
        paths = ["inbox/简历.pdf", "past/materials/学习笔记.md", "present/materials/课程.docx",
                 "present/items/作品/materials/截图.png", "future/materials/方向.txt",
                 "future/roles/产品/materials/公开观察.md",
                 "future/roles/产品/companies/星桥/机会/materials/JD.md"]
        for path in paths:
            atomic_write(self.ws.path(path), b"Fictional ordinary supplied content, no frontmatter.")
        result = self.ws.read(paths)
        self.assertEqual(set(result["draft_base"]["files"]), set(paths))
        self.assertTrue(all(d["metadata"]["type"] == "source" and "body" not in d for d in result["documents"]))
        self.assertEqual(self.ws.index()["documents"], [])
        self.assertTrue(self.ws.validate()["ok"])

    def test_index_never_opens_directly_dropped_material_content(self):
        formal = "past/work/one.md"
        self.save({formal: self.content("one", "work")})
        source = "past/materials/普通文件.md"
        atomic_write(self.ws.path(source), b"not frontmatter; must not be opened by index")
        original_open = store._open_regular
        def guarded(path):
            if store.is_material_path(Path(path).relative_to(self.ws.root).as_posix()):
                raise AssertionError("index read a raw material")
            return original_open(path)
        with mock.patch.object(store, "_open_regular", side_effect=guarded), mock.patch.object(self.ws, "_bytes", side_effect=AssertionError("index hashes no bodies")):
            result = self.ws.index()
        self.assertEqual([d["path"] for d in result["documents"]], [formal])

    def test_dropped_material_proposal_freezes_source_and_still_needs_confirmation(self):
        source, target = "inbox/我的简历.md", "past/work/新经历.md"
        atomic_write(self.ws.path(source), b"A wholly fictional source resume, manually dropped.")
        context = self.ws.context([target, source])
        content = self.content("manual-work", "work", sources=[source],
                               source_revisions={source: context["draft_base"]["files"][source]})
        proposal = self.ws.propose({"title": "虚构新增经历草稿", "base": context["draft_base"],
                                    "writes": [{"path": target, "content": content}]})
        self.assertFalse(self.ws.path(target).exists())
        with self.assertRaises(StoreError) as error:
            self.ws.apply(proposal["proposal_id"])
        self.assertEqual(error.exception.code, "confirmation_required")
        self.ws.apply(proposal["proposal_id"], confirmed=True)
        read = self.ws.context([target])
        self.assertEqual(read["source_paths"], [source])
        self.assertNotIn("body", next(d for d in read["documents"] if d["path"] == source))
        self.assertTrue(self.ws.validate()["ok"])

    def test_changed_dropped_material_blocks_old_proposal_without_overwriting_fact(self):
        source, target = "future/roles/产品/companies/星桥/机会/materials/JD.txt", "past/work/经历.md"
        atomic_write(self.ws.path(source), b"Fictional first supplied source.")
        content = self.content("fictional-source-backed-work", "work", sources=[source])
        proposal = self.ws.propose(self.draft({target: content}, [source]))
        atomic_write(self.ws.path(source), b"A different fictional source supplied later.")
        with self.assertRaises(StoreError) as error:
            self.ws.apply(proposal["proposal_id"], confirmed=True)
        self.assertEqual(error.exception.code, "conflict")
        self.assertFalse(self.ws.path(target).exists())
        self.assertEqual(self.ws.path(source).read_bytes(), b"A different fictional source supplied later.")

    def test_agent_cannot_propose_overwriting_material_or_forge_a_receipt(self):
        source = "past/materials/普通笔记.md"
        original = b"The user's ordinary Markdown source."
        atomic_write(self.ws.path(source), original)
        atomic_write(self.ws.path(source + ".receipt.json"), b"not a tool receipt")
        result = self.ws.read([source])["documents"][0]
        self.assertEqual(result["metadata"], {"type": "source", "title": "普通笔记.md"})
        with self.assertRaises(StoreError) as error:
            self.ws.propose(self.draft({source: self.content("fake", "work")}))
        self.assertEqual(error.exception.code, "not_canonical")
        self.assertEqual(self.ws.path(source).read_bytes(), original)

    def test_material_source_limits_and_symlinks_are_enforced(self):
        source = "present/materials/ordinary.bin"
        atomic_write(self.ws.path(source), b"x" * 100)
        with mock.patch.object(store, "MAX_DOCUMENT_BYTES", 20), mock.patch.object(store, "MAX_SOURCE_BYTES", 200):
            self.assertEqual(self.ws.read([source])["documents"][0]["metadata"]["type"], "source")
        with mock.patch.object(store, "MAX_SOURCE_BYTES", 50), self.assertRaises(StoreError) as error:
            self.ws.read([source])
        self.assertEqual(error.exception.code, "too_large")
        linked = self.ws.path("past/materials/linked.txt")
        linked.symlink_to(self.ws.path(source))
        with self.assertRaises(StoreError) as error:
            self.ws.read(["past/materials/linked.txt"])
        self.assertEqual(error.exception.code, "unsafe_path")

    def test_photo_note_can_reference_explicit_user_photo_drop_location(self):
        source, target = "past/materials/照片.png", "past/photos/照片说明.md"
        atomic_write(self.ws.path(source), b"Fictional photo payload; image renderer separately verifies image format.")
        self.save({target: self.content("manual-photo", "photo-note", asset_path=source)}, [source])
        self.assertEqual(self.ws.read([target])["documents"][0]["metadata"]["asset_path"], source)

    def test_partial_read_and_null_baseline(self):
        first, second = "past/work/one.md", "past/work/two.md"
        self.save({first: self.content("one", "work"), second: self.content("two", "work")})
        read_bytes = self.ws._bytes
        with mock.patch.object(self.ws, "_bytes", wraps=read_bytes) as spy:
            result = self.ws.read([first, "present/actions/new.md"])
        self.assertEqual([d["path"] for d in result["documents"]], [first])
        self.assertEqual(set(result["draft_base"]["files"]), {first, "present/actions/new.md"})
        self.assertIsNone(result["draft_base"]["files"]["present/actions/new.md"])
        self.assertNotIn(second, [call.args[0] for call in spy.call_args_list])
        self.assertNotIn("---", result["documents"][0]["body"])

    def test_index_metadata_only_and_derived_excluded(self):
        path = "past/work/one.md"
        self.save({path: self.content("one", "work", custom_color="green")})
        derived = self.ws.path("future/roles/fake/common/resumes/v-fake/content.md")
        atomic_write(derived, b"not canonical frontmatter")
        original = self.ws.path("past/originals/reference/manual.md")
        atomic_write(original, b"source is not a record")
        with mock.patch.object(self.ws, "_bytes", side_effect=AssertionError("index must not hash/read source bodies")):
            result = self.ws.index()
        self.assertEqual(len(result["documents"]), 1)
        self.assertNotIn("body", result["documents"][0])
        self.assertEqual(result["documents"][0]["metadata"]["custom_color"], "green")

    def test_corrupt_md_and_invalid_utf8_fail(self):
        path = self.ws.path("past/work/broken.md")
        atomic_write(path, b"not a record")
        with self.assertRaises(StoreError):
            self.ws.index()
        self.assertFalse(self.ws.validate()["ok"])
        atomic_write(path, b"---\nid: \xff\n---\n")
        with self.assertRaises(StoreError):
            self.ws.read(["past/work/broken.md"])

    def test_source_import_receipt_and_binary_read(self):
        original = Path(self.temp.name) / "fictional evidence.txt"
        original.write_bytes(b"fictional source bytes")
        receipt = self.ws.import_source(original, "evidence")
        self.assertEqual(receipt["original_name"], original.name)
        self.assertEqual(receipt["sha"], digest(original.read_bytes()))
        result = self.ws.read([receipt["source_path"]])["documents"][0]
        self.assertEqual(result["metadata"]["type"], "source")
        self.assertNotIn("body", result)
        self.assertEqual(self.ws.index()["documents"], [])

    def test_source_symlink_fifo_and_size_rejected(self):
        original = Path(self.temp.name) / "original"
        original.write_text("fictional")
        link = Path(self.temp.name) / "link"
        link.symlink_to(original)
        with self.assertRaises(StoreError):
            self.ws.import_source(link)
        if hasattr(os, "mkfifo"):
            fifo = Path(self.temp.name) / "fifo"
            os.mkfifo(fifo)
            with self.assertRaises(StoreError):
                self.ws.import_source(fifo)
        with mock.patch.object(store, "MAX_SOURCE_BYTES", 3), self.assertRaises(StoreError):
            self.ws.import_source(original)

    def test_only_canonical_sources_can_be_read_or_written(self):
        for path in ("views/overview.html", "career.json", "manifest.json", "https://example.invalid/x.md", "future/roles/x/common/resumes/v-x/resume.md"):
            with self.subTest(path=path), self.assertRaises(StoreError):
                self.ws.read([path])

    def test_new_goal_needs_no_jd_or_past(self):
        self.goal()
        self.assertTrue(self.ws.validate()["ok"])

    def test_proposal_is_concrete_and_requires_confirmation(self):
        path = "past/personal.md"
        draft = self.draft({path: self.content("person", "personal", contacts=["fictional@example.invalid"])})
        proposal = self.ws.propose(draft)
        self.assertEqual(proposal["draft"], draft)
        self.assertFalse(self.ws.path(path).exists())
        for confirmation in (False, None, "true", 1):
            with self.assertRaises(StoreError) as error:
                self.ws.apply(proposal["proposal_id"], confirmed=confirmation)
            self.assertEqual(error.exception.code, "confirmation_required")
        self.assertEqual(self.ws.apply(proposal["proposal_id"], True)["status"], "applied")
        self.assertEqual(self.ws.apply(proposal["proposal_id"], True)["status"], "already_applied")

    def test_conflict_on_target_prevents_overwrite(self):
        path = "past/work/one.md"
        self.save({path: self.content("one", "work")})
        proposal = self.ws.propose(self.draft({path: self.content("one", "work", title="proposed")}))
        manual = self.content("one", "work", title="manual edit")
        atomic_write(self.ws.path(path), manual.encode())
        with self.assertRaises(StoreError) as error:
            self.ws.apply(proposal["proposal_id"], True)
        self.assertEqual(error.exception.code, "conflict")
        self.assertEqual(self.ws.path(path).read_text(), manual)

    def test_conflict_on_used_source_but_unrelated_changes_allowed(self):
        source, unrelated, target = "past/work/source.md", "past/work/other.md", "past/profile.md"
        self.save({source: self.content("source", "work"), unrelated: self.content("other", "work")})
        content = self.content("profile", "portrait", sources=[source])
        proposal = self.ws.propose(self.draft({target: content}, [source]))
        atomic_write(self.ws.path(unrelated), self.content("other", "work", title="manual unrelated").encode())
        self.assertEqual(self.ws.apply(proposal["proposal_id"], True)["status"], "applied")
        proposal = self.ws.propose(self.draft({target: content}, [source]))
        atomic_write(self.ws.path(source), self.content("source", "work", title="changed source").encode())
        with self.assertRaises(StoreError) as error:
            self.ws.apply(proposal["proposal_id"], True)
        self.assertEqual(error.exception.code, "conflict")

    def test_all_source_lineage_requires_actual_baseline(self):
        original = Path(self.temp.name) / "fictional.txt"
        original.write_text("a fictional supplied original")
        source = self.ws.import_source(original)["source_path"]
        work, profile = "past/work/one.md", "past/profile.md"
        self.save({work: self.content("one", "work", sources=[source])}, [source])
        draft = self.draft({profile: self.content("profile", "portrait", sources=[work])}, [work])
        with self.assertRaises(StoreError) as error:
            self.ws.propose(draft)
        self.assertEqual(error.exception.code, "missing_base")
        self.save({profile: self.content("profile", "portrait", sources=[work])}, [work, source])

    def test_new_sources_in_same_multi_file_draft(self):
        source, target = "past/work/new.md", "past/profile.md"
        self.save({source: self.content("new", "work"), target: self.content("profile", "portrait", sources=[source])})
        self.assertEqual(self.ws.validate()["documents_count"], 2)

    def test_id_type_and_source_history_are_stable(self):
        source, target = "past/work/one.md", "past/profile.md"
        self.save({source: self.content("one", "work"), target: self.content("profile", "portrait", sources=[source])})
        for content, code in ((self.content("changed", "portrait", sources=[source]), "identity_change"),
                              (self.content("profile", "work", sources=[source]), "identity_change"),
                              (self.content("profile", "portrait"), "source_history")):
            with self.subTest(code=code), self.assertRaises(StoreError) as error:
                self.ws.propose(self.draft({target: content}, [source]))
            self.assertEqual(error.exception.code, code)

    def test_duplicate_id_and_typed_area_rejected(self):
        self.save({"past/work/one.md": self.content("one", "work")})
        for path, content in (("past/work/two.md", self.content("one", "work")),
                              ("present/actions/one.md", self.content("other", "work")),
                              ("present/items.md", self.content("item", "item"))):
            with self.subTest(path=path), self.assertRaises(StoreError):
                self.ws.propose(self.draft({path: content}))

    def test_dates_unknown_times_and_custom_fields(self):
        path = "present/actions/action.md"
        self.save({path: self.content("action", "action", status="todo", scheduled_for=None, due_on=None,
                                      minutes=None, spent_minutes=None, depends_on=[], custom_note={"energy": "unknown"})})
        metadata = self.ws.read([path])["documents"][0]["metadata"]
        self.assertIsNone(metadata["minutes"])
        self.assertEqual(metadata["custom_note"], {"energy": "unknown"})
        for values in ({"scheduled_for": "2026-02-30"}, {"minutes": -1}, {"minutes": True}, {"status": "magic"}):
            bad = {"status": "todo", **values}
            with self.subTest(values=values), self.assertRaises(StoreError):
                self.ws.propose(self.draft({path: self.content("action", "action", **bad)}))

    def test_action_dependencies_existing_and_acyclic(self):
        first, second = "present/actions/one.md", "present/actions/two.md"
        self.save({first: self.content("one", "action", status="todo"),
                   second: self.content("two", "action", status="todo", depends_on=["one"])})
        for dependencies, code in ((["two"], "dependency_cycle"), (["missing"], "missing_reference")):
            with self.subTest(code=code), self.assertRaises(StoreError) as error:
                self.ws.propose(self.draft({first: self.content("one", "action", status="todo", depends_on=dependencies)}))
            self.assertEqual(error.exception.code, code)

    def test_plan_references_one_action_set(self):
        action, plan = "present/actions/one.md", "present/plans/weekly/week.md"
        self.save({action: self.content("one", "action", status="doing", scheduled_for="2026-10-23"),
                   plan: self.content("week", "plan", period="weekly", start_date="2026-10-19", end_date="2026-10-25", action_ids=["one"])})
        self.assertTrue(self.ws.validate()["ok"])

    def test_sources_and_id_references_cannot_be_missing(self):
        path = "past/work/test.md"
        for values in ({"sources": ["past/work/missing.md"]}, {"related_ids": ["missing"]}):
            paths = values.get("sources", [])
            with self.subTest(values=values), self.assertRaises(StoreError):
                self.ws.propose(self.draft({path: self.content("test", "work", **values)}, paths))

    def test_source_cycles_rejected(self):
        first, second = "past/work/one.md", "past/work/two.md"
        with self.assertRaises(StoreError) as error:
            self.ws.propose(self.draft({first: self.content("one", "work", sources=[second]), second: self.content("two", "work", sources=[first])}))
        self.assertEqual(error.exception.code, "source_cycle")

    def test_application_history_append_only_and_scope_stable(self):
        goal = self.goal()
        path = "future/roles/产品目标/companies/虚构公司/opening/application.md"
        old = [{"date": "2026-10-22", "stage": "researching", "note": "fictional research"}]
        def application(history, stage="researching", **values):
            metadata = dict(role_id="product", company_id="fictional-co", company_name="虚构公司", opportunity_id="opening", stage=stage,
                            updated_on="2026-10-23", next_action="用户决定下一步", history=history, sources=[goal])
            metadata.update(values)
            return self.content("application", "application", **metadata)
        self.save({path: application(old)}, [goal])
        appended = old + [{"date": "2026-10-23", "stage": "preparing", "note": "fictional preparation"}]
        self.save({path: application(appended, "preparing")}, [goal])
        for content in (application([], "preparing"), application(appended, "interview"), application(appended, "preparing", company_id="other-co")):
            with self.assertRaises(StoreError):
                self.ws.propose(self.draft({path: content}, [goal]))

    def test_assessment_supported_requires_evidence_and_sources(self):
        self.goal()
        path = "future/roles/产品目标/assessment.md"
        criterion = {"requirement": "fictional capability", "status": "supported", "evidence": [], "note": ""}
        with self.assertRaises(StoreError) as error:
            self.ws.propose(self.draft({path: self.content("assessment", "assessment", role_id="product", evaluated_on="2026-10-23", criteria=[criterion])}))
        self.assertEqual(error.exception.code, "missing_evidence")

    def test_completed_activity_is_not_confirmed_capability(self):
        self.goal()
        log, assessment = "present/learning/day.md", "future/roles/产品目标/assessment.md"
        self.save({log: self.content("log", "learning-log", recorded_on="2026-10-23", evidence_status="record")})
        criterion = {"requirement": "fictional capability", "status": "partial", "evidence": [log], "note": ""}
        with self.assertRaises(StoreError) as error:
            self.ws.propose(self.draft({assessment: self.content("assessment", "assessment", role_id="product", evaluated_on="2026-10-23", criteria=[criterion], sources=[log])}, [log]))
        self.assertEqual(error.exception.code, "unconfirmed_evidence")

    def test_derived_freshness_warning_never_rewrites_record(self):
        source, profile = "past/work/one.md", "past/profile.md"
        self.save({source: self.content("one", "work")})
        revision = self.ws.read([source])["draft_base"]["files"][source]
        self.save({profile: self.content("profile", "portrait", sources=[source], source_revisions={source: revision})}, [source])
        self.assertEqual(self.ws.validate()["warnings"], [])
        before = self.ws.path(profile).read_bytes()
        atomic_write(self.ws.path(source), self.content("one", "work", title="manually changed").encode())
        result = self.ws.validate()
        self.assertTrue(result["ok"])
        self.assertEqual(result["warnings"][0]["code"], "stale_sources")
        self.assertEqual(self.ws.path(profile).read_bytes(), before)

    def test_untracked_source_warning(self):
        source, profile = "past/work/one.md", "past/profile.md"
        self.save({source: self.content("one", "work"), profile: self.content("profile", "portrait", sources=[source])})
        self.assertEqual(self.ws.validate()["warnings"][0]["code"], "untracked_sources")

    def test_history_preserves_actual_source_baseline(self):
        source, target = "past/work/source.md", "past/profile.md"
        self.save({source: self.content("source", "work")})
        before = self.ws.path(source).read_bytes()
        result = self.save({target: self.content("profile", "portrait", sources=[source])}, [source])
        baseline = self.ws.path(f".luji/history/{result['proposal_id']}/baseline/{source}")
        self.assertEqual(baseline.read_bytes(), before)

    def test_multi_file_failure_rolls_back_all_and_reports_failure(self):
        first, second = "past/work/one.md", "past/work/two.md"
        self.save({first: self.content("one", "work")})
        before = self.ws.path(first).read_bytes()
        proposal = self.ws.propose(self.draft({first: self.content("one", "work", title="new"), second: self.content("two", "work")}))
        real = store.atomic_write
        def fail_second(path, raw):
            if Path(path) == self.ws.path(second):
                raise OSError("simulated disk failure")
            return real(path, raw)
        with mock.patch.object(store, "atomic_write", side_effect=fail_second), self.assertRaises(StoreError):
            self.ws.apply(proposal["proposal_id"], True)
        self.assertEqual(self.ws.path(first).read_bytes(), before)
        self.assertFalse(self.ws.path(second).exists())
        self.assertTrue(self.ws.validate()["ok"])

    def test_interrupted_apply_blocks_reads_and_recovers_on_retry(self):
        first, second = "past/work/one.md", "past/work/two.md"
        proposal = self.ws.propose(self.draft({first: self.content("one", "work"), second: self.content("two", "work")}))
        real = store.atomic_write
        def crash(path, raw):
            if Path(path) == self.ws.path(second):
                raise KeyboardInterrupt("simulated abrupt process interruption")
            return real(path, raw)
        with mock.patch.object(store, "atomic_write", side_effect=crash), self.assertRaises(KeyboardInterrupt):
            self.ws.apply(proposal["proposal_id"], True)
        with self.assertRaises(StoreError) as error:
            self.ws.index()
        self.assertEqual(error.exception.code, "recovery_required")
        self.assertEqual(self.ws.apply(proposal["proposal_id"], True)["status"], "applied")
        self.assertEqual(len(self.ws.index()["documents"]), 2)

    def test_recovery_preserves_external_edit_and_reports_conflict(self):
        first, second = "past/work/one.md", "past/work/two.md"
        proposal = self.ws.propose(self.draft({first: self.content("one", "work"), second: self.content("two", "work")}))
        real = store.atomic_write
        def crash(path, raw):
            if Path(path) == self.ws.path(second):
                raise KeyboardInterrupt()
            return real(path, raw)
        with mock.patch.object(store, "atomic_write", side_effect=crash), self.assertRaises(KeyboardInterrupt):
            self.ws.apply(proposal["proposal_id"], True)
        manual = self.content("one", "work", title="user edit during interruption")
        real(self.ws.path(first), manual.encode())
        with self.assertRaises(StoreError) as error:
            self.ws.apply(proposal["proposal_id"], True)
        self.assertEqual(error.exception.code, "recovery_conflict")
        self.assertEqual(self.ws.path(first).read_text(), manual)

    def test_committed_transaction_recovers_missing_proposal_marker(self):
        path = "past/work/one.md"
        proposal = self.ws.propose(self.draft({path: self.content("one", "work")}))
        proposal_path = self.ws.path(f".luji/proposals/{proposal['proposal_id']}.json")
        real = store.atomic_write
        def lose_marker(target, raw):
            if Path(target) == proposal_path:
                raise OSError("simulated lost final response")
            return real(target, raw)
        with mock.patch.object(store, "atomic_write", side_effect=lose_marker), self.assertRaises(OSError):
            self.ws.apply(proposal["proposal_id"], True)
        self.assertEqual(self.ws.apply(proposal["proposal_id"], True)["status"], "already_applied")

    def windows_lock(self, side_effect=None):
        fake = types.SimpleNamespace(LK_NBLCK=1, LK_UNLCK=2, locking=mock.Mock(side_effect=side_effect))
        real_import = builtins.__import__
        def importing(name, *args, **kwargs):
            if name == "fcntl":
                raise ImportError("simulated Windows without fcntl")
            if name == "msvcrt":
                return fake
            return real_import(name, *args, **kwargs)
        return fake, mock.patch("builtins.__import__", side_effect=importing)

    def test_windows_byte_lock_branch_and_release_mocked(self):
        fake, patch = self.windows_lock()
        with patch:
            with self.ws._lock():
                self.assertEqual(self.ws.path(".luji/write.lock").read_bytes(), b"\0")
        self.assertEqual([call.args[1:] for call in fake.locking.call_args_list], [(1, 1), (2, 1)])

    def test_windows_byte_lock_busy_mocked(self):
        fake, patch = self.windows_lock(OSError(errno.EACCES, "simulated existing lock"))
        with patch, self.assertRaises(StoreError) as error:
            with self.ws._lock():
                self.fail("must not enter")
        self.assertEqual(error.exception.code, "locked")
        self.assertEqual(fake.locking.call_count, 1)

    def test_second_writer_fails_without_waiting(self):
        with self.ws._lock():
            with self.assertRaises(StoreError) as error:
                with Workspace(self.root)._lock():
                    self.fail("must not acquire a second lock")
        self.assertEqual(error.exception.code, "locked")

    def test_full_validation_detects_bad_body_encoding_without_index_body_read(self):
        path = "past/work/one.md"
        raw = self.content("one", "work").encode() + b"\xff"
        atomic_write(self.ws.path(path), raw)
        self.assertEqual(len(self.ws.index()["documents"]), 1)
        result = self.ws.validate()
        self.assertFalse(result["ok"])
        self.assertEqual(result["errors"][0]["code"], "encoding")

    def test_damaged_history_is_an_explicit_error(self):
        atomic_write(self.ws.path(".luji/history/damaged/journal.json"), json_bytes({"state": "writing", "files": [{}]}))
        with self.assertRaises(StoreError) as error:
            self.ws.index()
        self.assertEqual(error.exception.code, "damaged_history")

    def test_source_changed_during_apply_rolls_back_destinations(self):
        source, target = "past/work/source.md", "past/profile.md"
        self.save({source: self.content("source", "work")})
        proposal = self.ws.propose(self.draft({target: self.content("profile", "portrait", sources=[source])}, [source]))
        real = store.atomic_write
        manual = self.content("source", "work", title="external edit during apply")
        def change_source(path, raw):
            result = real(path, raw)
            if Path(path) == self.ws.path(target):
                real(self.ws.path(source), manual.encode())
            return result
        with mock.patch.object(store, "atomic_write", side_effect=change_source), self.assertRaises(StoreError) as error:
            self.ws.apply(proposal["proposal_id"], True)
        self.assertEqual(error.exception.code, "conflict")
        self.assertFalse(self.ws.path(target).exists())
        self.assertEqual(self.ws.path(source).read_text(), manual)

    def test_context_supplies_recursive_baseline_for_action_update(self):
        original_file = Path(self.temp.name) / "fictional-project.txt"
        original_file.write_text("Wholly fictional supplied project evidence.")
        original = self.ws.import_source(original_file, "project")["source_path"]
        project, learning, action = "past/projects/one.md", "past/learning/one.md", "present/actions/one.md"
        self.save({project: self.content("project", "project", sources=[original]),
                   learning: self.content("learning", "learning", sources=[original]),
                   action: self.content("action", "action", status="todo", sources=[project, learning])}, [original])
        unrelated = "past/work/unrelated.md"
        # An unrelated damaged record must not be read or indexed by context.
        atomic_write(self.ws.path(unrelated), b"invalid and intentionally unrelated")
        real_bytes = self.ws._bytes
        with mock.patch.object(self.ws, "_bytes", wraps=real_bytes) as reads, mock.patch.object(self.ws, "index", side_effect=AssertionError("no full index")):
            context = self.ws.context([action, action])
        self.assertEqual(context["requested_paths"], [action])
        self.assertEqual(context["source_paths"], [project, learning, original])
        self.assertEqual(set(context["draft_base"]["files"]), {action, project, learning, original})
        self.assertNotIn(unrelated, [call.args[0] for call in reads.call_args_list])
        imported = next(d for d in context["documents"] if d["path"] == original)
        self.assertNotIn("body", imported)
        self.assertEqual(imported["metadata"]["type"], "source")
        self.assertEqual(set(self.ws.read([action])["draft_base"]["files"]), {action})
        self.ws.path(unrelated).unlink()
        draft = {"title": "具体行动更新", "base": context["draft_base"], "writes": [{"path": action,
                 "content": self.content("action", "action", status="doing", sources=[project, learning])}]}
        proposal = self.ws.propose(draft)
        self.assertEqual(self.ws.apply(proposal["proposal_id"], True)["status"], "applied")

    def test_context_new_target_has_null_base_and_requested_sources_not_duplicated(self):
        work, new = "past/work/one.md", "past/profile.md"
        self.save({work: self.content("work", "work")})
        result = self.ws.context([new, work])
        self.assertEqual(result["requested_paths"], [new, work])
        self.assertEqual(result["source_paths"], [])
        self.assertIsNone(result["draft_base"]["files"][new])
        self.assertEqual([d["path"] for d in result["documents"]], [work])

    def test_context_follows_log_evidence_and_photo_asset(self):
        supplied = Path(self.temp.name) / "fictional-original.txt"
        supplied.write_text("A wholly fictional test original.")
        evidence = self.ws.import_source(supplied, "evidence")["source_path"]
        photo = self.ws.import_source(supplied, "photo")["source_path"]
        log, note = "present/learning/log.md", "past/photos/note.md"
        self.save({log: self.content("log", "learning-log", recorded_on="2026-10-23", evidence_paths=[evidence]),
                   note: self.content("photo-note", "photo-note", asset_path=photo)}, [evidence, photo])
        result = self.ws.context([log, note])
        self.assertEqual(set(result["source_paths"]), {evidence, photo})
        self.assertEqual(len(result["documents"]), 4)

    def test_context_missing_declared_source_is_not_a_new_file(self):
        target, missing = "past/work/one.md", "past/work/missing.md"
        atomic_write(self.ws.path(target), self.content("one", "work", sources=[missing]).encode())
        for requested in ([target], [target, missing]):
            with self.subTest(requested=requested), self.assertRaises(StoreError) as error:
                self.ws.context(requested)
            self.assertEqual(error.exception.code, "missing_source")
            self.assertEqual(error.exception.details, [missing])

    def test_context_source_cycle_is_explicit_and_bounded(self):
        first, second = "past/work/one.md", "past/work/two.md"
        atomic_write(self.ws.path(first), self.content("one", "work", sources=[second]).encode())
        atomic_write(self.ws.path(second), self.content("two", "work", sources=[first]).encode())
        with self.assertRaises(StoreError) as error:
            self.ws.context([first])
        self.assertEqual(error.exception.code, "source_cycle")

    def test_context_rechecks_hashes_before_return(self):
        work, profile = "past/work/one.md", "past/profile.md"
        self.save({work: self.content("one", "work"), profile: self.content("profile", "portrait", sources=[work])})
        real_verify = self.ws._verify_base
        def concurrent_change(base):
            atomic_write(self.ws.path(work), self.content("one", "work", title="external change during context").encode())
            return real_verify(base)
        with mock.patch.object(self.ws, "_verify_base", side_effect=concurrent_change), self.assertRaises(StoreError) as error:
            self.ws.context([profile])
        self.assertEqual(error.exception.code, "conflict")

    def test_context_cli_returns_same_shape_without_default_workspace(self):
        path = "past/work/one.md"
        self.save({path: self.content("one", "work")})
        completed = subprocess.run([sys.executable, str(Path(store.__file__)), "--workspace", str(self.root), "context",
                                    "--path", path, "--path", "present/actions/new.md"], capture_output=True, text=True, check=True)
        result = json.loads(completed.stdout)
        self.assertEqual(result["requested_paths"], [path, "present/actions/new.md"])
        self.assertIsNone(result["draft_base"]["files"]["present/actions/new.md"])
        self.assertEqual(result["documents"][0]["path"], path)


    def test_complete_source_graph_rejects_evidence_only_and_mixed_cycles(self):
        a, b = "present/work/a.md", "present/work/b.md"
        for first_field in ("evidence_paths", "sources"):
            with self.subTest(first_field=first_field):
                writes = {a: self.content("log-a", "work-log", recorded_on="2026-10-27", **{first_field: [b]}),
                          b: self.content("log-b", "work-log", recorded_on="2026-10-27", evidence_paths=[a])}
                with self.assertRaises(StoreError) as caught:
                    self.ws.propose(self.draft(writes))
                self.assertEqual(caught.exception.code, "source_cycle")
                self.assertFalse(self.ws.path(a).exists())
        for path, content in writes.items():
            atomic_write(self.ws.path(path), content.encode())
        result = self.ws.validate()
        self.assertFalse(result["ok"])
        self.assertEqual(result["errors"][0]["code"], "source_cycle")
        with self.assertRaises(StoreError) as caught:
            self.ws.context([a])
        self.assertEqual(caught.exception.code, "source_cycle")

    def test_graph_handles_long_lineage_without_recursion_limit(self):
        graph = {str(n): [str(n + 1)] for n in range(2000)}
        self.ws._acyclic(graph, "source_cycle")
        graph["2000"] = ["0"]
        with self.assertRaises(StoreError) as caught:
            self.ws._acyclic(graph, "source_cycle")
        self.assertEqual(caught.exception.code, "source_cycle")

    def test_duplicate_role_identity_rejected_with_both_paths(self):
        one, two = "future/roles/one/goal.md", "future/roles/two/goal.md"
        self.save({one: self.content("one", "goal", role_id="product")})
        with self.assertRaises(StoreError) as caught:
            self.save({two: self.content("two", "goal", role_id="product")})
        self.assertEqual(caught.exception.code, "duplicate_role")
        self.assertEqual(set(caught.exception.details["paths"]), {one, two})
        atomic_write(self.ws.path(two), self.content("two", "goal", role_id="product").encode())
        result = self.ws.validate()
        self.assertFalse(result["ok"])
        self.assertEqual(result["errors"][0]["code"], "duplicate_role")

    def test_independent_note_and_stage_summary_do_not_create_actions(self):
        note, summary = "present/notes/an-idea.md", "present/stages/first-review.md"
        self.save({note: self.content("idea", "note", recorded_on="2026-10-27"),
                   summary: self.content("first-review", "stage-summary", recorded_on="2026-10-27", transition="review")})
        self.assertTrue(self.ws.validate()["ok"])
        self.assertEqual(self.ws.index(types="action")["documents"], [])
        from md_resume import FACT_TYPES
        self.assertFalse({"note", "stage-summary"} & FACT_TYPES)
        self.assertEqual(self.ws.context([note])["source_paths"], [])

    def test_stage_summary_has_valid_transitions_and_typed_item_links(self):
        item, summary = "present/items/first.md", "present/stages/review.md"
        self.save({item: self.content("first", "item", status="done"),
                   summary: self.content("review", "stage-summary", recorded_on="2026-10-27", transition="joining", item_ids=["first"])})
        for changes, code in (({"transition": "change-everything"}, "metadata"), ({"item_ids": ["missing"]}, "missing_reference"), ({"recorded_on": None}, "metadata")):
            metadata, body = parse_document(self.ws.path(summary).read_text())
            metadata.update(changes)
            with self.subTest(changes=changes), self.assertRaises(StoreError) as caught:
                self.save({summary: dump_document(metadata, body)})
            self.assertEqual(caught.exception.code, code)
        with self.assertRaises(StoreError) as caught:
            self.save({"present/work/wrong.md": self.content("wrong", "note", recorded_on="2026-10-27")})
        self.assertEqual(caught.exception.code, "typed_path")

    def test_notes_and_stage_sources_need_actual_revisions_then_warn_on_change(self):
        source, summary = "past/work/source.md", "present/stages/review.md"
        self.save({source: self.content("source", "work")})
        for revisions in ({}, {source: "sha256:" + "0" * 64}):
            with self.subTest(revisions=revisions), self.assertRaises(StoreError):
                self.save({summary: self.content("review", "stage-summary", recorded_on="2026-10-27", sources=[source], source_revisions=revisions)}, [source])
        revision = self.ws.read([source])["draft_base"]["files"][source]
        self.save({summary: self.content("review", "stage-summary", recorded_on="2026-10-27", sources=[source], source_revisions={source: revision})}, [source])
        self.save({source: self.content("source", "work", title="Updated fictional source")})
        result = self.ws.validate()
        self.assertTrue(result["ok"])
        self.assertTrue(any(w["code"] == "stale_sources" and w["path"] == summary for w in result["warnings"]))
        metadata, body = parse_document(self.ws.path(summary).read_text())
        self.save({summary: dump_document(metadata, body + "\nA later reflection, preserving the historical citation.")}, [source])

    def test_stage_reflection_cannot_be_direct_supported_capability_evidence(self):
        goal = self.goal()
        note = "present/notes/idea.md"
        self.save({note: self.content("idea", "note", recorded_on="2026-10-27")})
        assessment = "future/roles/产品目标/assessment.md"
        with self.assertRaises(StoreError) as caught:
            self.save({assessment: self.content("assessment", "assessment", role_id="product", evaluated_on="2026-10-27", sources=[note],
                                                criteria=[{"requirement": "Build systems", "status": "supported", "evidence": [note], "note": "Reflection alone is insufficient"}])}, [note, goal])
        self.assertEqual(caught.exception.code, "unconfirmed_evidence")

    def resume_binding_fixture(self, company_id=None):
        from md_resume import ResumeWorkspace
        fixture = self.interview_fixture()
        personal = "past/personal.md"
        self.save({personal: self.content("person", "personal")})
        content = {"person": {"name": "Fictional Person", "headline": "Product", "contacts": ["demo@example.invalid"]},
                   "summary": {"text": "A fictional project", "source_paths": [fixture["work"]]},
                   "sections": [{"title": "Experience", "items": [{"heading": "Fictional project", "body": "A local prototype", "source_paths": [fixture["work"]]}]}],
                   "source_paths": [personal, fixture["work"]]}
        resume = ResumeWorkspace(self.root)
        version = resume.build(content, "product", company_id, "pm" if company_id else None)
        reference = resume.artifact_ref(version["relative_path"], "resume.html")
        return fixture, reference

    def append_application_event(self, path, reference):
        metadata, body = parse_document(self.ws.path(path).read_text())
        metadata["history"].append({"date": "2026-10-27", "stage": "applied", "note": "Fictional submission", "resume_ref": reference})
        metadata.update(stage="applied", updated_on="2026-10-27")
        return self.save({path: dump_document(metadata, body)})

    def test_application_binds_role_common_or_exact_company_version(self):
        fixture, reference = self.resume_binding_fixture()
        self.append_application_event(fixture["application"], reference)
        saved = self.ws.read([fixture["application"]])["documents"][0]["metadata"]
        self.assertEqual(saved["history"][-1]["resume_ref"], reference)
        self.assertTrue(self.ws.validate()["ok"])

    def test_application_rejects_other_company_version_and_changed_artifact(self):
        fixture, reference = self.resume_binding_fixture("second")
        with self.assertRaises(StoreError) as caught:
            self.append_application_event(fixture["application"], reference)
        self.assertEqual(caught.exception.code, "resume_ref_scope")
        # Even a syntactically valid claimed hash cannot bind a different file.
        reference["version"] = reference["version"].replace("/companies/虚构乙/产品岗/", "/common/")
        from md_resume import ResumeWorkspace
        # Build a real common version from the existing frozen input.
        original = next(self.ws.path("future/roles/产品目标/companies/虚构乙/产品岗/resumes").glob("v-*/content.json"))
        version = ResumeWorkspace(self.root).build(json.loads(original.read_text()), "product")
        bad = ResumeWorkspace(self.root).artifact_ref(version["relative_path"], "resume.html")
        bad["sha256"] = "sha256:" + "0" * 64
        with self.assertRaises(StoreError) as caught:
            self.append_application_event(fixture["application"], bad)
        self.assertEqual(caught.exception.code, "resume_ref_changed")

    def test_missing_historical_resume_warns_without_blocking_unrelated_update(self):
        fixture, reference = self.resume_binding_fixture("first")
        self.append_application_event(fixture["application"], reference)
        self.ws.path(reference["version"] + "/resume.html").unlink()
        self.save({"present/notes/new.md": self.content("new-note", "note", recorded_on="2026-10-27")})
        metadata, body = parse_document(self.ws.path(fixture["application"]).read_text())
        metadata["next_action"] = "Follow up later"
        self.save({fixture["application"]: dump_document(metadata, body)})
        result = self.ws.validate()
        self.assertTrue(result["ok"])
        self.assertTrue(any(w["code"] == "resume_reference_unavailable" for w in result["warnings"]))
        self.assertEqual(self.ws.read([fixture["application"]])["documents"][0]["metadata"]["history"][-1]["resume_ref"], reference)

    def test_history_binding_cannot_be_rewritten_and_unknown_is_allowed(self):
        fixture, reference = self.resume_binding_fixture()
        self.append_application_event(fixture["application"], None)
        metadata, body = parse_document(self.ws.path(fixture["application"]).read_text())
        metadata["history"][-1]["resume_ref"] = reference
        with self.assertRaises(StoreError) as caught:
            self.save({fixture["application"]: dump_document(metadata, body)})
        self.assertEqual(caught.exception.code, "history")
        self.append_application_event(fixture["application"], reference)

    def test_resume_reference_syntax_rejects_escape_wrong_artifact_and_hash(self):
        valid = {"version": "future/roles/product/common/resumes/v-" + "a" * 32, "artifact": "resume.html", "sha256": "sha256:" + "a" * 64}
        cases = [{**valid, "version": "../" + valid["version"]}, {**valid, "artifact": []}, {**valid, "artifact": "content.json"},
                 {**valid, "sha256": "a" * 64}, {**valid, "extra": True}, {**valid, "version": valid["version"] + "/resume.html"}]
        for reference in cases:
            with self.subTest(reference=reference), self.assertRaises(StoreError) as caught:
                self.ws._resume_ref_syntax(reference)
            self.assertEqual(caught.exception.code, "resume_ref")


if __name__ == "__main__":
    unittest.main()
