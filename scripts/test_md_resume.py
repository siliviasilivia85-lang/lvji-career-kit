"""Fictional, isolated behavior checks for Markdown-derived resume versions."""
from copy import deepcopy
import base64
from html.parser import HTMLParser
import io
import html
import uuid
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from md_workspace import Workspace, StoreError, dump_document, digest
import md_resume
from md_resume import ResumeWorkspace
from resume_layout import TEMPLATES, render_html, read_photo


class HeadingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.headings = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == "h2":
            self.current = []

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag == "h2" and self.current is not None:
            self.headings.append("".join(self.current))
            self.current = None


def fictional_pdf(label="fixture"):
    """A tiny valid xref PDF, with no real user's content or external tooling."""
    raw = b"%PDF-1.4\n"
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 10 10] >>"]
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(raw))
        raw += str(number).encode() + b" 0 obj\n" + body + b"\nendobj\n"
    raw += b"% " + label.encode() + b"\n"
    offset = len(raw)
    raw += b"xref\n0 4\n0000000000 65535 f \n"
    raw += b"".join(f"{entry:010d} 00000 n \n".encode() for entry in offsets)
    raw += b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n" + str(offset).encode() + b"\n%%EOF\n"
    return raw


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="luji-md-resume-test-")
        self.root = Path(self.temporary.name) / "workspace"
        self.store = Workspace(self.root)
        self.store.initialize()
        self.personal = "past/personal.md"
        self.education = "past/education/fictional-university.md"
        self.project = "past/projects/retrieval-demo.md"
        self.goal = "future/roles/ai-product/goal.md"
        self.jd = "future/roles/ai-product/companies/starbridge/apm/jd.md"
        self.write(self.personal, "personal", "person", "虚构周同学", "姓名：周同学（虚构）。邮箱：demo@example.invalid。")
        self.write(self.education, "education", "education-demo", "虚构学校", "2020—2024，示例大学，信息管理本科。")
        self.write(self.project, "project", "retrieval-demo", "检索实验", "完成一个本地检索原型；没有真实业务量化结果。")
        self.write(self.goal, "goal", "ai-product", "AI 产品方向", "想设计能实际解决问题的工具。", role_id="ai-product", priority=3)
        self.write(self.jd, "jd", "starbridge-jd", "星桥实验室 AI 产品", "虚构要求：需求分析、检索评估。", role_id="ai-product", company_id="starbridge", company_name="星桥实验室（虚构）", opportunity_id="apm", collected_on="2026-10-23", requirements=["需求分析", "检索评估"])
        self.resume = ResumeWorkspace(self.root)
        self.content = {"person": {"name": "周同学（虚构）", "headline": "AI 产品方向", "contacts": ["demo@example.invalid"]}, "summary": {"text": "完成本地检索原型。", "source_paths": [self.project]}, "sections": [{"title": "教育经历", "items": [{"heading": "示例大学 2020—2024", "body": "信息管理，本科。", "source_paths": [self.education]}]}, {"title": "项目经历", "items": [{"heading": "本地检索原型", "body": "设计并完成一个检索原型；结果仍待验证。", "source_paths": [self.project]}]}], "source_paths": [self.personal, self.education, self.project]}

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, path, kind, identifier, title, body, **extra):
        destination = self.store.path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(dump_document({"id": identifier, "type": kind, "title": title, **extra}, body), encoding="utf-8")

    def build(self, **kwargs):
        return self.resume.build(self.content, "ai-product", **kwargs)

    def export(self, draft, raw=None):
        with patch("md_resume.find_browser", return_value="/fictional/chrome"), patch(
                "md_resume.compile_chromium", side_effect=lambda executable, source, output, profile: output.write_bytes(raw or fictional_pdf())):
            return self.resume.pdf(draft["relative_path"], draft["approval_token"])

    def assertCode(self, code, call):
        with self.assertRaises(StoreError) as result:
            call()
        self.assertEqual(result.exception.code, code)

    def test_build_common_and_exact_company_versions(self):
        common = self.build()
        company = self.build(company_id="starbridge", opportunity_id="apm")
        self.assertIn("/common/resumes/", common["relative_path"])
        self.assertIn("/companies/starbridge/apm/resumes/", company["relative_path"])
        self.assertNotIn(self.jd, common["source_paths"])
        self.assertIn(self.jd, company["source_paths"])
        self.assertEqual(self.resume.inspect(company["relative_path"])["status"], "reviewable")

    def test_identity_and_claim_sources_required(self):
        bad = deepcopy(self.content)
        bad["source_paths"].remove(self.personal)
        self.assertCode("missing_source", lambda: self.resume.build(bad, "ai-product"))
        bad = deepcopy(self.content)
        bad["sections"][1]["items"][0]["source_paths"] = []
        self.assertCode("missing_source", lambda: self.resume.build(bad, "ai-product"))

    def test_jd_goal_and_portrait_cannot_support_claims(self):
        portrait = "past/profile.md"
        self.write(portrait, "portrait", "portrait", "暂定画像", "AI推断可能擅长规划。", sources=[self.project])
        for source in (self.jd, self.goal, portrait):
            bad = deepcopy(self.content)
            bad["source_paths"].append(source)
            bad["sections"][1]["items"][0]["source_paths"] = [source]
            self.assertCode("invalid_claim_source", lambda: self.resume.build(bad, "ai-product"))

    def test_current_progress_requires_confirmed_real_output(self):
        log = "present/learning/2026-10-23.md"
        evidence = "past/originals/evidence/fictional-result.txt"
        target = self.store.path(evidence)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("虚构评估结果：本地样例可用。")
        self.write(log, "learning-log", "current-output", "检索评估进展", "今天做了检索评估。", recorded_on="2026-10-23", evidence_status="candidate", evidence_paths=[evidence])
        content = deepcopy(self.content)
        content["source_paths"].append(log)
        content["summary"] = {"text": "已完成本地样例评估。", "source_paths": [log]}
        self.assertCode("unconfirmed_evidence", lambda: self.resume.build(content, "ai-product"))
        self.write(log, "learning-log", "current-output", "检索评估进展", "今天做了检索评估。", recorded_on="2026-10-23", evidence_status="confirmed", evidence_paths=[evidence])
        result = self.resume.build(content, "ai-product")
        self.assertIn(evidence, result["source_paths"])
        target.write_text("原始结果已修正。")
        self.assertCode("stale_draft", lambda: self.resume.inspect(result["relative_path"]))

    def test_preexisting_stale_confirmed_evidence_cannot_start_new_resume(self):
        log = "present/work/2026-10-23.md"
        evidence = "past/originals/evidence/output.txt"
        self.store.path(evidence).parent.mkdir(parents=True, exist_ok=True)
        self.store.path(evidence).write_text("旧成果。")
        recorded = digest(self.store.path(evidence).read_bytes())
        self.write(log, "work-log", "work-result", "工作成果", "成果的原始确认陈述。", recorded_on="2026-10-23", evidence_status="confirmed", evidence_paths=[evidence], sources=[evidence], source_revisions={evidence: recorded})
        self.store.path(evidence).write_text("更新后的成果有不同结论。")
        content = deepcopy(self.content)
        content["source_paths"].append(log)
        content["summary"] = {"text": "原始结论。", "source_paths": [log]}
        self.assertCode("stale_evidence", lambda: self.resume.build(content, "ai-product"))

    def test_selected_source_edit_rejects_approval(self):
        draft = self.build()
        self.store.path(self.project).write_text(self.store.path(self.project).read_text() + "\n用户修正。")
        self.assertCode("stale_draft", lambda: self.resume.pdf(draft["relative_path"], draft["approval_token"]))
        self.assertFalse(self.store.path(draft["relative_path"] + "/resume.pdf").exists())

    def test_unrelated_file_edit_does_not_stale_selected_resume(self):
        draft = self.build()
        self.write("past/work/unrelated.md", "work", "unrelated-job", "无关经历", "未引用。")
        self.assertEqual(self.resume.inspect(draft["relative_path"])["status"], "reviewable")

    def test_company_jd_change_does_not_stale_common_resume(self):
        common = self.build()
        company = self.build(company_id="starbridge", opportunity_id="apm")
        self.store.path(self.jd).write_text(self.store.path(self.jd).read_text() + "\n补充公开岗位要求。")
        self.assertEqual(self.resume.inspect(common["relative_path"])["status"], "reviewable")
        self.assertCode("stale_draft", lambda: self.resume.inspect(company["relative_path"]))

    def test_transitive_original_is_frozen_without_becoming_a_claim(self):
        original = "past/originals/resume/source-demo.md"
        self.store.path(original).parent.mkdir(parents=True, exist_ok=True)
        self.store.path(original).write_text("虚构简历原件。")
        self.write(self.project, "project", "retrieval-demo", "检索实验", "本地原型。", sources=[original])
        draft = self.build()
        self.assertIn(original, draft["source_paths"])
        self.store.path(original).write_text("原件被更正。")
        self.assertCode("stale_draft", lambda: self.resume.inspect(draft["relative_path"]))

    def test_html_content_or_metadata_tamper_rejected(self):
        for file in ("resume.html", "content.json", "manifest.json"):
            draft = self.build()
            target = self.store.path(draft["relative_path"] + "/" + file)
            if file == "manifest.json":
                value = json.loads(target.read_text())
                value["template"] = "classic-single"
                target.write_text(json.dumps(value))
            else:
                target.write_bytes(target.read_bytes() + b" ")
            self.assertCode("draft_changed", lambda: self.resume.inspect(draft["relative_path"]))

    def test_cross_workspace_copied_version_rejected(self):
        draft = self.build()
        manifest_path = self.store.path("manifest.json")
        value = json.loads(manifest_path.read_text())
        value["workspace_id"] = str(uuid.uuid4())
        manifest_path.write_text(json.dumps(value))
        self.assertCode("invalid_draft", lambda: self.resume.inspect(draft["relative_path"]))

    def test_scope_requires_complete_exact_company(self):
        self.assertCode("invalid_scope", lambda: self.resume.context("ai-product", "starbridge"))
        self.assertCode("invalid_scope", lambda: self.resume.context("ai-product", "not-real", "apm"))
        self.assertCode("invalid_scope", lambda: self.resume.context("unknown"))

    def test_read_only_context_and_list_never_read_source_bodies(self):
        draft = self.build()
        self.store.path(self.project).unlink()
        with patch.object(self.resume.workspace, "read", side_effect=AssertionError("Body read forbidden")):
            result = self.resume.list("ai-product")
            self.assertEqual(len(result["versions"]), 1)
            self.assertNotIn("approval_token", result["versions"][0])
            self.assertEqual(result["versions"][0]["inspection_status"], "not_inspected")
            self.assertEqual(self.resume.context("ai-product")["status"], "indexed")
        self.assertEqual(draft["relative_path"], result["versions"][0]["relative_path"])

    def test_old_versions_stay_independent_and_scope_filtered(self):
        first = self.build()
        second = self.build(template="classic-single")
        company = self.build(company_id="starbridge", opportunity_id="apm")
        versions = self.resume.list("ai-product")["versions"]
        self.assertEqual({v["relative_path"] for v in versions}, {first["relative_path"], second["relative_path"]})
        self.assertEqual(self.resume.list("ai-product", "starbridge", "apm")["versions"][0]["relative_path"], company["relative_path"])

    def test_missing_engine_is_honest_and_writes_no_pdf(self):
        draft = self.build()
        with patch("md_resume.find_browser", return_value=None):
            result = self.resume.pdf(draft["relative_path"], draft["approval_token"])
        self.assertEqual(result["status"], "engine_missing")
        self.assertFalse(self.store.path(draft["relative_path"] + "/resume.pdf").exists())

    def test_pdf_prints_frozen_html_and_never_overwrites(self):
        draft = self.build()
        approved_html = self.store.path(draft["relative_path"] + "/resume.html").read_bytes()
        def compiler(executable, source, output, profile):
            self.assertEqual(source.read_bytes(), approved_html)
            self.assertNotIn(str(self.root), str(profile))
            output.write_bytes(fictional_pdf())
        with patch("md_resume.find_browser", return_value="/fictional/chrome"), patch("md_resume.compile_chromium", side_effect=compiler):
            result = self.resume.pdf(draft["relative_path"], draft["approval_token"])
            self.assertEqual(result["status"], "exported")
            self.assertCode("output_exists", lambda: self.resume.pdf(draft["relative_path"], draft["approval_token"]))

    def test_renderer_upgrade_does_not_invalidate_frozen_history_or_export(self):
        draft = self.build()
        directory = self.store.path(draft["relative_path"])
        frozen = {p.name: p.read_bytes() for p in directory.iterdir()}
        original = md_resume.render_html
        with patch("md_resume.render_html", side_effect=lambda *args: original(*args) + b"\n"):
            inspection = self.resume.inspect(draft["relative_path"])
            self.assertEqual(inspection["integrity_status"], "verified")
            self.assertEqual(inspection["renderer_status"]["status"], "changed")
            self.assertEqual(inspection["source_status"]["status"], "current")
            self.assertEqual(self.export(draft)["pdf_status"], "verified")
        self.assertTrue(all((directory / name).read_bytes() == raw for name, raw in frozen.items()))

    def test_historical_inspection_and_binding_separate_stale_sources(self):
        draft = self.build(company_id="starbridge", opportunity_id="apm")
        self.export(draft)
        old_binding = self.resume.artifact_ref(draft["relative_path"], "resume.pdf")
        self.store.path(self.project).write_text(self.store.path(self.project).read_text() + "\n更正。")
        self.assertCode("stale_draft", lambda: self.resume.inspect(draft["relative_path"]))
        history = self.resume.inspect(draft["relative_path"], historical=True)
        self.assertEqual(history["status"], "historical")
        self.assertEqual(history["source_status"]["status"], "stale")
        self.assertEqual(history["pdf_status"]["status"], "verified")
        self.assertEqual(self.resume.artifact_ref(draft["relative_path"], "resume.pdf"), old_binding)
        self.store.path(self.jd).unlink()
        self.store.path(self.goal).unlink()
        self.assertEqual(self.resume.inspect(draft["relative_path"], historical=True)["source_status"]["status"], "unavailable")
        self.assertEqual(self.resume.artifact_ref(draft["relative_path"], "resume.pdf"), old_binding)

    def test_pdf_receipt_binds_exact_frozen_inputs_without_changing_approval(self):
        draft = self.build()
        manifest_path = self.store.path(draft["relative_path"] + "/manifest.json")
        before = manifest_path.read_bytes()
        result = self.export(draft)
        receipt = json.loads(self.store.path(result["receipt_relative_path"]).read_text())
        manifest = json.loads(before)
        self.assertEqual(manifest_path.read_bytes(), before)
        self.assertEqual(receipt["frozen_files"], manifest["files"])
        self.assertEqual(receipt["approval_token"], manifest["approval_token"])
        self.assertEqual(receipt["workspace_id"], manifest["workspace_id"])
        self.assertEqual(self.resume.inspect(draft["relative_path"])["pdf_status"]["status"], "verified")
        version = self.resume.list("ai-product")["versions"][0]
        self.assertEqual(version["pdf_status"]["status"], "verified")
        self.assertIsNotNone(version["pdf_path"])
        self.assertEqual(self.resume.artifact_ref(draft["relative_path"], "resume.pdf"), {
            "version": draft["relative_path"], "artifact": "resume.pdf", "sha256": result["sha256"]})

    def test_unregistered_or_fake_pdf_never_looks_like_verified_output(self):
        draft = self.build()
        directory = self.store.path(draft["relative_path"])
        self.assertEqual(self.resume.inspect(draft["relative_path"])["pdf_status"]["status"], "absent")
        (directory / "resume.pdf").write_bytes(fictional_pdf())
        self.assertEqual(self.resume.inspect(draft["relative_path"])["pdf_status"]["status"], "unverified")
        self.assertCode("unverified_pdf", lambda: self.resume.artifact_ref(draft["relative_path"], "resume.pdf"))
        version = self.resume.list("ai-product")["versions"][0]
        self.assertIsNone(version["pdf_path"])
        self.assertEqual(version["pdf_file_path"], str(directory / "resume.pdf"))
        (directory / "resume.pdf").write_text("ordinary text with a PDF extension")
        self.assertEqual(self.resume.inspect(draft["relative_path"])["pdf_status"]["status"], "tampered")
        self.assertIsNone(self.resume.list("ai-product")["versions"][0]["pdf_path"])

    def test_missing_historical_html_remains_visible_without_blocking_other_versions(self):
        lost = self.build()
        intact = self.build(template="classic-single")
        self.store.path(lost["relative_path"] + "/resume.html").unlink()
        versions = {v["relative_path"]: v for v in self.resume.list("ai-product")["versions"]}
        self.assertEqual(versions[lost["relative_path"]]["inspection_status"], "unavailable")
        self.assertEqual(versions[lost["relative_path"]]["availability_reason"], "historical_html_missing")
        self.assertIsNone(versions[lost["relative_path"]]["html_path"])
        self.assertEqual(versions[intact["relative_path"]]["inspection_status"], "not_inspected")
        self.assertCode("read_failed", lambda: self.resume.artifact_ref(lost["relative_path"], "resume.html"))

    def test_changed_pdf_or_receipt_cannot_keep_verified_status(self):
        for change in ("pdf", "receipt", "missing-pdf", "frozen-html"):
            draft = self.build()
            self.export(draft)
            directory = self.store.path(draft["relative_path"])
            if change == "pdf":
                (directory / "resume.pdf").write_bytes(fictional_pdf("different bytes"))
            elif change == "receipt":
                value = json.loads((directory / md_resume.RECEIPT_NAME).read_text())
                value["exported_at"] = "replaced"
                (directory / md_resume.RECEIPT_NAME).write_text(json.dumps(value))
            elif change == "missing-pdf":
                (directory / "resume.pdf").unlink()
            else:
                (directory / "resume.html").write_text("changed HTML")
            listed = next(v for v in self.resume.list("ai-product")["versions"] if v["relative_path"] == draft["relative_path"])
            self.assertEqual(listed["pdf_status"]["status"], "tampered", change)
            self.assertIsNone(listed["pdf_path"], change)
            with self.assertRaises(StoreError):
                self.resume.artifact_ref(draft["relative_path"], "resume.pdf")

    def test_receipt_from_another_version_cannot_verify_identical_pdf_bytes(self):
        first = self.build()
        second = self.build(template="classic-single")
        self.export(first)
        self.export(second)
        first_receipt = self.store.path(first["relative_path"] + "/" + md_resume.RECEIPT_NAME).read_bytes()
        self.store.path(second["relative_path"] + "/" + md_resume.RECEIPT_NAME).write_bytes(first_receipt)
        self.assertEqual(self.resume.inspect(second["relative_path"])["pdf_status"]["status"], "tampered")
        self.assertCode("unverified_pdf", lambda: self.resume.artifact_ref(second["relative_path"], "resume.pdf"))

    def test_symlink_receipt_is_not_read_and_only_marks_its_version_tampered(self):
        damaged = self.build()
        intact = self.build(template="classic-single")
        self.export(damaged)
        receipt = self.store.path(damaged["relative_path"] + "/" + md_resume.RECEIPT_NAME)
        receipt.unlink()
        outside = Path(self.temporary.name) / "not-to-be-read.json"
        outside.write_text("must not be followed")
        receipt.symlink_to(outside)
        with patch("md_resume.regular_bytes", side_effect=AssertionError("Do not read through unsafe receipts")):
            versions = {v["relative_path"]: v for v in self.resume.list("ai-product")["versions"]}
        self.assertEqual(versions[damaged["relative_path"]]["pdf_status"], {"status": "tampered", "reason": "unsafe_receipt_path"})
        self.assertIsNone(versions[damaged["relative_path"]]["pdf_path"])
        self.assertEqual(versions[intact["relative_path"]]["pdf_status"], {"status": "absent"})

    def test_receipt_failure_preserves_unverified_pdf_and_never_claims_success(self):
        draft = self.build()
        original = md_resume.create_new_file
        def fail_receipt(path, raw):
            if path.name == md_resume.RECEIPT_NAME:
                raise OSError("simulated interrupted receipt publication")
            original(path, raw)
        with patch("md_resume.create_new_file", side_effect=fail_receipt):
            self.assertCode("pdf_receipt_failed", lambda: self.export(draft))
        directory = self.store.path(draft["relative_path"])
        self.assertTrue((directory / "resume.pdf").is_file())
        self.assertFalse((directory / md_resume.RECEIPT_NAME).exists())
        self.assertEqual(self.resume.inspect(draft["relative_path"])["pdf_status"]["status"], "unverified")
        self.assertCode("output_exists", lambda: self.export(draft))
        (directory / ".luji-export-abandoned").write_text("partial staging bytes")
        self.assertEqual(self.resume.inspect(draft["relative_path"])["pdf_status"]["status"], "unverified")

    def test_pdf_structure_rejects_signature_only_and_broken_xref(self):
        for raw in (b"%PDF-1.4\nfictional test\n%%EOF\n", fictional_pdf().replace(b"startxref\n", b"startxref\n999")):
            draft = self.build()
            self.assertCode("pdf_failed", lambda: self.export(draft, raw))
            self.assertFalse(self.store.path(draft["relative_path"] + "/resume.pdf").exists())

    def test_cli_binding_uses_exact_version_and_historical_inspect_is_explicit(self):
        draft = self.build()
        self.store.path(self.education).unlink()
        with patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(md_resume.main(["--workspace", str(self.root), "binding", "--draft", draft["relative_path"], "--artifact", "resume.html"]), 0)
        self.assertEqual(json.loads(output.getvalue())["version"], draft["relative_path"])
        with patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(md_resume.main(["--workspace", str(self.root), "inspect", "--draft", draft["relative_path"], "--historical"]), 0)
        self.assertEqual(json.loads(output.getvalue())["source_status"]["status"], "unavailable")

    def test_source_changed_during_compiler_does_not_publish(self):
        draft = self.build()
        def compiler(executable, source, output, profile):
            output.write_bytes(fictional_pdf())
            self.store.path(self.education).write_text(self.store.path(self.education).read_text() + "\n修正。")
        with patch("md_resume.find_browser", return_value="/fictional/chrome"), patch("md_resume.compile_chromium", side_effect=compiler):
            self.assertCode("stale_draft", lambda: self.resume.pdf(draft["relative_path"], draft["approval_token"]))
        self.assertFalse(self.store.path(draft["relative_path"] + "/resume.pdf").exists())

    def test_invalid_compiler_result_or_wrong_approval_writes_nothing(self):
        draft = self.build()
        self.assertCode("approval_mismatch", lambda: self.resume.pdf(draft["relative_path"], "sha256:" + "0" * 64))
        def compiler(executable, source, output, profile):
            output.write_bytes(b"not pdf")
        with patch("md_resume.find_browser", return_value="/fictional/chrome"), patch("md_resume.compile_chromium", side_effect=compiler):
            self.assertCode("pdf_failed", lambda: self.resume.pdf(draft["relative_path"], draft["approval_token"]))
        self.assertFalse(self.store.path(draft["relative_path"] + "/resume.pdf").exists())

    def test_symlink_or_undeclared_file_rejected(self):
        draft = self.build()
        directory = self.store.path(draft["relative_path"])
        (directory / "unexpected.js").write_text("throw new Error('not allowed')")
        self.assertCode("invalid_draft", lambda: self.resume.inspect(draft["relative_path"]))
        (directory / "unexpected.js").unlink()
        outside = Path(self.temporary.name) / "outside.txt"
        outside.write_text("not a resume")
        (directory / "resume.html").unlink()
        (directory / "resume.html").symlink_to(outside)
        with self.assertRaises(StoreError):
            self.resume.inspect(draft["relative_path"])

    def test_all_layouts_preserve_strings_escape_html_and_hide_sources_when_printed(self):
        content = deepcopy(self.content)
        content["sections"][1]["items"][0]["body"] = '<img src="https://invalid.test/x" onerror="bad()"> & 原文'
        source_revisions = {p: digest(b"fictional") for p in content["source_paths"]}
        for template in TEMPLATES:
            page = render_html(content, template, source_revisions).decode()
            self.assertIn("&lt;img", page)
            self.assertNotIn('<img src="https://', page)
            self.assertIn("原文", page)
            self.assertIn("示例大学 2020—2024", page)
            self.assertIn("@page{size:A4", page)
            self.assertIn("details,.claim-sources{display:none!important}", page)
            self.assertIn("connect-src 'none'", html.unescape(page))
            self.assertNotIn("@import", page)
        page = render_html(self.content, "profile-split", source_revisions).decode()
        self.assertIn('class="resume-body two-column"', page)
        self.assertIn("minmax(0,30fr) minmax(0,70fr)", page)

    def test_optional_photo_rejects_html_and_requires_local_explicit_path(self):
        photo = Path(self.temporary.name).resolve() / "photo.svg"
        photo.write_text('<svg onload="bad()"></svg>')
        self.assertCode("invalid_photo", lambda: read_photo(photo))
        photo.unlink()
        photo.symlink_to(self.store.path(self.personal))
        self.assertCode("unsafe_path", lambda: read_photo(photo))

    def test_priority_layouts_reorder_only_explicit_project_or_work_sections(self):
        content = deepcopy(self.content)
        content["sections"].insert(1, {"title": "工作经历", "items": [
            {"heading": "虚构工作", "body": "示例原文，不增加职责。", "source_paths": [self.project]}]})
        content["sections"].append({"title": "技能与方法", "items": [
            {"heading": "原型方法", "body": "示例技能原文。", "source_paths": [self.project]}]})
        revisions = {path: digest(b"fictional") for path in content["source_paths"]}
        expected = {
            "project-first": ["个人简介", "项目经历", "教育经历", "工作经历", "技能与方法"],
            "experience-first": ["个人简介", "工作经历", "教育经历", "项目经历", "技能与方法"],
            "classic-single": ["个人简介", "教育经历", "工作经历", "项目经历", "技能与方法"],
        }
        for template, order in expected.items():
            page = render_html(content, template, revisions).decode()
            parser = HeadingParser()
            parser.feed(page)
            self.assertEqual(parser.headings, order)
            for section in content["sections"]:
                for item in section["items"]:
                    self.assertIn(html.escape(item["heading"]), page)
                    self.assertIn(html.escape(item["body"]), page)
        content["sections"][1]["title"] = "Professional experience"
        page = render_html(content, "experience-first", revisions).decode()
        parser = HeadingParser()
        parser.feed(page)
        self.assertEqual(parser.headings[1:3], ["Professional experience", "教育经历"])

    def test_explicit_photo_is_embedded_and_frozen_in_every_layout(self):
        # A complete one-pixel PNG is a test fixture, not a user/photo asset.
        raw = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6V4QAAAAASUVORK5CYII=")
        photo = Path(self.temporary.name).resolve() / "fictional.png"
        photo.write_bytes(raw)
        for template in TEMPLATES:
            draft = self.build(template=template, photo=photo)
            directory = self.store.path(draft["relative_path"])
            page = (directory / "resume.html").read_text()
            manifest = json.loads((directory / "manifest.json").read_text())
            self.assertIn('<img class="photo"', page)
            self.assertIn("data:image/png;base64," + base64.b64encode(raw).decode(), page)
            self.assertEqual(manifest["files"]["photo.png"], digest(raw))
            self.assertEqual((directory / "photo.png").read_bytes(), raw)
            self.assertEqual(self.resume.inspect(draft["relative_path"])["status"], "reviewable")
            self.assertEqual(json.loads((directory / "content.json").read_text()), self.content)
        (directory / "photo.png").write_bytes(raw + b"changed")
        self.assertCode("draft_changed", lambda: self.resume.inspect(draft["relative_path"]))
        without_photo = self.build()
        page = self.store.path(without_photo["relative_path"] + "/resume.html").read_text()
        self.assertNotIn('<img class="photo"', page)

    def test_cli_templates_work_without_any_workspace(self):
        with patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(md_resume.main(["--workspace", "/definitely/not/read", "templates"]), 0)
        self.assertEqual(len(json.loads(output.getvalue())["templates"]), 6)


if __name__ == "__main__":
    unittest.main()
