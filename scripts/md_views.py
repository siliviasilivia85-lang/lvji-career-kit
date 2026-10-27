#!/usr/bin/env python3
"""Build a single offline, read-only workspace view from canonical Markdown.

The editable HTML asset contains one __LUJI_DATA__ placeholder. Rendering never
updates career documents, and an unsuccessful read leaves the last HTML intact.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path, PurePosixPath
import re
import sys

from md_workspace import Workspace, StoreError, atomic_write, INTERVIEW_TYPES

ASSET = Path(__file__).resolve().parent.parent / "assets" / "md_workspace.html"
DERIVED = {"portrait", "assessment", "check", "interview-story", "interview-prep", "interview-practice", "stage-summary"}
VIEWS = {"overview", "plan", "roles", "applications"}
PERIODS = {"daily", "weekly", "monthly", "yearly"}


class ViewError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


def _date(value):
    try:
        return dt.date.fromisoformat(value or dt.date.today().isoformat()).isoformat()
    except (ValueError, TypeError):
        raise ViewError("invalid_date", "日期必须为 YYYY-MM-DD。")


def _sha(value):
    return value.removeprefix("sha256:") if isinstance(value, str) else value


def _references(metadata):
    paths = set(metadata.get("sources", []))
    paths.update(metadata.get("source_revisions", {}))
    for criterion in metadata.get("criteria", []):
        paths.update(criterion.get("evidence", []))
    paths.update(metadata.get("evidence_paths", []))
    if metadata.get("asset_path"):
        paths.add(metadata["asset_path"])
    return paths


def _event_resume(ws, helper, application, reference, versions):
    """Derive an event's exact artifact link; never select a newest version."""
    if reference is None:
        return {"status": "not_recorded"}
    invalid = {"status": "invalid", "message": "简历引用无效，需核对原记录。"}
    if not isinstance(reference, dict) or set(reference) != {"version", "artifact", "sha256"}:
        return invalid
    version, artifact, expected = (reference[key] for key in ("version", "artifact", "sha256"))
    if (not isinstance(version, str) or not version.startswith("future/roles/") or
            any(part in {"", ".", ".."} for part in version.split("/")) or "\\" in version or
            str(PurePosixPath(version)) != version or
            not re.fullmatch(r"v-[0-9a-f]{32}", PurePosixPath(version).name) or
            not isinstance(artifact, str) or artifact not in {"resume.html", "resume.pdf"} or
            not isinstance(expected, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", expected)):
        return invalid
    result = {"version": version, "artifact": artifact, "sha256": expected}
    listed = versions.get(version)
    if listed is None:
        return {**result, "status": "unavailable", "message": "所用历史版本当前不可用，请让 Agent 核对。"}
    scope = listed["scope"]
    if scope.get("role_id") != application.get("role_id") or not (
            (scope.get("company_id") is None and scope.get("opportunity_id") is None) or
            (scope.get("company_id") == application.get("company_id") and
             scope.get("opportunity_id") == application.get("opportunity_id"))):
        return {**result, "status": "wrong_scope", "message": "简历不属于这个岗位或公司机会。"}
    try:
        actual = helper.artifact_ref(version, artifact)
    except (StoreError, OSError, ValueError) as exc:
        return {**result, "status": "unavailable", "message": "历史文件未通过核验，请让 Agent 检查。",
                "reason": getattr(exc, "code", "read_failed")}
    if actual != reference:
        return {**result, "status": "changed", "message": "当前文件与投递时记录的摘要不同，需核对。"}
    return {**result, "status": "verified", "href": ws.path(version + "/" + artifact).as_uri()}


def build_snapshot(workspace, date=None):
    """Read only explicit indexed documents and their local source references."""
    ws = workspace if isinstance(workspace, Workspace) else Workspace(workspace)
    as_of = _date(date)
    index = ws.index()
    indexed = index["documents"]
    indexed_metadata = {entry["path"]: entry["metadata"] for entry in indexed}
    for entry in indexed:
        if entry["metadata"]["type"] in INTERVIEW_TYPES:
            ws._interview_scope(entry["path"], entry["metadata"], indexed_metadata)
    paths = [entry["path"] for entry in indexed]
    first = ws.read(paths)
    documents = {entry["path"]: entry for entry in first["documents"]}
    missing = set(paths) - set(documents)
    if missing:
        raise ViewError("snapshot_changed", "读取时文件已不存在：" + ", ".join(sorted(missing)))
    references = set()
    for record in documents.values():
        references.update(_references(record["metadata"]))
    # Read the complete selected set together so every freshness comparison uses
    # the same read result; include source originals only when explicitly cited.
    selected = sorted(set(paths) | references)
    result = ws.read(selected) if references else first
    records = {entry["path"]: entry for entry in result["documents"]}
    revisions = result.get("draft_base", {}).get("files", {})
    missing = set(selected) - set(records)
    if missing:
        raise ViewError("source_missing", "快照引用文件缺失：" + ", ".join(sorted(missing)))
    # Metadata may have changed after indexing: do not publish an incomplete set
    # of newly cited sources or silently turn a changed document into empty data.
    for path in paths:
        if not _references(records[path]["metadata"]).issubset(set(selected)):
            raise ViewError("snapshot_changed", "读取期间来源改变，请重新生成快照。")
    actual_metadata = {path: records[path]["metadata"] for path in paths}
    for path in paths:
        metadata = actual_metadata[path]
        if metadata["type"] in INTERVIEW_TYPES:
            ws._interview_scope(path, metadata, actual_metadata)
    links = {}
    for path in selected:
        file_path = ws.path(path)
        links[path] = {"path": path, "absolute_path": str(file_path), "href": file_path.as_uri(),
                       "revision": records[path].get("revision", revisions.get(path))}
    docs, warnings = [], list(index.get("warnings", []))
    for path in paths:
        entry = records[path]
        metadata = entry["metadata"]
        expected = metadata.get("source_revisions", {})
        cited = _references(metadata)
        changed = [p for p in sorted(cited) if p in expected and
                   _sha(expected[p]) != _sha(links[p]["revision"])]
        unverified = [p for p in sorted(cited) if p not in expected]
        freshness = "stale" if changed else "unverified" if metadata["type"] in DERIVED and (unverified or not cited) else "current"
        if freshness != "current":
            warnings.append({"path": path, "status": freshness,
                             "message": "来源已变化，需重新评估" if changed else "来源基准未齐，需重新评估"})
        docs.append({"path": path, "metadata": metadata, "body": entry.get("body", ""),
                     "revision": entry.get("revision", revisions.get(path)),
                     "freshness": freshness, "changed_sources": changed,
                     "unverified_sources": unverified, "href": links[path]["href"]})
    docs.sort(key=lambda entry: entry["path"])
    # A preparation file can reuse a story card whose own evidence changed.
    # Keep both files intact and expose that indirect invalidation as well.
    by_path = {doc["path"]: doc for doc in docs}
    checked = set()
    def review_dependencies(doc, visiting):
        path = doc["path"]
        if path in checked or path in visiting:
            return
        visiting = visiting | {path}
        for source in sorted(_references(doc["metadata"])):
            parent = by_path.get(source)
            if parent is None:
                continue
            review_dependencies(parent, visiting)
            if doc["metadata"]["type"] in DERIVED and parent["freshness"] != "current":
                if parent["freshness"] == "stale":
                    doc["freshness"] = "stale"
                    doc["changed_sources"] = sorted(set(doc["changed_sources"]) | {source} | set(parent["changed_sources"]))
                elif doc["freshness"] == "current":
                    doc["freshness"] = "unverified"
                doc["unverified_sources"] = sorted(set(doc["unverified_sources"]) | set(parent["unverified_sources"]))
                if not any(isinstance(w, dict) and w.get("path") == path for w in warnings):
                    warnings.append({"path": path, "status": doc["freshness"],
                                     "message": "所用材料的来源需复核"})
        checked.add(path)
    for doc in docs:
        review_dependencies(doc, set())
    for warning in warnings:
        if isinstance(warning, dict) and warning.get("path") in by_path:
            warning["status"] = by_path[warning["path"]]["freshness"]
    by_type = {}
    for doc in docs:
        by_type.setdefault(doc["metadata"]["type"], []).append(doc)
    roles = []
    for goal in by_type.get("goal", []):
        m = goal["metadata"]
        role_id = m.get("role_id", m["id"])
        related = [d for d in docs if d["metadata"].get("role_id") == role_id]
        assessments = sorted([d for d in related if d["metadata"]["type"] == "assessment"],
                             key=lambda d: (d["metadata"].get("evaluated_on", ""), d["path"]), reverse=True)
        assessment = assessments[0] if assessments else None
        counts = dict.fromkeys(("supported", "partial", "gap", "unknown"), 0)
        if assessment:
            for criterion in assessment["metadata"].get("criteria", []):
                counts[criterion["status"]] += 1
        known = counts["supported"] + counts["partial"] + counts["gap"]
        roles.append({"id": role_id, "goal": goal, "documents": [d["path"] for d in related],
                      "assessment": assessment, "counts": counts, "known": known,
                      "total": known + counts["unknown"],
                      "fit_sort_value": (counts["supported"] + 0.5 * counts["partial"]) / known if known else None,
                      "priority": m.get("priority", 0),
                      "needs_review": bool(assessment and assessment["freshness"] != "current")})
    roles.sort(key=lambda role: role["id"])
    # The resume helper lists frozen artifact metadata only: no content reads,
    # inspect calls or approval tokens. Source changes leave historical links.
    from md_resume import ResumeWorkspace
    resume_workspace = ResumeWorkspace(ws)
    resumes = []
    for role in roles:
        scopes = {(None, None)}
        scopes.update((d["metadata"].get("company_id"), d["metadata"].get("opportunity_id"))
                      for d in docs if d["metadata"].get("role_id") == role["id"] and
                      d["metadata"]["type"] in {"jd", "application"})
        for company_id, opportunity_id in sorted(scopes, key=lambda pair: (pair[0] or "", pair[1] or "")):
            listed = resume_workspace.list(role["id"], company_id, opportunity_id)
            for version in listed["versions"]:
                item = {**version, "scope": listed["scope"]}
                item["html_href"] = ws.path(version["html_relative_path"]).as_uri() if version.get("html_relative_path") else None
                item["pdf_href"] = ws.path(version["pdf_relative_path"]).as_uri() if version.get("pdf_relative_path") else None
                resumes.append(item)
    versions = {item["relative_path"]: item for item in resumes}
    application_events = {}
    for application in by_type.get("application", []):
        metadata = application["metadata"]
        application_events[application["path"]] = [
            {"date": event.get("date"), "stage": event.get("stage"), "note": event.get("note", ""),
             "resume": _event_resume(ws, resume_workspace, metadata, event.get("resume_ref"), versions)}
            for event in metadata.get("history", [])]
    return {"schema_version": "luji-markdown-view-0.1", "workspace_id": index["workspace_id"],
            "workspace_path": str(ws.root), "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "as_of": as_of, "documents": docs, "source_links": links, "roles": roles,
            "items": by_type.get("item", []), "actions": by_type.get("action", []),
            "logs": by_type.get("learning-log", []) + by_type.get("work-log", []),
            "notes": by_type.get("note", []), "stages": by_type.get("stage-summary", []),
            "plans": by_type.get("plan", []), "applications": by_type.get("application", []),
            "application_events": application_events,
            "resumes": resumes, "warnings": warnings}


def render(workspace, output=None, date=None, template=None, view="overview", role=None, company=None, opportunity=None, period="daily"):
    ws = workspace if isinstance(workspace, Workspace) else Workspace(workspace)
    if view not in VIEWS:
        raise ViewError("invalid_view", "未知视图。")
    if period not in PERIODS:
        raise ViewError("invalid_period", "未知计划尺度。")
    snapshot = build_snapshot(ws, date)
    snapshot["initial_state"] = {"view": view, "period": period, "role": role or "", "company": company or "", "opportunity": opportunity or ""}
    template_path = Path(template) if template else ASSET
    html = template_path.read_text(encoding="utf-8")
    if html.count("__LUJI_DATA__") != 1:
        raise ViewError("invalid_template", "模板必须且只能包含一个 __LUJI_DATA__ 占位符。")
    # JSON is embedded as data, never HTML; escaping '<' prevents </script>
    # termination even when a source contains attacker-controlled Markdown.
    payload = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))
    for char, replacement in (("&", "\\u0026"), ("<", "\\u003c"), (">", "\\u003e"), ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        payload = payload.replace(char, replacement)
    # Resolve the OS-level /tmp alias without allowing an existing output file
    # symlink to redirect a write. Workspace.path protects internal directories.
    requested = Path(output).expanduser().absolute() if output else ws.path("views/overview.html")
    if requested.is_symlink():
        raise ViewError("invalid_output", "快照输出不能是符号链接。")
    destination = requested.parent.resolve() / requested.name
    # A view destination cannot replace canonical records or runtime identity.
    try:
        relative = destination.relative_to(ws.root)
    except ValueError:
        relative = None
    if relative is not None and (not relative.parts or relative.parts[0] != "views"):
        raise ViewError("invalid_output", "工作区内的快照只能写入 views/。")
    if destination.suffix.lower() != ".html":
        raise ViewError("invalid_output", "快照输出必须为 .html 文件。")
    if destination.is_symlink():
        raise ViewError("invalid_output", "快照输出路径不能包含符号链接。")
    atomic_write(destination, html.replace("__LUJI_DATA__", payload).encode("utf-8"))
    return {"status": "generated_not_opened", "output": str(destination),
            "workspace_id": snapshot["workspace_id"], "as_of": snapshot["as_of"],
            "generated_at": snapshot["generated_at"], "documents_count": len(snapshot["documents"]),
            "warnings": snapshot["warnings"], "read_only": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--date")
    parser.add_argument("--output")
    parser.add_argument("--template", help="有意替换的本地 HTML 模板")
    parser.add_argument("--view", choices=sorted(VIEWS), default="overview")
    parser.add_argument("--period", choices=sorted(PERIODS), default="daily")
    parser.add_argument("--role")
    parser.add_argument("--company")
    parser.add_argument("--opportunity")
    args = parser.parse_args(argv)
    try:
        result = render(args.workspace, args.output, args.date, args.template, args.view, args.role, args.company, args.opportunity, args.period)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (StoreError, ViewError, OSError, ValueError, KeyError) as error:
        print(json.dumps({"status": "error", "code": getattr(error, "code", "view_error"),
                          "message": getattr(error, "message", str(error)), "previous_snapshot_preserved": True}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
