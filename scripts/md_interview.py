#!/usr/bin/env python3
"""Discover scoped interview sources and saved material without reading bodies.

The host Agent selects and reads relevant Markdown, drafts the actual preparation,
then uses md_workspace's ordinary proposal/confirmation protocol to save it.
"""
from __future__ import annotations

import argparse
import json
from pathlib import PurePosixPath
import sys

from md_workspace import Workspace, StoreError, ID_RE, INTERVIEW_TYPES

FACT_TYPES = {"work", "project", "education", "award", "learning"}
LOG_TYPES = {"work-log", "learning-log"}


def fail(message):
    raise StoreError("invalid_scope", message)


class InterviewWorkspace:
    def __init__(self, root):
        self.workspace = root if isinstance(root, Workspace) else Workspace(root)

    def _scope(self, role_id, company_id=None, opportunity_id=None, round_id=None):
        for value in (role_id, company_id, opportunity_id, round_id):
            if value is not None and (not isinstance(value, str) or len(value) > 64 or not ID_RE.fullmatch(value)):
                fail("Choose stable role/company/opportunity/round IDs, not file paths.")
        if role_id is None:
            fail("Choose an existing role.")
        if (company_id is None) != (opportunity_id is None) or (round_id is not None and company_id is None):
            fail("Company and opportunity must be paired; a round belongs to that opportunity.")
        index = self.workspace.index()
        documents = index["documents"]
        goals = [d for d in documents if d["metadata"]["type"] == "goal"
                 and d["metadata"].get("role_id", d["metadata"]["id"]) == role_id]
        if len(goals) != 1:
            fail("The selected role must identify exactly one existing goal.")
        goal = goals[0]
        base = PurePosixPath(goal["path"]).parent
        if goal["path"] != str(base / "goal.md") or len(base.parts) != 3 or base.parts[:2] != ("future", "roles"):
            fail("Store the selected goal as future/roles/<direction>/goal.md.")
        targets = [goal]
        if company_id is None:
            location = base / "common" / "interviews"
        else:
            matches = [d for d in documents if d["metadata"]["type"] in {"jd", "application"}
                       and d["metadata"].get("role_id") == role_id
                       and d["metadata"].get("company_id") == company_id
                       and d["metadata"].get("opportunity_id") == opportunity_id]
            parents = {PurePosixPath(d["path"]).parent for d in matches}
            if len(parents) != 1:
                fail("Choose an opportunity with one consistent JD/application directory.")
            parent = parents.pop()
            remainder = parent.relative_to(base) if parent.is_relative_to(base) else None
            if remainder is None or len(remainder.parts) != 3 or remainder.parts[0] != "companies":
                fail("Opportunity files must use <direction>/companies/<company>/<opportunity>/.")
            targets += [d for d in matches if d["metadata"]["type"] == "jd"]
            location = parent / "interviews"
            if round_id:
                location /= round_id
        scope = {"role_id": role_id, "company_id": company_id,
                 "opportunity_id": opportunity_id, "round_id": round_id}
        records = {d["path"]: d["metadata"] for d in documents}
        for document in documents:
            if document["metadata"]["type"] in INTERVIEW_TYPES and document["metadata"].get("role_id") == role_id:
                # A manually moved file must not be returned under another
                # company's identity merely because its header still matches.
                self.workspace._interview_scope(document["path"], document["metadata"], records)
        return index["workspace_id"], scope, str(location), documents, targets

    @staticmethod
    def _materials(documents, scope):
        common, selected, other_rounds = [], [], []
        for d in documents:
            m = d["metadata"]
            if m["type"] not in INTERVIEW_TYPES or m.get("role_id") != scope["role_id"]:
                continue
            if m.get("company_id") is None and m.get("opportunity_id") is None:
                common.append(d)
            elif scope["company_id"] and m.get("company_id") == scope["company_id"] and m.get("opportunity_id") == scope["opportunity_id"]:
                (selected if not scope["round_id"] or m.get("round_id") == scope["round_id"] else other_rounds).append(d)
        def newest(records):
            return sorted(records, key=lambda d: (d["metadata"].get("prepared_on", d["metadata"].get("practiced_on", d["metadata"].get("updated_on", ""))), d["path"]), reverse=True)
        return {"common": newest(common), "selected": newest(selected), "other_rounds": newest(other_rounds)}

    def list(self, role_id, company_id=None, opportunity_id=None, round_id=None):
        identity, scope, location, documents, _ = self._scope(role_id, company_id, opportunity_id, round_id)
        return {"status": "indexed", "workspace_id": identity, "scope": scope,
                "location": location, "materials": self._materials(documents, scope),
                "freshness_checked": False}

    def context(self, role_id, company_id=None, opportunity_id=None, round_id=None):
        identity, scope, location, documents, targets = self._scope(role_id, company_id, opportunity_id, round_id)
        facts, progress = [], []
        for document in documents:
            m = document["metadata"]
            if m["type"] in FACT_TYPES:
                facts.append({**document, "usage": "verify_personal_claims"})
            elif m["type"] in LOG_TYPES:
                confirmed = m.get("evidence_status") == "confirmed" and bool(m.get("evidence_paths"))
                (facts if confirmed else progress).append({**document, "usage": "verify_confirmed_output" if confirmed else "practice_context_only"})
        feedback = [d for d in documents if d["metadata"]["type"] == "feedback"
                    and scope["company_id"] and d["metadata"].get("role_id") == role_id
                    and d["metadata"].get("company_id") == company_id
                    and d["metadata"].get("opportunity_id") == opportunity_id]
        opportunities = {}
        for document in documents:
            m = document["metadata"]
            if m["type"] not in {"jd", "application"} or m.get("role_id") != role_id:
                continue
            if company_id and (m.get("company_id") != company_id or m.get("opportunity_id") != opportunity_id):
                continue
            key = (m["company_id"], m["opportunity_id"])
            entry = opportunities.setdefault(key, {"company_id": m["company_id"], "company_name": m["company_name"],
                                                   "opportunity_id": m["opportunity_id"], "documents": []})
            entry["documents"].append(document)
        missing = []
        if not any(d["metadata"]["type"] == "jd" for d in targets):
            missing.append("No selected company JD; use an explicit role outline or ask for the JD before company-specific predictions.")
        if not facts:
            missing.append("No experience/output candidate found; personal examples remain unknown.")
        if company_id and not round_id:
            missing.append("Round not selected; discuss first, then choose a stable round ID before saving scoped material.")
        return {"status": "indexed", "workspace_id": identity, "scope": scope, "location": location,
                "target_documents": targets, "evidence_candidates": facts,
                "opportunity_candidates": [opportunities[key] for key in sorted(opportunities)],
                "progress_candidates": progress, "feedback_candidates": feedback,
                "materials": self._materials(documents, scope), "missing": missing,
                "freshness_checked": False,
                "next_step": "Metadata only. Read the selected target, relevant experience/output and prior material explicitly. Verify their provenance before personal claims. Draft preparation or practice Markdown; save only via the normal reviewed proposal flow. No task, application stage or evidence has been changed."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("context", "list"):
        sub = commands.add_parser(command)
        sub.add_argument("--role", required=True)
        sub.add_argument("--company")
        sub.add_argument("--opportunity")
        sub.add_argument("--round", dest="round_id")
    args = parser.parse_args(argv)
    try:
        helper = InterviewWorkspace(args.workspace)
        result = getattr(helper, args.command)(args.role, args.company, args.opportunity, args.round_id)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (StoreError, OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "code": getattr(exc, "code", "interview_error"),
                          "message": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
