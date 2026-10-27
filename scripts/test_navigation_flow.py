"""Three fictional user journeys, using real proposals and separate CLI processes.

Confirmation is an explicit test fixture, not proof of human approval detection.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from md_workspace import Workspace, StoreError, dump_document
from md_navigation import NavigationWorkspace
from md_interview import InterviewWorkspace


class NavigationFlowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="luji-navigation-flow-")
        self.ws = Workspace(Path(self.temp.name) / "fictional")
        self.ws.initialize()
        self.nav = NavigationWorkspace(self.ws)

    def tearDown(self):
        self.temp.cleanup()

    def drop(self, relative, text):
        path = self.ws.path(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return relative

    def proposal(self, path, metadata, body):
        selected = self.ws.context([path, *metadata.get("sources", [])])
        if metadata.get("sources"):
            metadata["source_revisions"] = {p: selected["draft_base"]["files"][p] for p in metadata["sources"]}
        return self.ws.propose({"title": "TEST ONLY：已展示的虚构草稿", "base": selected["draft_base"],
                                "writes": [{"path": path, "content": dump_document(metadata, body)}]})

    def save_fixture(self, path, metadata, body):
        proposal = self.proposal(path, metadata, body)
        self.ws.apply(proposal["proposal_id"], confirmed=True)  # Simulated fixture approval.

    def entry(self, scope, path):
        return next(e for e in self.nav.catalog(scope)["entries"] if e["path"] == path)

    def test_drop_resume_find_select_confirm_link_then_detect_change(self):
        raw = self.drop("past/materials/resume/周同学旧简历.md", "原创虚构：周同学参与需求访谈整理，不能证明业务增长。")
        untouched = self.ws.path(raw).read_bytes()
        result = self.nav.refresh("past")
        self.assertEqual(next(e for e in result["entries"] if e["path"] == raw)["state"], "pending")
        self.assertEqual(self.ws.index("past")["documents"], [])
        fact = "past/work/产品助理.md"
        proposal = self.proposal(fact, {"id": "assistant-work", "type": "work", "title": "虚构产品助理经历", "sources": [raw]}, "参与需求访谈整理；没有已知增长指标。")
        self.assertFalse(self.ws.path(fact).exists())
        with self.assertRaises(StoreError):
            self.nav.link(raw, [fact])
        self.ws.apply(proposal["proposal_id"], confirmed=True)
        self.ws.read([fact])
        self.nav.link(raw, [fact])
        self.assertEqual(self.entry("past", raw)["state"], "processed")
        self.assertEqual(self.ws.path(raw).read_bytes(), untouched)
        fact_bytes = self.ws.path(fact).read_bytes()
        self.ws.path(raw).write_bytes(untouched + "\n补充了新材料。".encode())
        self.nav.refresh("past")
        self.assertEqual(self.entry("past", raw)["state"], "changed")
        self.assertEqual(self.ws.path(fact).read_bytes(), fact_bytes)
        self.assertIn(raw, self.ws.path("navigation/past.md").read_text())

    def test_drop_company_jd_locates_one_opportunity_without_reading_other_company(self):
        goal = "future/roles/AI产品/goal.md"
        self.save_fixture(goal, {"id": "ai-product", "type": "goal", "title": "AI产品探索", "role_id": "ai-product", "decision_status": "exploring"}, "先探索，不自动排计划。")
        scope = "future/roles/AI产品/companies/星桥/产品经理"
        raw = self.drop(scope + "/materials/JD原文.md", "星桥（虚构）：负责需求梳理、原型验证。")
        other = self.drop("future/roles/AI产品/companies/远山/产品经理/materials/另一个JD.md", "不该为星桥的问题读取这份正文。")
        with mock.patch.object(self.ws, "_bytes", side_effect=AssertionError("Discovery must not read bodies")):
            discovered = self.nav.refresh(scope)
        self.assertIn(raw, [e["path"] for e in discovered["entries"]])
        self.assertNotIn(other, [e["path"] for e in discovered["entries"]])
        jd = scope + "/jd.md"
        self.save_fixture(jd, {"id": "jd-star", "type": "jd", "title": "星桥AI产品", "role_id": "ai-product", "company_id": "star", "company_name": "星桥（虚构）", "opportunity_id": "product-one", "collected_on": "2026-10-26", "requirements": ["需求梳理", "原型验证"], "sources": [raw]}, "来自用户直接投放的虚构JD。")
        self.nav.link(raw, [jd])
        metadata = InterviewWorkspace(self.ws).context("ai-product", "star", "product-one", "first")
        self.assertEqual([d["path"] for d in metadata["target_documents"]], [goal, jd])
        self.assertFalse(self.ws.path(scope + "/application.md").exists())
        with mock.patch.object(self.ws, "_bytes", wraps=self.ws._bytes) as read:
            chosen = self.ws.context([jd])
        self.assertNotIn(other, chosen["draft_base"]["files"])
        self.assertNotIn(other, [call.args[0] for call in read.call_args_list])
        self.assertEqual(self.entry(scope, raw)["state"], "processed")

    def test_new_process_resumes_saved_item_from_map_without_other_bodies(self):
        item = "present/items/检索作品.md"
        body = "目标：完成一个检索评估作品。\n已决定：先检查样本选择。\n未确定：是否扩大样本。\n当前停点：为什么选择这十个问题？\n下一步：补充选择依据。\n待采纳草稿：扩大样本暂不排程。"
        self.save_fixture(item, {"id": "retrieval", "type": "item", "title": "检索评估作品", "status": "doing"}, body)
        unrelated = "present/items/其他探索.md"
        self.save_fixture(unrelated, {"id": "other", "type": "item", "title": "另一个事项"}, "UNRELATED BODY SHOULD NOT BE LOADED")
        before = {p.relative_to(self.ws.root).as_posix(): p.read_bytes() for area in ("past", "present", "future") for p in self.ws.path(area).rglob("*.md")}
        self.nav.refresh("present")
        script = str(Path(__file__).with_name("md_navigation.py"))
        process = subprocess.run([sys.executable, script, "--workspace", str(self.ws.root), "catalog", "--scope", "present"], text=True, capture_output=True, timeout=20)
        self.assertEqual(process.returncode, 0, process.stderr)
        catalog = json.loads(process.stdout)
        selected = next(e for e in catalog["entries"] if e.get("metadata", {}).get("id") == "retrieval")
        self.assertEqual(selected["path"], item)
        self.assertNotIn("UNRELATED BODY", process.stdout)
        process = subprocess.run([sys.executable, str(Path(__file__).with_name("md_workspace.py")), "--workspace", str(self.ws.root), "context", "--path", selected["path"]], text=True, capture_output=True, timeout=20)
        self.assertEqual(process.returncode, 0, process.stderr)
        context = json.loads(process.stdout)
        self.assertIn("为什么选择这十个问题", context["documents"][0]["body"])
        self.assertEqual(set(context["draft_base"]["files"]), {item})
        self.assertEqual(before, {p.relative_to(self.ws.root).as_posix(): p.read_bytes() for area in ("past", "present", "future") for p in self.ws.path(area).rglob("*.md")})
        self.assertIn("navigation/present.md", self.ws.path("MAP.md").read_text())
        self.assertIn("navigation/present.md", self.ws.path("AGENT-MAP.md").read_text())
        router = self.ws.path("AGENTS.md")
        self.assertIn("AGENT-MAP.md", router.read_text())
        router.write_text(router.read_text() + "\n用户自行维护的工作区约定。\n", encoding="utf-8")
        custom = router.read_bytes()
        self.nav.refresh("present")
        self.assertEqual(router.read_bytes(), custom)


    def test_new_english_user_drops_material_then_records_independent_note_and_stage(self):
        root = Path(self.temp.name) / "english-workspace"
        command = [sys.executable, str(Path(__file__).with_name("md_workspace.py")), "--workspace", str(root), "init", "--language", "en"]
        result = subprocess.run(command, text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        ws = Workspace(root)
        original = "past/materials/learning/README.md"
        ws.path(original).parent.mkdir(parents=True)
        ws.path(original).write_text("A fictional learning record. No formal fields required.")
        navigation = NavigationWorkspace(ws)
        self.assertIn(original, [e["path"] for e in navigation.refresh("past")["entries"]])
        paths = ["present/notes/new-idea.md", "present/stages/review.md"]
        before = ws.path("manifest.json").read_bytes()
        selected = ws.context([original, *paths])
        revision = selected["draft_base"]["files"][original]
        metadata = {"recorded_on": "2026-10-27", "sources": [original], "source_revisions": {original: revision}}
        writes = [{"path": paths[0], "content": dump_document({"id": "idea", "type": "note", "title": "An independent idea", **metadata}, "Keep this idea without inventing an action.")},
                  {"path": paths[1], "content": dump_document({"id": "review", "type": "stage-summary", "title": "A stage review", "transition": "review", "related_ids": ["idea"], **metadata}, "Review what was learned; future links remain optional.")}]
        proposal = ws.propose({"title": "Fictional reviewed records", "base": selected["draft_base"], "writes": writes})
        ws.apply(proposal["proposal_id"], confirmed=True)
        navigation.refresh("present")
        self.assertIn("An independent idea", ws.path("navigation/present.md").read_text())
        self.assertEqual(ws.index(types="action")["documents"], [])
        result = subprocess.run([sys.executable, str(Path(__file__).with_name("md_navigation.py")), "--workspace", str(root), "setup", "--language", "zh"], text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["career_records_changed"])
        self.assertEqual(ws.path("manifest.json").read_bytes(), before)
        self.assertTrue(ws.path("从这里开始.md").exists())
        self.assertEqual(set(ws.context([paths[1]])["draft_base"]["files"]), {paths[1], original})


if __name__ == "__main__":
    unittest.main()
