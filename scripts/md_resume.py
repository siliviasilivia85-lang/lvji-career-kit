#!/usr/bin/env python3
"""Source-backed Markdown career resumes: context, HTML versions, review and PDF.

Only selected local Markdown and its declared provenance are read. Layouts and
optional Chromium export are separate from the canonical career documents.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hmac
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
import uuid

from md_workspace import Workspace, StoreError, digest, atomic_write, json_bytes, read_json, _sync_dir
from resume_layout import TEMPLATES, render_html, read_photo, find_browser, compile_chromium

SCHEMA = "luji-markdown-resume-0.1"
MAX_CONTENT = 2 * 1024 * 1024
MAX_HTML = 12 * 1024 * 1024
MAX_PDF = 50 * 1024 * 1024
MAX_PHOTO = 5 * 1024 * 1024
VERSION_RE = re.compile(r"v-[0-9a-f]{32}\Z")
HASH_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
FACT_TYPES = {"personal", "education", "work", "project", "award", "learning", "learning-log", "work-log"}
PDF_SCHEMA = "luji-markdown-resume-pdf-0.1"
RECEIPT_NAME = "pdf-receipt.json"
RECEIPT_KEYS = {"schema_version", "workspace_id", "workspace_manifest_hash", "version", "scope", "approval_token", "frozen_files", "pdf_sha256", "pdf_size", "exported_at", "integrity_token"}
MANIFEST_KEYS = {"schema_version", "workspace_id", "workspace_manifest_hash", "scope", "relative_path", "template", "created_at", "source_paths", "source_revisions", "files", "approval_token"}


def error(code, message):
    raise StoreError(code, message)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def regular_bytes(path, limit):
    try:
        if not path.is_file() or path.is_symlink() or path.stat().st_size > limit:
            raise OSError()
        raw = path.read_bytes()
        if len(raw) > limit:
            raise OSError()
        return raw
    except OSError:
        error("read_failed", "Cannot read a regular local file within its size limit: " + path.name)


def strings(value, label, maximum=1000):
    if not isinstance(value, list) or len(value) > maximum or any(not isinstance(v, str) or not v.strip() or len(v) > 2000 for v in value):
        error("invalid_content", label + " must be a list of non-empty strings within its size limit.")
    if len(set(value)) != len(value):
        error("invalid_content", label + " must not contain duplicates.")


def text(value, label, maximum=50000, required=False):
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        error("invalid_content", label + " must be text within its size limit.")


def keys(value, allowed, required):
    if not isinstance(value, dict) or set(value) - set(allowed) or set(required) - set(value):
        error("invalid_content", "Unexpected or missing fields in the resume input or metadata.")


def token(manifest):
    return digest(json_bytes({k: v for k, v in manifest.items() if k != "approval_token"}))


def pdf_structure_valid(raw):
    """Check the local browser PDF envelope/xref, without claiming full PDF parsing.

    A receipt additionally binds the exact bytes produced by the compiler. This
    deliberately uses the standard library; it is not a PDF security validator.
    """
    if not re.match(rb"%PDF-(?:1\.[0-7]|2\.0)[\r\n]", raw):
        return False
    end = re.search(rb"startxref\s+(\d+)\s+%%EOF\s*\Z", raw[-4096:])
    if not end:
        return False
    offset = int(end.group(1))
    if offset < 9 or offset >= len(raw):
        return False
    xref = raw[offset:]
    if not (xref.startswith(b"xref") or (re.match(rb"\d+\s+\d+\s+obj\b", xref)
            and re.search(rb"/Type\s*/XRef\b", xref[:4096]))):
        return False
    root = re.search(rb"/Root\s+(\d+)\s+(\d+)\s+R\b", xref)
    if not root:
        return False
    catalog = re.search(rb"(?m)^" + root.group(1) + rb"\s+" + root.group(2) + rb"\s+obj\b(.*?)endobj", raw, re.S)
    return bool(catalog and re.search(rb"/Type\s*/Catalog\b", catalog.group(1))
                and re.search(rb"/Pages\s+\d+\s+\d+\s+R\b", catalog.group(1))
                and re.search(rb"/Type\s*/Pages\b", raw)
                and re.search(rb"/Type\s*/Page\b", raw))


def create_new_file(path, raw):
    """Publish complete bytes without ever replacing an existing version's PDF."""
    fd, temporary = tempfile.mkstemp(prefix=".luji-export-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            error("output_exists", "This version already has an output; it will not be overwritten.")
        _sync_dir(path.parent)
    finally:
        Path(temporary).unlink(missing_ok=True)


class ResumeWorkspace:
    def __init__(self, root):
        self.workspace = root if isinstance(root, Workspace) else Workspace(root)
        self.root = self.workspace.root

    def _scope(self, role_id, company_id=None, opportunity_id=None):
        if not isinstance(role_id, str) or not role_id:
            error("invalid_scope", "Choose one existing goal role_id.")
        if (company_id is None) != (opportunity_id is None):
            error("invalid_scope", "A company-specific version needs both company and opportunity IDs.")
        index = self.workspace.index()
        documents = index["documents"]
        goals = [d for d in documents if d["metadata"]["type"] == "goal" and d["metadata"].get("role_id", d["metadata"]["id"]) == role_id]
        if len(goals) != 1:
            error("invalid_scope", "The selected role must identify exactly one existing goal.md.")
        goal = goals[0]
        base = PurePosixPath(goal["path"]).parent
        if goal["path"] != str(base / "goal.md") or not str(base).startswith("future/roles/"):
            error("invalid_scope", "The goal must be stored as future/roles/<role>/goal.md.")
        source_paths = [goal["path"]]
        if company_id is None:
            location = str(base / "common")
        else:
            matches = [d for d in documents if d["metadata"]["type"] in {"jd", "application"} and d["metadata"].get("role_id") == role_id and d["metadata"].get("company_id") == company_id and d["metadata"].get("opportunity_id") == opportunity_id]
            parents = {str(PurePosixPath(d["path"]).parent) for d in matches}
            if len(parents) != 1:
                error("invalid_scope", "The selected company/opportunity must have one consistent JD/application folder.")
            location = parents.pop()
            # Require exactly company/opportunity depth; never let IDs become paths.
            remainder = PurePosixPath(location).relative_to(base) if PurePosixPath(location).is_relative_to(base) else None
            if remainder is None or len(remainder.parts) != 3 or remainder.parts[0] != "companies":
                error("invalid_scope", "Company files must use <role>/companies/<company>/<opportunity>/.")
            source_paths.extend(d["path"] for d in matches if d["metadata"]["type"] == "jd")
        return {"workspace_id": index["workspace_id"], "scope": {"role_id": role_id, "company_id": company_id, "opportunity_id": opportunity_id}, "location": location, "source_paths": sorted(source_paths), "documents": documents}

    def context(self, role_id, company_id=None, opportunity_id=None, *, source_paths=None):
        """Metadata-only discovery; the Agent selects actual facts before reading them."""
        scope = self._scope(role_id, company_id, opportunity_id)
        candidates = [d for d in scope["documents"] if d["metadata"]["type"] in FACT_TYPES]
        selected = list(source_paths or [])
        strings(selected, "selected source_paths")
        available = {d["path"] for d in candidates}
        if set(selected) - available:
            error("invalid_source", "Select fact documents from the returned local candidate index.")
        return {"status": "indexed", "workspace_id": scope["workspace_id"], "scope": scope["scope"], "location": scope["location"], "scope_source_paths": scope["source_paths"], "selected_source_paths": selected, "candidates": candidates,
                "next_step": "Read only selected fact Markdown plus the goal/JD needed for this role. Verify identity, education, work, projects, and any confirmed current outputs. Missing facts stay missing; plans and JD requirements are not achievements."}

    def _snapshot(self, paths):
        """Freeze the selected documents and their explicitly declared provenance."""
        remaining = set(paths)
        docs, revisions = {}, {}
        identity_raw = regular_bytes(self.workspace.path("manifest.json"), MAX_CONTENT)
        identity = self.workspace.manifest()
        while remaining:
            if len(docs) + len(remaining) > 1000:
                error("too_many_sources", "The selected provenance graph is too large for one resume version.")
            batch = sorted(remaining)
            remaining.clear()
            result = self.workspace.read(batch)
            if result["workspace_id"] != identity["workspace_id"]:
                error("workspace_changed", "Workspace identity changed during source reading.")
            by_path = {d["path"]: d for d in result["documents"]}
            for path in batch:
                if path not in by_path or result["draft_base"]["files"].get(path) is None:
                    error("missing_source", "A selected local source is missing: " + path)
                document = by_path[path]
                docs[path] = document
                revisions[path] = result["draft_base"]["files"][path]
                meta = document.get("metadata", {})
                inherited = list(meta.get("sources", []))
                if meta.get("type") in {"learning-log", "work-log"}:
                    inherited.extend(meta.get("evidence_paths", []))
                for source in inherited:
                    if source not in docs:
                        remaining.add(source)
        # Check an edit during the multi-batch read, rather than mixing revisions.
        check = self.workspace.read(sorted(revisions))
        if check["workspace_id"] != identity["workspace_id"] or check["draft_base"]["files"] != revisions or regular_bytes(self.workspace.path("manifest.json"), MAX_CONTENT) != identity_raw:
            error("source_changed", "Selected files changed while being read; reread and rebuild.")
        return {"workspace_id": identity["workspace_id"], "workspace_manifest_hash": digest(identity_raw), "source_revisions": dict(sorted(revisions.items()))}, docs

    def _validate_content(self, content, documents):
        keys(content, {"person", "summary", "sections", "source_paths"}, {"person", "summary", "sections", "source_paths"})
        person = content["person"]
        keys(person, {"name", "headline", "contacts", "source_paths"}, {"name", "headline", "contacts"})
        text(person["name"], "person.name", 200, True)
        text(person["headline"], "person.headline", 1000)
        strings(person["contacts"], "person.contacts", 30)
        strings(content["source_paths"], "source_paths")
        global_sources = set(content["source_paths"])
        if not global_sources:
            error("missing_source", "A resume needs selected local fact Markdown, including identity details.")

        def check_claim(paths, label):
            strings(paths, label)
            if not paths or set(paths) - global_sources:
                error("missing_source", "Each claim needs a declared source covered by global source_paths.")
            for path in paths:
                document = documents.get(path)
                meta = document.get("metadata", {}) if document else {}
                if meta.get("type") not in FACT_TYPES or "body" not in document:
                    error("invalid_claim_source", "Claims must use actual fact Markdown, not goals, JD, portraits, tasks or imported-file hashes: " + path)
                if meta.get("type") in {"learning-log", "work-log"} and (meta.get("evidence_status") != "confirmed" or not meta.get("evidence_paths")):
                    error("unconfirmed_evidence", "Current progress must have confirmed actual output evidence before becoming a resume claim: " + path)
                for source, expected in meta.get("source_revisions", {}).items():
                    actual = documents.get(source, {}).get("revision")
                    if actual != expected:
                        error("stale_evidence", "A claim's recorded source version changed; recheck the fact before using it: " + path)
        identity_sources = person.get("source_paths")
        if identity_sources is None:
            identity_sources = [p for p in content["source_paths"] if documents.get(p, {}).get("metadata", {}).get("type") == "personal"]
        check_claim(identity_sources, "person.source_paths")
        summary = content["summary"]
        keys(summary, {"text", "source_paths"}, {"text", "source_paths"})
        text(summary["text"], "summary.text", 30000)
        strings(summary["source_paths"], "summary.source_paths")
        if summary["text"].strip():
            check_claim(summary["source_paths"], "summary.source_paths")
        elif summary["source_paths"]:
            check_claim(summary["source_paths"], "summary.source_paths")
        if not isinstance(content["sections"], list) or len(content["sections"]) > 30:
            error("invalid_content", "sections must be a list of at most 30 sections.")
        for section in content["sections"]:
            keys(section, {"title", "items"}, {"title", "items"})
            text(section["title"], "section.title", 1000, True)
            if not isinstance(section["items"], list) or len(section["items"]) > 100:
                error("invalid_content", "Each section must have at most 100 items.")
            for item in section["items"]:
                keys(item, {"heading", "body", "source_paths"}, {"heading", "body", "source_paths"})
                text(item["heading"], "item.heading", 2000, True)
                text(item["body"], "item.body")
                check_claim(item["source_paths"], "item.source_paths")
        # Even a globally declared source cannot be an unreadable/unread source.
        if global_sources - set(documents):
            error("missing_source", "At least one declared source was not read.")

    def build(self, content, role_id, company_id=None, opportunity_id=None, *, template="profile-split", photo=None):
        if template not in TEMPLATES:
            error("invalid_template", "Unknown resume layout.")
        if not isinstance(content, dict):
            error("invalid_content", "Resume content must be a JSON object.")
        paths = content.get("source_paths", [])
        strings(paths, "source_paths")
        scope = self._scope(role_id, company_id, opportunity_id)
        baseline, documents = self._snapshot(sorted(set(paths) | set(scope["source_paths"])))
        self._validate_content(content, documents)
        photo_name, photo_raw = read_photo(photo) if photo is not None else (None, None)
        relative = scope["location"] + "/resumes/v-" + uuid.uuid4().hex
        destination = self.workspace.path(relative)
        content_raw = json_bytes(content)
        html_raw = render_html(content, template, baseline["source_revisions"], photo_name, photo_raw)
        if len(content_raw) > MAX_CONTENT or len(html_raw) > MAX_HTML:
            error("too_large", "Resume content or rendered HTML exceeds the local size limit.")
        files = {"content.json": digest(content_raw), "resume.html": digest(html_raw)}
        if photo_name:
            files[photo_name] = digest(photo_raw)
        manifest = {"schema_version": SCHEMA, **baseline, "scope": scope["scope"], "relative_path": relative,
                    "template": template, "created_at": now(), "source_paths": sorted(baseline["source_revisions"]), "files": files}
        manifest["approval_token"] = token(manifest)
        destination.mkdir(parents=True, exist_ok=False, mode=0o700)
        try:
            atomic_write(self.workspace.path(relative + "/content.json"), content_raw)
            atomic_write(self.workspace.path(relative + "/resume.html"), html_raw)
            if photo_name:
                atomic_write(self.workspace.path(relative + "/" + photo_name), photo_raw)
            atomic_write(self.workspace.path(relative + "/manifest.json"), json_bytes(manifest))
            # Do not announce a coherent new version if its selected inputs changed mid-build.
            self._inspect(relative)
        except Exception:
            shutil.rmtree(destination)
            raise
        return {"status": "draft", "relative_path": relative, "html_path": str(destination / "resume.html"),
                "content_path": str(destination / "content.json"), "approval_token": manifest["approval_token"],
                "source_paths": manifest["source_paths"], "template": template,
                "next_step": "Review this exact HTML and factual sources. Export only after explicit user approval of this version; the token itself is not human consent."}

    def _metadata(self, draft, scope=None):
        directory = self.workspace.path(draft)
        value = read_json(self.workspace.path(draft + "/manifest.json"))
        keys(value, MANIFEST_KEYS, MANIFEST_KEYS)
        if value["schema_version"] != SCHEMA or value["relative_path"] != draft or value["workspace_id"] != self.workspace.manifest()["workspace_id"]:
            error("invalid_draft", "Draft schema, directory or workspace identity differs.")
        keys(value["scope"], {"role_id", "company_id", "opportunity_id"}, {"role_id", "company_id", "opportunity_id"})
        stored_scope = value["scope"]
        if (not isinstance(stored_scope["role_id"], str) or not stored_scope["role_id"]
                or (stored_scope["company_id"] is None) != (stored_scope["opportunity_id"] is None)
                or any(v is not None and (not isinstance(v, str) or not v) for v in stored_scope.values())):
            error("invalid_draft", "Invalid stored resume scope.")
        parts = PurePosixPath(draft).parts
        common = stored_scope["company_id"] is None
        valid_location = (len(parts) == 6 and parts[3:5] == ("common", "resumes")) if common else (len(parts) == 8 and parts[3] == "companies" and parts[6] == "resumes")
        if not valid_location or parts[:2] != ("future", "roles") or not VERSION_RE.fullmatch(parts[-1]):
            error("invalid_draft", "Draft is not stored at a canonical role/company resume path.")
        if scope is not None and (draft != scope["location"] + "/resumes/" + parts[-1] or stored_scope != scope["scope"]):
            error("invalid_draft", "Draft does not belong to the selected role/company/opportunity.")
        if not isinstance(value["template"], str) or not isinstance(value["created_at"], str):
            error("invalid_draft", "Invalid stored layout or timestamp.")
        if not isinstance(value["approval_token"], str) or not HASH_RE.fullmatch(value["approval_token"]) or not hmac.compare_digest(token(value), value["approval_token"]):
            error("draft_changed", "Draft metadata changed; rebuild and review.")
        return directory, value, scope

    def _frozen(self, draft):
        """Verify historical bytes against their own frozen manifest, not today's renderer."""
        directory, value, _ = self._metadata(draft)
        files = value["files"]
        if not isinstance(files, dict) or not {"content.json", "resume.html"} <= set(files) or set(files) - {"content.json", "resume.html", "photo.png", "photo.jpg", "photo.webp"} or len(set(files) - {"content.json", "resume.html"}) > 1:
            error("invalid_draft", "Unexpected declared files in this version.")
        actual = {}
        for name, expected in files.items():
            if not isinstance(expected, str) or not HASH_RE.fullmatch(expected):
                error("invalid_draft", "Invalid stored file digest.")
            raw = regular_bytes(self.workspace.path(draft + "/" + name), MAX_HTML if name == "resume.html" else MAX_CONTENT if name == "content.json" else MAX_PHOTO)
            if not hmac.compare_digest(digest(raw), expected):
                error("draft_changed", "Content, HTML or photo changed; rebuild and review.")
            actual[name] = raw
        allowed = {"manifest.json", *files, "resume.pdf", RECEIPT_NAME}
        for child in directory.iterdir():
            # A killed exclusive publication may leave its unlinked staging file.
            # It is never a resume artifact or evidence and is never read here.
            staging = re.fullmatch(r"\.luji-export-[A-Za-z0-9_-]+", child.name)
            if child.is_symlink() or not child.is_file() or (child.name not in allowed and not staging):
                error("invalid_draft", "Unexpected file or symlink in this version.")
        strings(value["source_paths"], "source_paths")
        if (not isinstance(value["source_revisions"], dict) or set(value["source_paths"]) != set(value["source_revisions"])
                or any(not isinstance(v, str) or not HASH_RE.fullmatch(v) for v in value["source_revisions"].values())):
            error("invalid_draft", "Stored sources do not match their digests.")
        try:
            content = json.loads(actual["content.json"])
        except (ValueError, UnicodeError):
            error("invalid_content", "Stored resume content is not readable JSON.")
        if not isinstance(content, dict):
            error("invalid_content", "Stored resume content must be a JSON object.")
        photo_name = next((name for name in files if name.startswith("photo.")), None)
        if photo_name and read_photo(self.workspace.path(draft + "/" + photo_name))[0] != photo_name:
            error("invalid_photo", "Photo signature no longer matches its extension.")
        return value, content, actual

    def _source_status(self, value, content):
        try:
            scope = self._scope(**value["scope"])
            baseline, documents = self._snapshot(value["source_paths"])
            changed = [key for key, current in baseline.items() if value[key] != current]
            if set(scope["source_paths"]) - set(value["source_paths"]):
                changed.append("scope_source_paths")
            if changed:
                return {"status": "stale", "changed": changed}, None
            self._validate_content(content, documents)
            return {"status": "current"}, documents
        except StoreError as exc:
            return {"status": "unavailable", "code": exc.code, "message": str(exc)}, None

    def _renderer_status(self, value, content, actual):
        if value["template"] not in TEMPLATES:
            return {"status": "unavailable", "reason": "template_not_in_current_renderer"}
        photo_name = next((name for name in value["files"] if name.startswith("photo.")), None)
        try:
            current = render_html(content, value["template"], value["source_revisions"], photo_name, actual.get(photo_name))
            return {"status": "current" if current == actual["resume.html"] else "changed",
                    "meaning": "Current rendering comparison only; frozen HTML integrity is checked independently."}
        except (StoreError, KeyError, TypeError, ValueError):
            return {"status": "unavailable", "reason": "current_renderer_cannot_render_historical_content"}

    def _inspection(self, draft, *, historical=False):
        value, content, actual = self._frozen(draft)
        source_status, _ = self._source_status(value, content)
        if not historical and source_status["status"] != "current":
            error("stale_draft", "Selected sources or workspace identity changed/unavailable; inspect historically, or rebuild and review before a new export.")
        return value, content, {"integrity_status": "verified", "source_status": source_status,
                                "renderer_status": self._renderer_status(value, content, actual),
                                "pdf_status": self._pdf_status(draft, value)}

    def _inspect(self, draft):
        value, content, _ = self._inspection(draft)
        return value, content

    def inspect(self, draft, *, historical=False):
        manifest, content, checks = self._inspection(draft, historical=historical)
        return {"status": "historical" if historical else "reviewable", "relative_path": draft,
                "html_path": str(self.workspace.path(draft + "/resume.html")), "approval_token": manifest["approval_token"],
                "manifest": manifest, "content": content, **checks}

    def _pdf_status(self, draft, manifest):
        """No source bodies are read; a PDF's provenance is separate from HTML review."""
        pdf = self.workspace.path(draft + "/resume.pdf")
        try:
            receipt = self.workspace.path(draft + "/" + RECEIPT_NAME)
        except StoreError:
            # A bad optional export receipt affects this PDF only. Do not follow
            # a symlink or turn an intact unrelated version into a failed page.
            return {"status": "tampered", "reason": "unsafe_receipt_path"}
        if not pdf.exists() and not pdf.is_symlink():
            return {"status": "tampered", "reason": "receipt_without_pdf"} if receipt.exists() or receipt.is_symlink() else {"status": "absent"}
        try:
            raw = regular_bytes(pdf, MAX_PDF)
            if not pdf_structure_valid(raw):
                return {"status": "tampered", "reason": "invalid_pdf_structure"}
            if not receipt.exists() and not receipt.is_symlink():
                return {"status": "unverified", "reason": "export_receipt_missing", "sha256": digest(raw)}
            value = json.loads(regular_bytes(receipt, MAX_CONTENT))
            keys(value, RECEIPT_KEYS, RECEIPT_KEYS)
            expected = {"schema_version": PDF_SCHEMA, "workspace_id": manifest["workspace_id"],
                        "workspace_manifest_hash": manifest["workspace_manifest_hash"], "version": draft,
                        "scope": manifest["scope"], "approval_token": manifest["approval_token"],
                        "frozen_files": manifest["files"], "pdf_sha256": digest(raw), "pdf_size": len(raw)}
            if any(value[k] != v for k, v in expected.items()) or not isinstance(value["exported_at"], str):
                return {"status": "tampered", "reason": "export_receipt_mismatch"}
            expected_token = digest(json_bytes({k: v for k, v in value.items() if k != "integrity_token"}))
            if not isinstance(value["integrity_token"], str) or not hmac.compare_digest(expected_token, value["integrity_token"]):
                return {"status": "tampered", "reason": "export_receipt_changed"}
            # Check frozen file bytes too, so a receipt is not trusted after HTML/photo edits.
            for name, expected_hash in manifest["files"].items():
                raw_file = regular_bytes(self.workspace.path(draft + "/" + name), MAX_HTML if name == "resume.html" else MAX_CONTENT if name == "content.json" else MAX_PHOTO)
                if digest(raw_file) != expected_hash:
                    return {"status": "tampered", "reason": "frozen_input_changed"}
            return {"status": "verified", "sha256": digest(raw), "receipt_relative_path": draft + "/" + RECEIPT_NAME}
        except (StoreError, ValueError, UnicodeError, TypeError, KeyError):
            return {"status": "tampered", "reason": "unreadable_pdf_or_receipt"}

    def artifact_ref(self, version, artifact):
        """Bind the file actually used, even if later career sources are now stale."""
        if artifact not in {"resume.html", "resume.pdf"}:
            error("invalid_artifact", "Choose resume.html or resume.pdf from one exact version.")
        manifest, _, _ = self._frozen(version)
        if artifact == "resume.html":
            sha256 = manifest["files"][artifact]
        else:
            status = self._pdf_status(version, manifest)
            if status["status"] != "verified":
                error("unverified_pdf", "The exact PDF must have a verified export receipt before it can be bound; do not guess or use the latest version.")
            sha256 = status["sha256"]
        return {"version": version, "artifact": artifact, "sha256": sha256}

    def list(self, role_id, company_id=None, opportunity_id=None):
        """Return same-scope version links; never read source bodies or imply approval."""
        scope = self._scope(role_id, company_id, opportunity_id)
        parent = self.workspace.path(scope["location"] + "/resumes")
        versions = []
        if parent.exists():
            for child in sorted(parent.iterdir()):
                if child.is_symlink() or not child.is_dir() or not VERSION_RE.fullmatch(child.name):
                    error("invalid_draft", "Unexpected version entry; inspect it explicitly before continuing.")
                relative = str(child.relative_to(self.root).as_posix())
                _, value, _ = self._metadata(relative, scope)
                html_path = self.workspace.path(relative + "/resume.html")
                pdf_path = self.workspace.path(relative + "/resume.pdf")
                if html_path.is_symlink() or pdf_path.is_symlink():
                    error("invalid_draft", "A listed resume output is unsafe.")
                html_exists = html_path.is_file()
                pdf_status = self._pdf_status(relative, value)
                verified_pdf = pdf_status["status"] == "verified"
                versions.append({"relative_path": relative, "template": value["template"], "created_at": value["created_at"],
                                 "html_relative_path": relative + "/resume.html" if html_exists else None,
                                 "html_path": str(html_path) if html_exists else None,
                                 "pdf_relative_path": relative + "/resume.pdf" if verified_pdf else None,
                                 "pdf_path": str(pdf_path) if verified_pdf else None, "pdf_status": pdf_status,
                                 "pdf_file_relative_path": relative + "/resume.pdf" if pdf_path.is_file() else None,
                                 "pdf_file_path": str(pdf_path) if pdf_path.is_file() else None,
                                 "inspection_status": "not_inspected" if html_exists else "unavailable",
                                 "availability_reason": None if html_exists else "historical_html_missing"})
        versions.sort(key=lambda v: (v["created_at"], v["relative_path"]), reverse=True)
        return {"status": "indexed", "workspace_id": scope["workspace_id"], "scope": scope["scope"], "versions": versions,
                "next_step": "Choose a version, then inspect it before export. Existing files and newest timestamps do not mean user approval."}

    def pdf(self, draft, approved, *, browser=None):
        if not isinstance(approved, str) or not HASH_RE.fullmatch(approved):
            error("approval_mismatch", "Approval must identify the exact inspected version.")
        manifest, _ = self._inspect(draft)
        if not hmac.compare_digest(approved, manifest["approval_token"]):
            error("approval_mismatch", "Approval token does not match this exact reviewed version.")
        output = self.workspace.path(draft + "/resume.pdf")
        if output.exists() or output.is_symlink() or self.workspace.path(draft + "/" + RECEIPT_NAME).exists():
            error("output_exists", "This version already has resume.pdf; it will not be overwritten.")
        executable = find_browser(browser)
        if executable is None:
            return {"status": "engine_missing", "relative_path": draft, "html_path": str(self.workspace.path(draft + "/resume.html")), "message": "No installed Chrome/Chromium found. Open the reviewed resume.html and print to PDF manually. Nothing was installed or exported."}
        with tempfile.TemporaryDirectory(prefix="luji-md-resume-pdf-") as temporary:
            temp = Path(temporary)
            html_raw = regular_bytes(self.workspace.path(draft + "/resume.html"), MAX_HTML)
            if digest(html_raw) != manifest["files"]["resume.html"]:
                error("draft_changed", "HTML changed before export; rebuild and review.")
            snapshot = temp / "resume.html"
            atomic_write(snapshot, html_raw)
            staging = temp / "resume.pdf"
            compile_chromium(executable, snapshot, staging, temp / "profile")
            raw = regular_bytes(staging, MAX_PDF)
            if not pdf_structure_valid(raw):
                error("pdf_failed", "The browser did not produce a complete PDF. No output was saved.")
            self._inspect(draft)
            create_new_file(output, raw)
            receipt = {"schema_version": PDF_SCHEMA, "workspace_id": manifest["workspace_id"],
                       "workspace_manifest_hash": manifest["workspace_manifest_hash"], "version": draft,
                       "scope": manifest["scope"], "approval_token": manifest["approval_token"],
                       "frozen_files": manifest["files"], "pdf_sha256": digest(raw), "pdf_size": len(raw), "exported_at": now()}
            receipt["integrity_token"] = digest(json_bytes(receipt))
            try:
                create_new_file(self.workspace.path(draft + "/" + RECEIPT_NAME), json_bytes(receipt))
            except (OSError, StoreError) as exc:
                error("pdf_receipt_failed", "PDF bytes were saved but their export receipt was not completed; the PDF remains unverified and will not be overwritten. " + type(exc).__name__)
            if self._pdf_status(draft, manifest)["status"] != "verified":
                error("pdf_receipt_failed", "PDF export verification failed after saving; no verified export was recorded.")
        return {"status": "exported", "relative_path": draft + "/resume.pdf", "path": str(output), "approval_token": approved, "sha256": digest(raw), "pdf_status": "verified", "receipt_relative_path": draft + "/" + RECEIPT_NAME}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=os.environ.get("LUJI_WORKSPACE_DIR", "data/workspace"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("templates")
    for name in ("context", "build", "list"):
        command = commands.add_parser(name)
        command.add_argument("--role", required=True)
        command.add_argument("--company")
        command.add_argument("--opportunity")
        if name == "context":
            command.add_argument("--source", action="append", default=[])
        if name == "build":
            command.add_argument("--file", required=True)
            command.add_argument("--template", choices=TEMPLATES, default="profile-split")
            command.add_argument("--photo")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--draft", required=True)
    inspect.add_argument("--historical", action="store_true")
    binding = commands.add_parser("binding")
    binding.add_argument("--draft", required=True)
    binding.add_argument("--artifact", required=True, choices=("resume.html", "resume.pdf"))
    pdf = commands.add_parser("pdf")
    pdf.add_argument("--draft", required=True)
    pdf.add_argument("--approved", required=True)
    pdf.add_argument("--browser")
    args = parser.parse_args(argv)
    try:
        if args.command == "templates":
            result = {"templates": [{"id": key, "name": value} for key, value in TEMPLATES.items()], "default": "profile-split", "behavior": "All six layouts preserve the same content and sources. Layout choice does not certify ATS compatibility."}
        else:
            workspace = ResumeWorkspace(args.workspace)
            if args.command == "context":
                result = workspace.context(args.role, args.company, args.opportunity, source_paths=args.source)
            elif args.command == "build":
                result = workspace.build(read_json(Path(args.file).expanduser()), args.role, args.company, args.opportunity, template=args.template, photo=args.photo)
            elif args.command == "list":
                result = workspace.list(args.role, args.company, args.opportunity)
            elif args.command == "inspect":
                result = workspace.inspect(args.draft, historical=args.historical)
            elif args.command == "binding":
                result = workspace.artifact_ref(args.draft, args.artifact)
            else:
                result = workspace.pdf(args.draft, args.approved, browser=args.browser)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 2 if result.get("status") == "engine_missing" else 0
    except StoreError as exc:
        print(json.dumps({"status": "error", "code": exc.code, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "error", "code": "read_or_io_failed", "message": "Cannot complete the selected local operation; no success was recorded. " + type(exc).__name__}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
