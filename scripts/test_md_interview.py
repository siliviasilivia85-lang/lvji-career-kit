"""Fictional metadata discovery and real CLI checks; no model or network."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from md_workspace import Workspace, StoreError, dump_document
from md_interview import InterviewWorkspace


class InterviewDiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="luji-interview-discovery-")
        self.ws = Workspace(Path(self.temp.name) / "fictional")
        self.ws.initialize()
        self.helper = InterviewWorkspace(self.ws)
        self.goal = self.put("future/roles/产品方向/goal.md", "goal", "product", role_id="product")
        self.work = self.put("past/work/经历.md", "work", "work-one", body="只在显式读取时可见的虚构工作正文")
        self.jd = self.put("future/roles/产品方向/companies/星桥/产品/jd.md", "jd", "jd-star",
                           role_id="product", company_id="star", opportunity_id="product-one",
                           company_name="星桥（虚构）", collected_on="2026-10-23", requirements=["需求分析"])
        self.other_jd = self.put("future/roles/产品方向/companies/远山/产品/jd.md", "jd", "jd-far",
                                 role_id="product", company_id="far", opportunity_id="product-two",
                                 company_name="远山（虚构）", collected_on="2026-10-23", requirements=["产品设计"])

    def tearDown(self):
        self.temp.cleanup()

    def put(self, path, kind, id, body="原创虚构测试，不表示真实经验。", **fields):
        file = self.ws.path(path)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(dump_document({"id": id, "type": kind, "title": id, **fields}, body), encoding="utf-8")
        return path

    def material(self, where, id, kind="interview-prep", **fields):
        date_field = {"interview-story": "updated_on", "interview-prep": "prepared_on", "interview-practice": "practiced_on"}[kind]
        return self.put(where, kind, id, role_id="product", sources=[self.work], **{date_field: "2026-10-23"}, **fields)

    def test_context_is_metadata_only_and_never_writes(self):
        before = {p.relative_to(self.ws.root): p.read_bytes() for p in self.ws.root.rglob("*") if p.is_file()}
        with mock.patch.object(self.ws, "read", side_effect=AssertionError("No body reads")), mock.patch.object(self.ws, "_revision", side_effect=AssertionError("No hashing")):
            result = self.helper.context("product", "star", "product-one", "first")
        self.assertEqual(result["location"], "future/roles/产品方向/companies/星桥/产品/interviews/first")
        self.assertEqual([d["path"] for d in result["target_documents"]], [self.goal, self.jd])
        self.assertEqual(result["evidence_candidates"][0]["path"], self.work)
        self.assertNotIn("只在显式读取时可见", json.dumps(result, ensure_ascii=False))
        self.assertFalse(result["freshness_checked"])
        self.assertEqual(before, {p.relative_to(self.ws.root): p.read_bytes() for p in self.ws.root.rglob("*") if p.is_file()})

    def test_selected_round_and_other_rounds_never_mix_companies(self):
        common = self.material("future/roles/产品方向/common/interviews/stories/story.md", "story", "interview-story")
        first = self.material("future/roles/产品方向/companies/星桥/产品/interviews/first/prep-one.md", "first", company_id="star", opportunity_id="product-one", round_id="first")
        second = self.material("future/roles/产品方向/companies/星桥/产品/interviews/second/prep-one.md", "second", company_id="star", opportunity_id="product-one", round_id="second")
        self.material("future/roles/产品方向/companies/远山/产品/interviews/first/prep-one.md", "other", company_id="far", opportunity_id="product-two", round_id="first")
        result = self.helper.list("product", "star", "product-one", "first")
        self.assertEqual([d["path"] for d in result["materials"]["common"]], [common])
        self.assertEqual([d["path"] for d in result["materials"]["selected"]], [first])
        self.assertEqual([d["path"] for d in result["materials"]["other_rounds"]], [second])
        common_result = self.helper.list("product")
        self.assertEqual(common_result["materials"]["selected"], [])
        self.assertEqual(common_result["materials"]["other_rounds"], [])

    def test_progress_is_not_claimed_as_confirmed_evidence(self):
        unconfirmed = self.put("present/learning/学习记录.md", "learning-log", "progress", recorded_on="2026-10-23", evidence_status="record")
        confirmed = self.put("present/work/作品记录.md", "work-log", "output", recorded_on="2026-10-23", evidence_status="confirmed", evidence_paths=[self.work])
        result = self.helper.context("product")
        self.assertEqual(result["progress_candidates"][0]["path"], unconfirmed)
        self.assertEqual(result["progress_candidates"][0]["usage"], "practice_context_only")
        self.assertIn(confirmed, [d["path"] for d in result["evidence_candidates"]])

    def test_invalid_or_ambiguous_scope_fails_explicitly(self):
        for scope in (("missing",), ("product", "star"), ("product", None, None, "first"), ("product", "star", "../escape"), ("product", "far", "product-one")):
            with self.subTest(scope=scope), self.assertRaises(StoreError):
                self.helper.context(*scope)
        self.put("future/roles/产品方向/companies/分裂/产品/application.md", "application", "split", role_id="product", company_id="star", opportunity_id="product-one", company_name="虚构分裂", stage="preparing", updated_on="2026-10-23", next_action="核实路径", history=[])
        with self.assertRaises(StoreError):
            self.helper.context("product", "star", "product-one")

    def test_feedback_is_scoped_and_does_not_require_round_first(self):
        selected = self.put("future/roles/产品方向/companies/星桥/产品/feedback/一条.md", "feedback", "feedback-one", role_id="product", company_id="star", opportunity_id="product-one", received_on="2026-10-23", round_id="first")
        self.put("future/roles/产品方向/companies/远山/产品/feedback/一条.md", "feedback", "feedback-other", role_id="product", company_id="far", opportunity_id="product-two", received_on="2026-10-23")
        result = self.helper.context("product", "star", "product-one")
        self.assertEqual([d["path"] for d in result["feedback_candidates"]], [selected])
        self.assertTrue(any("Round" in x for x in result["missing"]))

    def test_real_cli_needs_explicit_workspace_and_round_is_optional(self):
        script = str(Path(__file__).with_name("md_interview.py"))
        run = subprocess.run([sys.executable, script, "--workspace", str(self.ws.root), "context", "--role", "product"], text=True, capture_output=True, timeout=20)
        self.assertEqual(run.returncode, 0, run.stderr)
        data = json.loads(run.stdout)
        self.assertEqual(data["scope"]["role_id"], "product")
        self.assertTrue(data["missing"])
        run = subprocess.run([sys.executable, script, "list", "--role", "product"], text=True, capture_output=True, timeout=20)
        self.assertNotEqual(run.returncode, 0)

    def test_moved_material_does_not_appear_under_another_company(self):
        self.material("future/roles/产品方向/companies/远山/产品/interviews/first/prep-moved.md", "moved", company_id="star", opportunity_id="product-one", round_id="first")
        for command in (self.helper.list, self.helper.context):
            with self.subTest(command=command.__name__), self.assertRaises(StoreError) as caught:
                command("product", "star", "product-one", "first")
            self.assertEqual(caught.exception.code, "invalid_scope")

    def test_role_context_can_locate_companies_without_another_index(self):
        result = self.helper.context("product")
        self.assertEqual({d["company_id"] for d in result["opportunity_candidates"]}, {"star", "far"})
        scoped = self.helper.context("product", "star", "product-one")
        self.assertEqual([d["company_id"] for d in scoped["opportunity_candidates"]], ["star"])
        self.assertNotIn("body", scoped["opportunity_candidates"][0]["documents"][0])


if __name__ == "__main__":
    unittest.main()
