#!/usr/bin/env python3
"""Fictional fixtures only. Run: python3 -m unittest discover -s scripts -p test_md_views.py"""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from md_workspace import Workspace, StoreError, dump_document, digest
from md_views import ASSET, ViewError, _event_resume, build_snapshot, render


class ViewsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="luji-md-view-test-")
        self.root = Path(self.temp.name).resolve() / "fictional"
        self.ws = Workspace(self.root)
        self.ws.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, *arguments):
        # Run the actual public entry point in a new process. Passing argv text
        # catches accidental duck typing against str.index that object-only API
        # tests cannot detect. Every test uses its explicit fictional workspace.
        return subprocess.run(
            [sys.executable, str(Path(__file__).with_name("md_views.py")),
             "--workspace", str(self.root), *arguments],
            cwd=self.temp.name, capture_output=True, text=True, timeout=20,
            check=False,
        )

    def rendered_data(self, output):
        html = Path(output).read_text(encoding="utf-8")
        payload = html.split('<script type="application/json" id="workspace-data">', 1)[1].split('</script>', 1)[0]
        return json.loads(payload)

    def doc(self, path, type, id, title, body="完全虚构的测试记录。", **metadata):
        metadata = {"id": id, "type": type, "title": title, **metadata}
        target = self.ws.path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(dump_document(metadata, body), encoding="utf-8")
        return path

    def fixture(self):
        work = self.doc("past/work/虚构经历.md", "work", "work-one", "虚构项目经历", occurred_on="2026-01-01")
        goal = self.doc("future/roles/产品/goal.md", "goal", "product", "虚构产品方向", role_id="product", priority=4)
        jd = self.doc("future/roles/产品/companies/示例公司/机会/jd.md", "jd", "jd-one", "产品岗位",
                      role_id="product", company_id="example", company_name="示例公司（虚构）", opportunity_id="one",
                      collected_on="2026-10-23", requirements=["需求分析", "原型", "访谈", "领域知识"])
        assessment = self.doc("future/roles/产品/assessment.md", "assessment", "assessment-one", "要求与证据",
                              role_id="product", evaluated_on="2026-10-23", sources=[work, jd],
                              source_revisions={p: digest(self.ws.path(p).read_bytes()) for p in [work, jd]},
                              criteria=[{"requirement": req, "status": status, "evidence": [work] if status in {"supported", "partial"} else [], "note": "虚构判断"}
                                        for req, status in zip(["需求分析", "原型", "访谈", "领域知识"], ["supported", "partial", "gap", "unknown"])])
        item = self.doc("present/items/学习.md", "item", "item-one", "虚构原型练习", status="doing", goal_ids=["product"])
        action = self.doc("present/actions/一项行动.md", "action", "action-one", "完成一份原型", item_id="item-one",
                          goal_ids=["product"], scheduled_for="2026-10-23", due_on="2026-10-25", minutes=40, status="done", depends_on=[])
        log = self.doc("present/learning/进展.md", "learning-log", "log-one", "练习结果", recorded_on="2026-10-23",
                       item_id="item-one", action_ids=["action-one"], evidence_status="record")
        plan = self.doc("present/plans/weekly/本周.md", "plan", "plan-week", "本周成果", period="weekly", start_date="2026-10-19",
                        end_date="2026-10-25", action_ids=["action-one"])
        app = self.doc("future/roles/产品/companies/示例公司/机会/application.md", "application", "app-one", "产品机会",
                       role_id="product", company_id="example", company_name="示例公司（虚构）", opportunity_id="one",
                       stage="applied", updated_on="2026-10-23", next_action="等待实际反馈", sources=[jd],
                       history=[{"date": "2026-10-22", "stage": "preparing", "note": "整理材料"},
                                {"date": "2026-10-23", "stage": "applied", "note": "用户记录已投递"}])
        return {"work": work, "goal": goal, "jd": jd, "assessment": assessment, "item": item,
                "action": action, "log": log, "plan": plan, "application": app}

    def test_empty_workspace_contains_no_fake_records(self):
        data = build_snapshot(self.ws, "2026-10-23")
        self.assertEqual(data["documents"], [])
        self.assertEqual(data["roles"], [])
        self.assertEqual(data["notes"], [])
        self.assertEqual(data["stages"], [])
        self.assertEqual(data["application_events"], {})
        result = render(self.ws, date="2026-10-23")
        self.assertEqual(result["status"], "generated_not_opened")

    def test_shared_action_and_separate_match_information(self):
        paths = self.fixture()
        data = build_snapshot(self.ws, "2026-10-23")
        role = data["roles"][0]
        self.assertEqual(role["counts"], {"supported": 1, "partial": 1, "gap": 1, "unknown": 1})
        self.assertEqual((role["known"], role["total"]), (3, 4))
        self.assertEqual(role["fit_sort_value"], 0.5)
        self.assertEqual(role["priority"], 4)
        self.assertFalse(role["needs_review"])
        self.assertEqual(data["plans"][0]["metadata"]["action_ids"], [data["actions"][0]["metadata"]["id"]])
        self.assertNotIn("scheduled_for", data["plans"][0]["metadata"])
        self.assertEqual(data["logs"][0]["metadata"]["evidence_status"], "record")
        self.assertIn("%E8%99%9A", data["source_links"][paths["work"]]["href"])

    def test_source_change_marks_judgment_stale_without_rewriting_it(self):
        paths = self.fixture()
        assessment_before = self.ws.path(paths["assessment"]).read_bytes()
        self.ws.path(paths["work"]).write_text(self.ws.path(paths["work"]).read_text()+"\n新增虚构反馈。", encoding="utf-8")
        data = build_snapshot(self.ws, "2026-10-23")
        self.assertTrue(data["roles"][0]["needs_review"])
        self.assertEqual(data["roles"][0]["assessment"]["freshness"], "stale")
        self.assertEqual(self.ws.path(paths["assessment"]).read_bytes(), assessment_before)

    def test_missing_baseline_is_visible_not_confident_match(self):
        paths = self.fixture()
        self.doc(paths["assessment"], "assessment", "assessment-one", "暂定判断", role_id="product", evaluated_on="2026-10-23",
                 sources=[paths["jd"]], criteria=[{"requirement": "访谈", "status": "unknown", "evidence": [], "note": "尚缺资料"}])
        role = build_snapshot(self.ws, "2026-10-23")["roles"][0]
        self.assertIsNone(role["fit_sort_value"])
        self.assertEqual(role["assessment"]["freshness"], "unverified")
        self.assertEqual((role["known"], role["total"]), (0, 1))

    def test_render_does_not_mutate_canonical_files(self):
        self.fixture()
        before = {str(p.relative_to(self.root)): p.read_bytes() for area in ["past", "present", "future"] for p in (self.root/area).rglob("*") if p.is_file()}
        result = render(self.ws, date="2026-10-23", view="applications", role="product", company="example", opportunity="one")
        self.assertTrue(result["read_only"])
        after = {str(p.relative_to(self.root)): p.read_bytes() for area in ["past", "present", "future"] for p in (self.root/area).rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        html = Path(result["output"]).read_text()
        self.assertIn('"view":"applications"', html)
        self.assertIn('"opportunity":"one"', html)

    def test_corrupt_read_preserves_last_successful_html(self):
        paths = self.fixture()
        output = Path(render(self.ws, date="2026-10-23")["output"])
        previous = output.read_bytes()
        self.ws.path(paths["action"]).write_text("---\nid: [invalid\n---", encoding="utf-8")
        with self.assertRaises((StoreError, ViewError)):
            render(self.ws, date="2026-10-23")
        self.assertEqual(output.read_bytes(), previous)

    def test_missing_referenced_source_preserves_previous_html(self):
        paths = self.fixture()
        output = Path(render(self.ws, date="2026-10-23")["output"])
        previous = output.read_bytes()
        self.ws.path(paths["work"]).unlink()
        with self.assertRaises((StoreError, ViewError)):
            render(self.ws, date="2026-10-23")
        self.assertEqual(output.read_bytes(), previous)

    def test_json_cannot_terminate_data_script_or_inject_html(self):
        payload = '</script><script>window.bad=true</script><img src=x onerror=alert(1)>'
        self.doc("past/work/测试.md", "work", "malicious-data", payload, body=payload)
        output = Path(render(self.ws, date="2026-10-23")["output"])
        html = output.read_text()
        self.assertNotIn(payload, html)
        self.assertIn('\\u003c/script\\u003e', html)
        data_text = html.split('<script type="application/json" id="workspace-data">')[1].split('</script>')[0]
        self.assertEqual(json.loads(data_text)["documents"][0]["body"].strip(), payload)

    def test_invalid_template_preserves_previous_html(self):
        output = Path(render(self.ws, date="2026-10-23")["output"])
        previous = output.read_bytes()
        template = Path(self.temp.name)/"bad.html"
        template.write_text("<main>__LUJI_DATA____LUJI_DATA__</main>")
        with self.assertRaises(ViewError):
            render(self.ws, date="2026-10-23", template=template)
        self.assertEqual(output.read_bytes(), previous)

    def test_editable_template_and_custom_output(self):
        template = Path(self.temp.name)/"custom.html"
        template.write_text('<main id="custom">__LUJI_DATA__</main>', encoding="utf-8")
        output = Path(self.temp.name)/"selected.html"
        result = render(self.ws, output, "2026-10-23", template)
        self.assertIn('id="custom"', output.read_text())
        self.assertEqual(Path(result["output"]), output.resolve())

    def test_initial_week_is_explicit_and_does_not_change_action(self):
        paths = self.fixture()
        before = self.ws.path(paths["action"]).read_bytes()
        result = render(self.ws, date="2026-10-23", view="plan", period="weekly")
        self.assertIn('"period":"weekly"', Path(result["output"]).read_text())
        self.assertEqual(self.ws.path(paths["action"]).read_bytes(), before)

    def test_cli_workspace_string_opens_weekly_plan_directly(self):
        paths = self.fixture()
        before = self.ws.path(paths["action"]).read_bytes()
        process = self.cli("--date", "2026-10-23", "--view", "plan", "--period", "weekly")
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(result["status"], "generated_not_opened")
        self.assertEqual(result["workspace_id"], self.ws.manifest()["workspace_id"])
        data = self.rendered_data(result["output"])
        self.assertEqual(data["initial_state"]["view"], "plan")
        self.assertEqual(data["initial_state"]["period"], "weekly")
        self.assertEqual(data["as_of"], "2026-10-23")
        self.assertEqual(data["plans"][0]["metadata"]["action_ids"], ["action-one"])
        self.assertEqual(self.ws.path(paths["action"]).read_bytes(), before)

    def test_cli_initial_role_company_opportunity_filter(self):
        self.fixture()
        self.doc("future/roles/另一方向/goal.md", "goal", "another", "另一虚构方向", role_id="another")
        process = self.cli("--date", "2026-10-23", "--view", "applications",
                           "--role", "product", "--company", "example", "--opportunity", "one")
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        data = self.rendered_data(json.loads(process.stdout)["output"])
        self.assertEqual(data["initial_state"], {"view": "applications", "period": "daily",
                                                "role": "product", "company": "example", "opportunity": "one"})
        selected = [d for d in data["applications"]
                    if all(d["metadata"][key] == value for key, value in
                           {"role_id": "product", "company_id": "example", "opportunity_id": "one"}.items())]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["metadata"]["history"][-1]["stage"], "applied")

    def test_cli_read_failure_reports_error_and_preserves_last_snapshot(self):
        paths = self.fixture()
        successful = self.cli("--date", "2026-10-23", "--view", "plan", "--period", "weekly")
        self.assertEqual(successful.returncode, 0, successful.stdout + successful.stderr)
        output = Path(json.loads(successful.stdout)["output"])
        before = output.read_bytes()
        self.ws.path(paths["action"]).write_text("---\nid: [broken\n---", encoding="utf-8")
        failed = self.cli("--date", "2026-10-23", "--view", "plan", "--period", "weekly")
        self.assertEqual(failed.returncode, 1, failed.stdout + failed.stderr)
        result = json.loads(failed.stdout)
        self.assertEqual(result["status"], "error")
        self.assertTrue(result["previous_snapshot_preserved"])
        self.assertEqual(output.read_bytes(), before)

    def test_snapshot_api_accepts_workspace_path_string(self):
        self.fixture()
        data = build_snapshot(str(self.root), "2026-10-23")
        self.assertEqual(data["workspace_id"], self.ws.manifest()["workspace_id"])
        self.assertEqual(len(data["actions"]), 1)

    def test_resume_links_list_common_and_opportunity_versions_without_approval(self):
        from md_resume import ResumeWorkspace
        paths = self.fixture()
        personal = self.doc("past/个人.md", "personal", "personal-one", "虚构身份", body="姓名：虚构周同学")
        content = {"person": {"name": "虚构周同学", "headline": "", "contacts": [], "source_paths": [personal]},
                   "summary": {"text": "虚构项目记录", "source_paths": [paths["work"]]},
                   "sections": [], "source_paths": [personal, paths["work"]]}
        resumes = ResumeWorkspace(self.ws)
        resumes.build(content, "product", template="profile-split")
        resumes.build(content, "product", company_id="example", opportunity_id="one", template="profile-split")
        data = build_snapshot(self.ws, "2026-10-23")
        self.assertEqual(len(data["resumes"]), 2)
        self.assertEqual({r["scope"]["company_id"] for r in data["resumes"]}, {None, "example"})
        self.assertTrue(all(r["html_href"].startswith("file://") for r in data["resumes"]))
        self.assertTrue(all(r["inspection_status"] == "not_inspected" for r in data["resumes"]))
        self.assertNotIn("approval_token", json.dumps(data["resumes"]))
        self.ws.path(paths["work"]).write_text(self.ws.path(paths["work"]).read_text()+"\n虚构更新。")
        self.assertEqual(len(build_snapshot(self.ws, "2026-10-23")["resumes"]), 2)

    def test_output_cannot_replace_source_or_manifest(self):
        self.fixture()
        for path in [self.root/"manifest.json", self.root/"past"/"work"/"bad.html"]:
            with self.assertRaises(ViewError):
                render(self.ws, path, "2026-10-23")
        self.assertFalse((self.root/"past"/"work"/"bad.html").exists())

    def test_reject_symlink_output(self):
        target = Path(self.temp.name)/"unchanged.html"
        target.write_text("keep")
        link = self.ws.path("views/linked.html")
        link.parent.mkdir(exist_ok=True)
        link.symlink_to(target)
        with self.assertRaises(ViewError):
            render(self.ws, link, "2026-10-23")
        self.assertEqual(target.read_text(), "keep")

    def test_unused_original_is_not_read(self):
        self.fixture()
        untouched = self.ws.path("past/originals/reference/unused.txt")
        untouched.parent.mkdir(parents=True, exist_ok=True)
        untouched.write_text("不应读取的虚构原件")
        original_read, calls = self.ws.read, []
        def read(paths):
            calls.extend(paths)
            return original_read(paths)
        self.ws.read = read
        build_snapshot(self.ws, "2026-10-23")
        self.assertNotIn("past/originals/reference/unused.txt", calls)

    def test_invalid_date_rejected_before_write(self):
        with self.assertRaises(ViewError):
            render(self.ws, date="2026-02-30")
        self.assertFalse(self.ws.path("views/overview.html").exists())

    def interview_fixture(self):
        paths = self.fixture()
        story = self.doc("future/roles/产品/common/interviews/stories/经历故事.md", "interview-story", "story-one", "可复用经历故事",
                         role_id="product", updated_on="2026-10-23", sources=[paths["work"]],
                         source_revisions={paths["work"]: digest(self.ws.path(paths["work"]).read_bytes())})
        prep = self.doc("future/roles/产品/companies/示例公司/机会/interviews/round-1/prep-v1.md", "interview-prep", "prep-one", "一面准备",
                        role_id="product", company_id="example", opportunity_id="one", round_id="round-1",
                        prepared_on="2026-10-23", interview_on="2026-10-26", sources=[story, paths["jd"]],
                        source_revisions={p: digest(self.ws.path(p).read_bytes()) for p in [story, paths["jd"]]})
        practice = self.doc("future/roles/产品/companies/示例公司/机会/interviews/round-1/practice-v1.md", "interview-practice", "practice-one", "模拟一面记录",
                            body="仅为虚构练习，不是公司评价或已确认能力。", role_id="product", company_id="example", opportunity_id="one", round_id="round-1",
                            practiced_on="2026-10-23", sources=[prep], source_revisions={prep: digest(self.ws.path(prep).read_bytes())})
        return {**paths, "story": story, "prep": prep, "practice": practice}

    def test_interview_snapshot_includes_common_and_round_material_without_career_writes(self):
        paths = self.interview_fixture()
        before = {p.relative_to(self.root).as_posix(): p.read_bytes()
                  for area in ("past", "present", "future") for p in (self.root/area).rglob("*") if p.is_file()}
        result = render(self.ws, date="2026-10-23", view="applications", role="product", company="example", opportunity="one")
        data = self.rendered_data(result["output"])
        materials = {d["path"]: d for d in data["documents"] if d["metadata"]["type"].startswith("interview-")}
        self.assertEqual(set(materials), {paths["story"], paths["prep"], paths["practice"]})
        self.assertTrue(all(d["freshness"] == "current" for d in materials.values()))
        self.assertEqual(materials[paths["prep"]]["metadata"]["round_id"], "round-1")
        self.assertEqual(data["applications"][0]["metadata"]["stage"], "applied")
        self.assertEqual(len(data["actions"]), 1)
        self.assertEqual(data["logs"][0]["metadata"]["evidence_status"], "record")
        self.assertEqual(before, {p.relative_to(self.root).as_posix(): p.read_bytes()
                                 for area in ("past", "present", "future") for p in (self.root/area).rglob("*") if p.is_file()})

    def test_interview_indirect_evidence_change_marks_story_prep_and_practice_stale(self):
        paths = self.interview_fixture()
        before = {p: self.ws.path(p).read_bytes() for p in (paths["story"], paths["prep"], paths["practice"])}
        self.ws.path(paths["work"]).write_text(self.ws.path(paths["work"]).read_text()+"\n虚构经历已补充。", encoding="utf-8")
        data = build_snapshot(self.ws, "2026-10-23")
        docs = {d["path"]: d for d in data["documents"]}
        for p in before:
            self.assertEqual(docs[p]["freshness"], "stale")
            self.assertIn(paths["work"], docs[p]["changed_sources"])
            self.assertEqual(self.ws.path(p).read_bytes(), before[p])
        self.assertEqual(docs[paths["application"]]["metadata"]["stage"], "applied")

    def test_interview_missing_source_baseline_propagates_unverified_not_supported(self):
        paths = self.interview_fixture()
        story_path = self.ws.path(paths["story"])
        from md_workspace import parse_document
        metadata, body = parse_document(story_path.read_text())
        metadata.pop("source_revisions")
        story_path.write_text(dump_document(metadata, body), encoding="utf-8")
        # Re-freeze the exact story bytes to isolate its unknown evidence basis
        # from a direct byte change in the preparation document.
        prep_path = self.ws.path(paths["prep"])
        metadata, body = parse_document(prep_path.read_text())
        metadata["source_revisions"][paths["story"]] = digest(story_path.read_bytes())
        prep_path.write_text(dump_document(metadata, body), encoding="utf-8")
        docs = {d["path"]: d for d in build_snapshot(self.ws, "2026-10-23")["documents"]}
        self.assertEqual(docs[paths["story"]]["freshness"], "unverified")
        self.assertEqual(docs[paths["prep"]]["freshness"], "unverified")
        self.assertIn(paths["work"], docs[paths["prep"]]["unverified_sources"])

    def test_manually_moved_interview_material_rejects_wrong_scope_before_body_read(self):
        paths = self.interview_fixture()
        output = Path(render(self.ws, date="2026-10-23")["output"])
        previous = output.read_bytes()
        wrong_path = "future/roles/产品/companies/另一公司/其他机会/interviews/round-1/prep-v1.md"
        destination = self.ws.path(wrong_path)
        destination.parent.mkdir(parents=True)
        self.ws.path(paths["prep"]).rename(destination)
        original_read, reads = self.ws.read, []
        def read(selected):
            reads.extend(selected)
            return original_read(selected)
        self.ws.read = read
        with self.assertRaises(StoreError) as caught:
            render(self.ws, date="2026-10-23", view="applications", role="product", company="example", opportunity="one")
        self.assertEqual(caught.exception.code, "invalid_scope")
        self.assertNotIn(wrong_path, reads)
        self.assertEqual(output.read_bytes(), previous)

    def test_growth_snapshot_preserves_finished_items_notes_and_source_bound_stage(self):
        paths = self.fixture()
        self.doc("present/items/完成事项.md", "item", "item-done", "虚构已完成事项", status="done")
        note = self.doc("present/notes/还未决定.md", "note", "note-one", "一个独立想法",
                        recorded_on="2026-10-25", body="仅记下来，暂不设目标。")
        stage = self.doc("present/stages/阶段回看.md", "stage-summary", "stage-one", "阶段回看",
                         recorded_on="2026-10-27", transition="direction-change", item_ids=["item-done"],
                         sources=[paths["log"]], source_revisions={paths["log"]: digest(self.ws.path(paths["log"]).read_bytes())})
        before = {p: self.ws.path(p).read_bytes() for p in (note, stage, paths["item"], paths["log"])}
        data = build_snapshot(self.ws, "2026-10-27")
        self.assertEqual({d["metadata"]["status"] for d in data["items"]}, {"done", "doing"})
        self.assertEqual(data["notes"][0]["path"], note)
        self.assertNotIn("goal_ids", data["notes"][0]["metadata"])
        self.assertEqual(data["stages"][0]["freshness"], "current")
        self.assertEqual(data["actions"][0]["metadata"]["status"], "done")
        self.ws.path(paths["log"]).write_text(self.ws.path(paths["log"]).read_text()+"\n虚构补充。")
        revised = build_snapshot(self.ws, "2026-10-27")
        self.assertEqual(revised["stages"][0]["freshness"], "stale")
        for path in (note, stage, paths["item"]):
            self.assertEqual(self.ws.path(path).read_bytes(), before[path])

    def test_application_snapshot_binds_exact_used_artifact_not_latest(self):
        from md_resume import ResumeWorkspace
        from md_workspace import parse_document
        paths = self.fixture()
        personal = self.doc("past/个人.md", "personal", "person-used", "虚构身份", body="虚构周同学")
        content = {"person": {"name": "虚构周同学", "headline": "", "contacts": [], "source_paths": [personal]},
                   "summary": {"text": "虚构经历", "source_paths": [paths["work"]]},
                   "sections": [], "source_paths": [personal, paths["work"]]}
        helper = ResumeWorkspace(self.ws)
        used = helper.build(content, "product", template="profile-split")
        newest = helper.build(content, "product", company_id="example", opportunity_id="one", template="classic-single")
        reference = helper.artifact_ref(used["relative_path"], "resume.html")
        metadata, body = parse_document(self.ws.path(paths["application"]).read_text())
        metadata["history"][1]["resume_ref"] = reference
        self.ws.path(paths["application"]).write_text(dump_document(metadata, body))
        events = build_snapshot(self.ws, "2026-10-27")["application_events"][paths["application"]]
        self.assertEqual(events[0]["resume"], {"status": "not_recorded"})
        self.assertEqual(events[1]["resume"]["status"], "verified")
        self.assertEqual(events[1]["resume"]["version"], used["relative_path"])
        self.assertNotIn(newest["relative_path"], events[1]["resume"]["href"])
        self.assertEqual(events[1]["resume"]["href"], self.ws.path(used["relative_path"]+"/resume.html").as_uri())
        self.ws.path(used["relative_path"]+"/resume.html").unlink()
        missing = build_snapshot(self.ws, "2026-10-27")["application_events"][paths["application"]][1]["resume"]
        self.assertEqual(missing["status"], "unavailable")
        self.assertNotIn("href", missing)

    def test_event_binding_defuses_traversal_wrong_scope_changed_or_unverified_artifacts(self):
        app = {"role_id": "product", "company_id": "one", "opportunity_id": "first"}
        version = "future/roles/产品/common/resumes/v-" + "a"*32
        reference = {"version": version, "artifact": "resume.html", "sha256": "sha256:"+"b"*64}
        helper = SimpleNamespace(artifact_ref=Mock(return_value=reference))
        versions = {version: {"scope": {"role_id": "product", "company_id": None, "opportunity_id": None}}}
        self.assertEqual(_event_resume(self.ws, helper, app, reference, versions)["status"], "verified")
        helper.artifact_ref.reset_mock()
        for malicious in ("../../etc/passwd", "/etc/passwd", "future/roles/x/../common/resumes/v-"+"a"*32,
                          "file:///etc/passwd", "future\\roles\\bad"):
            self.assertEqual(_event_resume(self.ws, helper, app, {**reference, "version": malicious}, versions)["status"], "invalid")
        for value in ([], {}, "javascript:alert(1)"):
            self.assertEqual(_event_resume(self.ws, helper, app, {**reference, "artifact": value}, versions)["status"], "invalid")
        helper.artifact_ref.assert_not_called()
        other = {version: {"scope": {"role_id": "product", "company_id": "other", "opportunity_id": "first"}}}
        self.assertEqual(_event_resume(self.ws, helper, app, reference, other)["status"], "wrong_scope")
        helper.artifact_ref.assert_not_called()
        self.assertEqual(_event_resume(self.ws, helper, app, reference, {})["status"], "unavailable")
        helper.artifact_ref.return_value = {**reference, "sha256": "sha256:"+"c"*64}
        self.assertEqual(_event_resume(self.ws, helper, app, reference, versions)["status"], "changed")
        helper.artifact_ref.side_effect = StoreError("unverified_pdf", "No export receipt")
        unavailable = _event_resume(self.ws, helper, app, {**reference, "artifact": "resume.pdf"}, versions)
        self.assertEqual(unavailable["status"], "unavailable")
        self.assertEqual(unavailable["reason"], "unverified_pdf")
        self.assertNotIn("href", unavailable)


if __name__ == "__main__":
    unittest.main()
