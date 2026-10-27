#!/usr/bin/env python3
"""Small Markdown-first career workspace store (Python 3.10+, standard library).

Career facts live in past/, present/ and future/.  JSON is used only for the
identity manifest, source receipts and recoverable draft/history bookkeeping.
There is deliberately no migration or implicit workspace location.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
import uuid


SCHEMA_VERSION = "luji-markdown-0.1"
AREAS = {"past", "present", "future"}
TYPES = {"personal", "work", "education", "project", "award", "learning",
         "portrait", "item", "goal", "thought", "research", "jd", "assessment",
         "check", "action", "learning-log", "work-log", "plan", "application",
         "feedback", "photo-note", "interview-story", "interview-prep", "interview-practice",
         "note", "stage-summary"}
INTERVIEW_TYPES = {"interview-story", "interview-prep", "interview-practice"}
PAST_TYPES = {"personal", "work", "education", "project", "award", "learning",
              "portrait", "photo-note"}
PRESENT_TYPES = {"item", "check", "action", "learning-log", "work-log", "plan", "note", "stage-summary"}
TRANSITIONS = {"review", "leaving", "offer", "joining", "direction-change"}
STAGES = {"researching", "preparing", "applied", "screening", "interview", "offer", "closed"}
STATUSES = {"todo", "doing", "done", "paused"}
SOURCE_KINDS = {"resume", "photo", "learning", "experience", "project", "reference", "evidence"}
MAX_SOURCE_BYTES = 50 * 1024 * 1024
MAX_DOCUMENT_BYTES = 4 * 1024 * 1024
ID_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
KEY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*\Z")
REV_RE = re.compile(r"(?:sha256:)?[0-9a-f]{64}\Z")


def is_material_path(relative):
    """Recognize explicit user drop locations, without opening any file.

    Arbitrary files in these locations are sources, even when they use .md.
    Canonical career records remain outside them; filenames need no schema.
    """
    if not isinstance(relative, str) or not relative or "\\" in relative or any(ord(c) < 32 for c in relative):
        return False
    parts = relative.split("/")
    if any(p in {"", ".", ".."} for p in parts) or PurePosixPath(relative).is_absolute() or re.match(r"^[A-Za-z]:", relative):
        return False
    if parts[0] == "inbox":
        return len(parts) >= 2
    if len(parts) >= 3 and parts[0] in AREAS and parts[1] == "materials":
        return True
    if len(parts) >= 5 and parts[:2] == ["present", "items"] and parts[3] == "materials":
        return True
    if len(parts) >= 5 and parts[:2] == ["future", "roles"] and parts[3] == "materials":
        return True
    return (len(parts) >= 8 and parts[:2] == ["future", "roles"] and
            parts[3] == "companies" and parts[6] == "materials")


class StoreError(Exception):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code, self.message, self.details = code, message, details

    def as_dict(self):
        result = {"code": self.code, "message": self.message}
        if self.details is not None:
            result["details"] = self.details
        return result


def digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def json_bytes(value) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    except (ValueError, TypeError) as exc:
        raise StoreError("invalid_json", str(exc)) from exc


def read_json(path: Path):
    try:
        with _open_regular(Path(path)) as stream:
            return json.loads(stream.read().decode("utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise StoreError("read_json", f"Cannot read JSON {path}: {exc}") from exc


def _sync_dir(path):
    if os.name == "nt":
        # Windows has no portable stdlib directory fsync. File data is still
        # fsynced before replace; journals make interrupted batches recoverable.
        return
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        # Some filesystems do not support directory fsync; do not hide other IO errors.
        import errno
        if exc.errno not in {errno.EINVAL, errno.ENOTSUP, errno.EBADF}:
            raise


def atomic_write(path: Path, value: bytes):
    """Durable same-directory replacement; caller controls destination scope."""
    path = Path(path)
    if path.is_symlink():
        raise StoreError("unsafe_path", f"Refusing symlink: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        fd, temp = tempfile.mkstemp(prefix=".luji-write-", dir=path.parent)
        with os.fdopen(fd, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        temp = None
        _sync_dir(path.parent)
    except OSError as exc:
        raise StoreError("write_failed", f"Cannot write {path}: {exc}") from exc
    finally:
        if temp is not None:
            with contextlib.suppress(OSError):
                os.unlink(temp)


def _simple(value, depth=0):
    if depth > 12:
        raise StoreError("metadata", "Metadata nesting exceeds 12 levels")
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float) and math.isfinite(value):
        return
    if isinstance(value, list):
        for item in value:
            _simple(item, depth + 1)
        return
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        for item in value.values():
            _simple(item, depth + 1)
        return
    raise StoreError("metadata", "Metadata must contain finite JSON-compatible values")


def parse_document(text: str):
    """Return (metadata, Markdown body), parsing a safe one-line YAML subset."""
    if not isinstance(text, str):
        raise StoreError("frontmatter", "Document must be UTF-8 text")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise StoreError("frontmatter", "Markdown must start with --- frontmatter")
    metadata = {}
    for pos, line in enumerate(lines[1:], 1):
        raw = line.rstrip("\r\n")
        if raw == "---":
            return metadata, "".join(lines[pos + 1:])
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[0].isspace() or ":" not in raw:
            raise StoreError("frontmatter", f"Line {pos + 1}: use one key: value per line")
        key, value = raw.split(":", 1)
        key, value = key.strip(), value.strip()
        if not KEY_RE.fullmatch(key) or key in metadata:
            raise StoreError("frontmatter", f"Invalid or repeated metadata key: {key}")
        if not value:
            raise StoreError("frontmatter", f"Empty metadata value: {key}; use null explicitly")
        try:
            parsed = json.loads(value)
        except ValueError:
            if value.startswith("'") and value.endswith("'") and len(value) >= 2:
                parsed = value[1:-1].replace("''", "'")
            elif value[0] in "!&*|>{[\"'" or value in {"---", "..."}:
                raise StoreError("frontmatter", f"Unsupported YAML value for {key}; use a JSON literal")
            else:
                parsed = value
        _simple(parsed)
        metadata[key] = parsed
    raise StoreError("frontmatter", "Missing closing --- frontmatter delimiter")


def dump_document(metadata, body):
    if not isinstance(metadata, dict) or not isinstance(body, str):
        raise StoreError("frontmatter", "Expected metadata object and Markdown body string")
    _simple(metadata)
    lines = ["---"]
    for key, value in metadata.items():
        if not KEY_RE.fullmatch(key):
            raise StoreError("frontmatter", f"Invalid metadata key: {key}")
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False, allow_nan=False)}")
    return "\n".join(lines) + "\n---\n" + body


def _date(value, field, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise StoreError("metadata", f"{field} must be an ISO date" + (" or null" if nullable else ""))
    try:
        dt.date.fromisoformat(value)
    except ValueError as exc:
        raise StoreError("metadata", f"Invalid date in {field}: {value}") from exc


def _string(value, field, nonempty=True):
    if not isinstance(value, str) or (nonempty and not value.strip()):
        raise StoreError("metadata", f"{field} must be a" + (" nonempty" if nonempty else "") + " string")


def _id(value, field):
    if not isinstance(value, str) or len(value) > 64 or not ID_RE.fullmatch(value):
        raise StoreError("metadata", f"{field} must be a lower ASCII slug of at most 64 characters")


def _strings(value, field, ids=False):
    if not isinstance(value, list):
        raise StoreError("metadata", f"{field} must be a list")
    for item in value:
        (_id if ids else _string)(item, field)
    if len(value) != len(set(value)):
        raise StoreError("metadata", f"{field} contains repeated entries")


def _enum(value, field, choices):
    if not isinstance(value, str) or value not in choices:
        raise StoreError("metadata", f"{field} must be one of {', '.join(sorted(choices))}")


def _revision_equal(a, b):
    if a is None or b is None:
        return a is b
    return a.removeprefix("sha256:") == b.removeprefix("sha256:")


def _open_regular(path):
    """Do not block on FIFOs/devices, and reject a symlink swapped at open time."""
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise StoreError("not_regular", f"Not a regular file: {path}")
        return os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise


class Workspace:
    def __init__(self, root):
        if root is None or not str(root).strip():
            raise StoreError("workspace_required", "Choose a workspace explicitly")
        self.root = Path(root).expanduser().resolve()

    def path(self, relative):
        if not isinstance(relative, str) or not relative or "\\" in relative or any(ord(c) < 32 for c in relative):
            raise StoreError("unsafe_path", f"Invalid relative path: {relative!r}")
        parts = relative.split("/")
        if any(p in {"", ".", ".."} for p in parts) or PurePosixPath(relative).is_absolute():
            raise StoreError("unsafe_path", f"Use a workspace-relative path without . or ..: {relative}")
        if re.match(r"^[A-Za-z]:", relative):
            raise StoreError("unsafe_path", f"Absolute drive path is not allowed: {relative}")
        current = self.root
        for part in parts:
            current = current / part
            if current.is_symlink():
                raise StoreError("unsafe_path", f"Symlink is not allowed: {relative}")
        return current

    def _canonical(self, relative, allow_original=True):
        self.path(relative)
        parts = relative.split("/")
        original = relative.startswith("past/originals/") or is_material_path(relative)
        if not original and (parts[0] not in AREAS or "resumes" in parts):
            raise StoreError("not_canonical", f"Not a canonical document/source: {relative}")
        if original:
            if not allow_original or (relative.startswith("past/originals/") and relative.endswith(".receipt.json")):
                raise StoreError("not_canonical", f"Not an editable canonical Markdown record: {relative}")
        elif not relative.endswith(".md"):
            raise StoreError("not_canonical", f"Career documents must be Markdown: {relative}")
        return original

    def _bytes(self, relative, missing=False):
        path = self.path(relative)
        try:
            with _open_regular(path) as stream:
                limit = MAX_SOURCE_BYTES if relative.startswith("past/originals/") or is_material_path(relative) else MAX_DOCUMENT_BYTES
                if os.fstat(stream.fileno()).st_size > limit:
                    raise StoreError("too_large", f"File exceeds workspace read limit: {relative}")
                value = stream.read(limit + 1)
                if len(value) > limit:
                    raise StoreError("too_large", f"File exceeds workspace read limit: {relative}")
                return value
        except FileNotFoundError:
            if missing:
                return None
            raise StoreError("missing_source", f"File is missing: {relative}")
        except OSError as exc:
            raise StoreError("read_failed", f"Cannot read {relative}: {exc}") from exc

    def _revision(self, relative):
        value = self._bytes(relative, missing=True)
        return None if value is None else digest(value)

    def manifest(self):
        data = read_json(self.path("manifest.json"))
        if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
            raise StoreError("unsupported_workspace", "Expected luji-markdown-0.1; old formats are not migrated")
        if set(data) != {"schema_version", "workspace_id", "created_at"}:
            raise StoreError("manifest", "Manifest is identity only: schema_version, workspace_id, created_at")
        try:
            uuid.UUID(data["workspace_id"])
            dt.datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        except (ValueError, TypeError, AttributeError) as exc:
            raise StoreError("manifest", "Invalid manifest identity or creation date") from exc
        return data

    def initialize(self, language="zh", skill_root=None):
        # Language and Skill location belong to replaceable navigation, never the
        # identity manifest or a career record. Validate before creating files.
        from md_navigation import NavigationWorkspace
        NavigationWorkspace.validate_setup(language, skill_root)
        if self.root.exists() and (not self.root.is_dir() or any(self.root.iterdir())):
            raise StoreError("not_empty", "Initialize only a new/empty directory; no automatic migration")
        self.root.mkdir(parents=True, exist_ok=True)
        directories = ["past/" + s for s in ("work", "education", "projects", "awards", "learning", "photos", "originals")]
        directories += ["present/" + s for s in ("items", "checks", "actions", "notes", "stages", "learning", "work", "plans/daily", "plans/weekly", "plans/monthly", "plans/yearly")]
        directories += ["inbox", "past/materials", "present/materials", "future/materials",
                        "future/roles", "views", ".luji/proposals", ".luji/history"]
        for name in directories:
            self.path(name).mkdir(parents=True, exist_ok=True)
        result = {"schema_version": SCHEMA_VERSION, "workspace_id": str(uuid.uuid4()),
                  "created_at": dt.datetime.now(dt.timezone.utc).isoformat()}
        atomic_write(self.path("manifest.json"), json_bytes(result))
        navigation = NavigationWorkspace(self.root)
        navigation.setup(language=language, skill_root=skill_root)
        navigation.refresh("all")
        return result

    def _metadata(self, metadata, relative):
        if not isinstance(metadata, dict):
            raise StoreError("metadata", f"Expected metadata object: {relative}")
        _simple(metadata)
        for key in metadata:
            if not KEY_RE.fullmatch(key):
                raise StoreError("metadata", f"Invalid metadata key {key} in {relative}")
        for key in ("id", "type", "title"):
            if key not in metadata:
                raise StoreError("metadata", f"Missing {key} in {relative}")
        _id(metadata["id"], "id")
        _enum(metadata["type"], "type", TYPES)
        _string(metadata["title"], "title")
        if "status" in metadata:
            _string(metadata["status"], "status")
        kind = metadata["type"]
        expected = "past" if kind in PAST_TYPES else "present" if kind in PRESENT_TYPES else "future"
        if relative.split("/")[0] != expected:
            raise StoreError("typed_path", f"{kind} belongs under {expected}/: {relative}")
        if kind == "item" and not relative.startswith("present/items/"):
            raise StoreError("typed_path", f"Continuing items belong under present/items/: {relative}")
        if kind in {"note", "stage-summary"}:
            expected_dir = "present/notes/" if kind == "note" else "present/stages/"
            if not relative.startswith(expected_dir):
                raise StoreError("typed_path", f"{kind} belongs under {expected_dir}: {relative}")
        for key in ("created_at", "updated_at"):
            if key in metadata:
                try:
                    dt.datetime.fromisoformat(metadata[key].replace("Z", "+00:00"))
                except (ValueError, TypeError, AttributeError) as exc:
                    raise StoreError("metadata", f"{key} must be an ISO date/time") from exc
        if "occurred_on" in metadata:
            _date(metadata["occurred_on"], "occurred_on")
        for key in ("sources", "tags", "evidence_paths"):
            if key in metadata:
                _strings(metadata[key], key)
        for key in ("related_ids", "goal_ids", "action_ids", "depends_on", "item_ids"):
            if key in metadata:
                _strings(metadata[key], key, ids=True)
        for key in ("role_id", "company_id", "opportunity_id", "goal_id", "item_id"):
            if key in metadata:
                _id(metadata[key], key)
        if kind in INTERVIEW_TYPES and "round_id" in metadata:
            _id(metadata["round_id"], "round_id")
        for source in self._source_paths(metadata):
            self._canonical(source)
        revisions = metadata.get("source_revisions", {})
        if not isinstance(revisions, dict):
            raise StoreError("metadata", "source_revisions must be an object")
        for source, revision in revisions.items():
            self._canonical(source)
            if not isinstance(revision, str) or not REV_RE.fullmatch(revision):
                raise StoreError("metadata", f"Invalid source revision: {source}")
            if source not in metadata.get("sources", []):
                raise StoreError("metadata", f"Tracked source must also appear in sources: {source}")
        if kind in {"note", "stage-summary"}:
            missing_revisions = [p for p in self._source_paths(metadata) if p not in revisions]
            if missing_revisions:
                raise StoreError("missing_source_revision", "Referenced notes/stage summaries need reviewed source_revisions", missing_revisions)
        if "source_url" in metadata:
            _string(metadata["source_url"], "source_url")
            if not re.match(r"https?://[^\s]+\Z", metadata["source_url"]):
                raise StoreError("metadata", "source_url must be an explicit http(s) citation")
        required = {
            "thought": ("role_id", "recorded_on"), "research": ("role_id", "researched_on"),
            "jd": ("role_id", "company_id", "company_name", "opportunity_id", "collected_on", "requirements"),
            "assessment": ("role_id", "evaluated_on", "criteria"), "check": ("generated_on",),
            "action": ("status",), "learning-log": ("recorded_on",), "work-log": ("recorded_on",),
            "note": ("recorded_on",), "stage-summary": ("recorded_on",),
            "plan": ("period", "start_date", "end_date", "action_ids"),
            "application": ("role_id", "company_id", "company_name", "opportunity_id", "stage", "updated_on", "next_action", "history"),
            "feedback": ("role_id", "company_id", "opportunity_id", "received_on"), "photo-note": ("asset_path",),
            "interview-story": ("role_id", "updated_on", "sources"),
            "interview-prep": ("role_id", "prepared_on", "sources"),
            "interview-practice": ("role_id", "practiced_on", "sources"),
        }.get(kind, ())
        for key in required:
            if key not in metadata:
                raise StoreError("metadata", f"Missing {key} for {kind}: {relative}")
        for key in ("recorded_on", "researched_on", "collected_on", "evaluated_on", "generated_on", "updated_on", "received_on", "start_date", "end_date"):
            if key in metadata:
                _date(metadata[key], key)
        if kind in INTERVIEW_TYPES:
            for key in ("prepared_on", "practiced_on"):
                if key in metadata:
                    _date(metadata[key], key)
            if "interview_on" in metadata:
                if kind != "interview-prep":
                    raise StoreError("metadata", "interview_on belongs only to interview-prep")
                _date(metadata["interview_on"], "interview_on", nullable=True)
            if not metadata["sources"]:
                raise StoreError("missing_source", "Interview material needs explicitly selected sources")
            company = "company_id" in metadata
            opportunity = "opportunity_id" in metadata
            if company != opportunity:
                raise StoreError("invalid_scope", "Interview company and opportunity IDs must be supplied together")
            if kind == "interview-story" and (company or "round_id" in metadata):
                raise StoreError("invalid_scope", "Reusable interview stories belong to a role, not one company or round")
            if company != ("round_id" in metadata):
                raise StoreError("invalid_scope", "A company interview needs round_id; common material has no round_id")
            parts = PurePosixPath(relative).parts
            if parts[:2] != ("future", "roles"):
                raise StoreError("typed_path", "Interview files belong under future/roles/<role>/")
            if kind == "interview-story":
                valid = len(parts) == 7 and parts[3:6] == ("common", "interviews", "stories")
            elif company:
                valid = len(parts) == 9 and parts[3] == "companies" and parts[6:8] == ("interviews", metadata["round_id"])
            else:
                valid = len(parts) == 6 and parts[3:5] == ("common", "interviews")
            if not valid:
                raise StoreError("typed_path", "Interview file path must match its common/company/round scope: " + relative)
        for key in ("desired_by", "scheduled_for", "due_on"):
            if key in metadata:
                _date(metadata[key], key, nullable=True)
        for key in ("minutes", "spent_minutes"):
            if key in metadata and metadata[key] is not None and (type(metadata[key]) is not int or metadata[key] < 0):
                raise StoreError("metadata", f"{key} must be a nonnegative integer or null")
        if "company_name" in metadata:
            _string(metadata["company_name"], "company_name")
        if kind in {"action", "item"} and "status" in metadata:
            _enum(metadata["status"], "status", STATUSES)
        if kind == "goal":
            if "decision_status" in metadata:
                _enum(metadata["decision_status"], "decision_status", {"exploring", "adopted", "paused"})
            priority = metadata.get("priority", 0)
            if type(priority) is not int or not 0 <= priority <= 5:
                raise StoreError("metadata", "priority must be an integer 0..5")
            if "target_kind" in metadata:
                _enum(metadata["target_kind"], "target_kind", {"role", "startup", "other"})
        if kind == "stage-summary" and "transition" in metadata:
            _enum(metadata["transition"], "transition", TRANSITIONS)
        if kind == "jd":
            _strings(metadata["requirements"], "requirements")
        if kind == "assessment":
            criteria = metadata["criteria"]
            if not isinstance(criteria, list):
                raise StoreError("metadata", "criteria must be a list")
            for criterion in criteria:
                if not isinstance(criterion, dict) or not {"requirement", "status", "evidence", "note"}.issubset(criterion):
                    raise StoreError("metadata", "Each criterion needs requirement, status, evidence, note")
                _string(criterion["requirement"], "requirement")
                _string(criterion["note"], "note", nonempty=False)
                _enum(criterion["status"], "criterion status", {"supported", "partial", "gap", "unknown"})
                _strings(criterion["evidence"], "criterion evidence")
                if criterion["status"] in {"supported", "partial"} and not criterion["evidence"]:
                    raise StoreError("missing_evidence", "Supported/partial criteria need actual source paths")
                if not set(criterion["evidence"]).issubset(metadata.get("sources", [])):
                    raise StoreError("missing_evidence", "sources must include every criterion evidence path")
        if kind in {"learning-log", "work-log"} and "evidence_status" in metadata:
            _enum(metadata["evidence_status"], "evidence_status", {"record", "candidate", "confirmed"})
            if metadata["evidence_status"] == "confirmed" and not metadata.get("evidence_paths"):
                raise StoreError("missing_evidence", "Confirmed logs need actual evidence_paths")
        if kind == "plan":
            _enum(metadata["period"], "period", {"daily", "weekly", "monthly", "yearly"})
            if metadata["start_date"] > metadata["end_date"]:
                raise StoreError("metadata", "Plan end_date precedes start_date")
        if kind == "application":
            _enum(metadata["stage"], "stage", STAGES)
            _string(metadata["next_action"], "next_action", nonempty=False)
            if not isinstance(metadata["history"], list):
                raise StoreError("metadata", "Application history must be a list")
            dates = []
            for entry in metadata["history"]:
                if not isinstance(entry, dict) or not {"date", "stage", "note"}.issubset(entry):
                    raise StoreError("metadata", "History entries need date, stage and note")
                _date(entry["date"], "history date")
                _enum(entry["stage"], "history stage", STAGES)
                _string(entry["note"], "history note", nonempty=False)
                if "resume_ref" in entry and entry["resume_ref"] is not None:
                    self._resume_ref_syntax(entry["resume_ref"])
                dates.append(entry["date"])
            if dates != sorted(dates):
                raise StoreError("history", "Application history must be chronological")
            if dates and (metadata["stage"] != metadata["history"][-1]["stage"] or metadata["updated_on"] < dates[-1]):
                raise StoreError("history", "Current application stage/date must agree with final history entry")
        if kind == "photo-note":
            if not metadata["asset_path"].startswith("past/originals/photo/") and not is_material_path(metadata["asset_path"]):
                raise StoreError("metadata", "Photo must reference an imported photo original")

    @staticmethod
    def _source_paths(metadata):
        paths = list(metadata.get("sources", [])) if isinstance(metadata.get("sources", []), list) else []
        if isinstance(metadata.get("evidence_paths", []), list):
            paths += metadata.get("evidence_paths", [])
        if "asset_path" in metadata:
            paths.append(metadata["asset_path"])
        # source_revisions keys are declared source dependencies as well. The
        # validator requires them in sources, but deduplicate here so every
        # graph consumer follows exactly the same closure.
        if isinstance(metadata.get("source_revisions", {}), dict):
            paths.extend(metadata.get("source_revisions", {}))
        return list(dict.fromkeys(paths))

    @staticmethod
    def _resume_ref_syntax(reference):
        if not isinstance(reference, dict) or set(reference) != {"version", "artifact", "sha256"}:
            raise StoreError("resume_ref", "resume_ref needs exactly version, artifact and sha256, or null")
        version = reference["version"]
        if not isinstance(version, str) or "\\" in version or any(ord(c) < 32 for c in version):
            raise StoreError("resume_ref", "resume_ref.version must be a workspace-relative version directory")
        parts = version.split("/")
        if any(p in {"", ".", ".."} for p in parts) or not re.fullmatch(r"v-[0-9a-f]{32}", parts[-1]):
            raise StoreError("resume_ref", "resume_ref.version must identify an immutable v-<32 hex> directory")
        common = len(parts) == 6 and parts[:2] == ["future", "roles"] and parts[3:5] == ["common", "resumes"]
        company = len(parts) == 8 and parts[:2] == ["future", "roles"] and parts[3] == "companies" and parts[6] == "resumes"
        if not (common or company):
            raise StoreError("resume_ref", "resume_ref.version must belong to a role-common or company opportunity resumes/ directory")
        if not isinstance(reference["artifact"], str) or reference["artifact"] not in {"resume.html", "resume.pdf"}:
            raise StoreError("resume_ref", "resume_ref.artifact must be resume.html or resume.pdf")
        if not isinstance(reference["sha256"], str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", reference["sha256"]):
            raise StoreError("resume_ref", "resume_ref.sha256 must be sha256:<64 lowercase hex>")

    def _resume_ref(self, reference, metadata, records):
        self._resume_ref_syntax(reference)
        goals = [p for p, m in records.items() if m["type"] == "goal" and m.get("role_id", m["id"]) == metadata["role_id"]]
        if len(goals) != 1:
            raise StoreError("resume_ref", "A resume reference must identify one existing goal")
        base = PurePosixPath(goals[0]).parent
        version = PurePosixPath(reference["version"])
        common = base / "common" / "resumes"
        locations = {PurePosixPath(p).parent for p, m in records.items() if m["type"] in {"jd", "application"} and
                     all(m.get(k) == metadata[k] for k in ("role_id", "company_id", "opportunity_id"))}
        if version.parent != common and version.parent not in {p / "resumes" for p in locations}:
            raise StoreError("resume_ref_scope", "Resume version must belong to this role's common resume or this exact company opportunity")
        # Resume helper verifies frozen version manifest, exported PDF receipt,
        # file hashes and workspace ownership without rendering with new code.
        from md_resume import ResumeWorkspace
        manifest_path = reference["version"] + "/manifest.json"
        before = self._bytes(manifest_path)
        stored = read_json(self.path(manifest_path))
        expected_scope = {"role_id": metadata["role_id"], "company_id": None, "opportunity_id": None} if version.parent == common else {
            key: metadata[key] for key in ("role_id", "company_id", "opportunity_id")}
        if not isinstance(stored, dict) or stored.get("scope") != expected_scope:
            raise StoreError("resume_ref_scope", "Frozen resume scope does not match this application's role/company/opportunity")
        actual = ResumeWorkspace(self.root).artifact_ref(reference["version"], reference["artifact"])
        if self._bytes(manifest_path) != before:
            raise StoreError("conflict", "Resume version metadata changed during binding verification")
        if actual != reference:
            raise StoreError("resume_ref_changed", "Referenced resume artifact differs from its recorded hash")
        return actual

    def _pending(self):
        history = self.path(".luji/history")
        if not history.exists():
            return []
        result = []
        for folder in sorted(history.iterdir()):
            if folder.is_symlink():
                raise StoreError("unsafe_path", "History contains a symlink")
            journal = folder / "journal.json"
            if journal.exists():
                data = read_json(self.path(journal.relative_to(self.root).as_posix()))
                if not isinstance(data, dict) or data.get("state") not in {"prepared", "writing", "committed", "rolled_back", "recovery_conflict"} or not isinstance(data.get("files"), list):
                    raise StoreError("damaged_history", f"Invalid recovery journal: {journal}")
                if not isinstance(data.get("proposal_id"), str) or not re.fullmatch(r"p-[0-9a-f]{32}", data["proposal_id"]):
                    raise StoreError("damaged_history", f"Invalid proposal identity in recovery journal: {journal}")
                for entry in data["files"]:
                    if not isinstance(entry, dict) or set(entry) != {"path", "before_revision", "after_revision"}:
                        raise StoreError("damaged_history", f"Invalid file entry in recovery journal: {journal}")
                    self._canonical(entry["path"], allow_original=False)
                    for key in ("before_revision", "after_revision"):
                        revision = entry[key]
                        if not (key == "before_revision" and revision is None) and (not isinstance(revision, str) or not REV_RE.fullmatch(revision)):
                            raise StoreError("damaged_history", f"Invalid revision in recovery journal: {journal}")
                if data.get("state") not in {"committed", "rolled_back"}:
                    result.append((folder, data))
        return result

    def _assert_readable(self):
        pending = self._pending()
        if pending:
            raise StoreError("recovery_required", "An interrupted write needs recovery; apply its proposal again with confirmation", [j.get("proposal_id") for _, j in pending])

    def index(self, area=None, types=None):
        identity = self.manifest()
        self._assert_readable()
        if area is not None and area not in AREAS:
            raise StoreError("area", "area must be past, present or future")
        selected_types = {types} if isinstance(types, str) else set(types or [])
        if selected_types - TYPES:
            raise StoreError("type", f"Unknown types: {sorted(selected_types - TYPES)}")
        records, ids = [], {}
        for current_area in ([area] if area else sorted(AREAS)):
            start = self.path(current_area)
            if not start.is_dir():
                raise StoreError("missing_area", f"Workspace area is missing: {current_area}")
            for directory, folders, files in os.walk(start, followlinks=False):
                relative_dir = Path(directory).relative_to(self.root).as_posix()
                for name in folders + files:
                    if (Path(directory) / name).is_symlink():
                        raise StoreError("unsafe_path", f"Symlink in canonical area: {relative_dir}/{name}")
                folders[:] = sorted(name for name in folders if name != "resumes" and
                                    not (current_area == "past" and relative_dir == "past" and name == "originals") and
                                    not is_material_path(relative_dir + "/" + name + "/_"))
                for name in sorted(files):
                    if not name.endswith(".md"):
                        continue
                    relative = relative_dir + "/" + name
                    path = self.path(relative)
                    try:
                        with _open_regular(path) as stream:
                            first = stream.readline().decode("utf-8")
                            if first.rstrip("\r\n") != "---":
                                from md_navigation import owned_guide
                                if owned_guide(self.root, relative, identity["workspace_id"]):
                                    continue
                                raise StoreError("frontmatter", f"Missing frontmatter: {relative}")
                            header, size = [first], len(first.encode("utf-8"))
                            for raw_line in stream:
                                line = raw_line.decode("utf-8")
                                header.append(line)
                                size += len(line.encode("utf-8"))
                                if size > MAX_DOCUMENT_BYTES:
                                    raise StoreError("too_large", f"Frontmatter too large: {relative}")
                                if line.rstrip("\r\n") == "---":
                                    break
                        metadata, _ = parse_document("".join(header))
                    except (OSError, UnicodeError) as exc:
                        raise StoreError("read_failed", f"Cannot read Markdown {relative}: {exc}") from exc
                    self._metadata(metadata, relative)
                    if metadata["id"] in ids:
                        raise StoreError("duplicate_id", f"ID {metadata['id']} occurs in {ids[metadata['id']]} and {relative}")
                    ids[metadata["id"]] = relative
                    if not selected_types or metadata["type"] in selected_types:
                        records.append({"path": relative, "metadata": metadata})
        return {"workspace_id": identity["workspace_id"], "documents": records, "warnings": []}

    def read(self, paths):
        identity = self.manifest()
        self._assert_readable()
        if not isinstance(paths, (list, tuple)) or not all(isinstance(p, str) for p in paths):
            raise StoreError("paths", "read expects an explicit list of relative paths")
        documents, baselines = [], {}
        for relative in dict.fromkeys(paths):
            original = self._canonical(relative)
            raw = self._bytes(relative, missing=True)
            baselines[relative] = None if raw is None else digest(raw)
            if raw is None:
                continue
            if original:
                metadata = {"type": "source", "title": Path(relative).name}
                receipt_path = self.path(relative + ".receipt.json")
                if relative.startswith("past/originals/") and receipt_path.exists():
                    receipt = read_json(receipt_path)
                    if not isinstance(receipt, dict) or receipt.get("source_path") != relative:
                        raise StoreError("receipt", f"Invalid source receipt: {relative}")
                    metadata.update(receipt)
                    metadata["type"] = "source"
                documents.append({"path": relative, "metadata": metadata, "revision": digest(raw)})
            else:
                if len(raw) > MAX_DOCUMENT_BYTES:
                    raise StoreError("too_large", f"Markdown exceeds size limit: {relative}")
                try:
                    metadata, body = parse_document(raw.decode("utf-8"))
                except UnicodeError as exc:
                    raise StoreError("encoding", f"Markdown is not UTF-8: {relative}") from exc
                self._metadata(metadata, relative)
                documents.append({"path": relative, "metadata": metadata, "body": body, "revision": digest(raw)})
        return {"workspace_id": identity["workspace_id"], "documents": documents,
                "draft_base": {"workspace_id": identity["workspace_id"], "files": baselines}}

    def context(self, paths):
        """Read explicit targets and only their declared source lineage.

        Missing explicit targets are valid new-file baselines. A missing declared
        source is an error. Original files provide metadata and hashes, never a
        body. read() remains an exact-path primitive for callers needing no graph.
        """
        if not isinstance(paths, (list, tuple)) or not paths or not all(isinstance(p, str) for p in paths):
            raise StoreError("paths", "context expects one or more explicit relative paths")
        identity = self.manifest()
        requested = list(dict.fromkeys(paths))
        requested_set = set(requested)
        queue, queued = list(requested), set(requested)
        documents, files, source_paths, required_sources, edges = [], {}, [], set(), {}
        position = 0
        while position < len(queue):
            relative = queue[position]
            position += 1
            selected = self.read([relative])
            if selected["workspace_id"] != identity["workspace_id"]:
                raise StoreError("wrong_workspace", "Workspace identity changed while reading context")
            files.update(selected["draft_base"]["files"])
            documents.extend(selected["documents"])
            references = []
            if selected["documents"] and selected["documents"][0]["metadata"].get("type") != "source":
                metadata = selected["documents"][0]["metadata"]
                references = self._source_paths(metadata)
            edges[relative] = references
            for source in references:
                self._canonical(source)
                required_sources.add(source)
                if source not in queued:
                    queued.add(source)
                    queue.append(source)
                    if source not in requested_set:
                        source_paths.append(source)
        missing = sorted(source for source in required_sources if files[source] is None)
        if missing:
            raise StoreError("missing_source", "Declared context sources are missing; no complete draft baseline was returned", missing)
        # Iterative cycle detection also handles long manually edited lineages
        # without overflowing Python's call stack.
        done, active = set(), set()
        for first in queue:
            stack = [(first, False)]
            while stack:
                node, exiting = stack.pop()
                if exiting:
                    active.remove(node)
                    done.add(node)
                elif node not in done:
                    if node in active:
                        raise StoreError("source_cycle", f"Context source cycle includes {node}")
                    active.add(node)
                    stack.append((node, True))
                    stack.extend((child, False) for child in reversed(edges.get(node, [])))
        base = {"workspace_id": identity["workspace_id"], "files": files}
        self._assert_readable()
        self._verify_base(base)
        self._assert_readable()
        return {"workspace_id": identity["workspace_id"], "documents": documents,
                "draft_base": base, "requested_paths": requested, "source_paths": source_paths}

    def _graph(self, records, overrides=None):
        overrides = overrides or {}
        by_id = {}
        for relative, metadata in records.items():
            self._metadata(metadata, relative)
            if metadata["id"] in by_id:
                raise StoreError("duplicate_id", f"Duplicate ID: {metadata['id']}")
            by_id[metadata["id"]] = (relative, metadata)
        roles = {}
        for relative, metadata in records.items():
            if metadata["type"] == "goal":
                role = metadata.get("role_id", metadata["id"])
                if role in roles:
                    raise StoreError("duplicate_role", f"role_id {role} occurs in {roles[role]} and {relative}",
                                     {"role_id": role, "paths": [roles[role], relative]})
                roles[role] = relative
        for relative, metadata in records.items():
            for source in self._source_paths(metadata):
                self._canonical(source)
                if source == relative:
                    raise StoreError("source_cycle", f"A document cannot source itself: {relative}")
                if source not in overrides:
                    try:
                        with _open_regular(self.path(source)):
                            pass
                    except FileNotFoundError as exc:
                        raise StoreError("missing_source", f"File is missing: {source}") from exc
                    except OSError as exc:
                        raise StoreError("read_failed", f"Cannot read source {source}: {exc}") from exc
                if not source.startswith("past/originals/") and not is_material_path(source) and source not in records:
                    raise StoreError("missing_source", f"Source is not a canonical Markdown record: {source}")
            references = [(v, None) for v in metadata.get("related_ids", [])]
            references += [(v, "goal") for v in metadata.get("goal_ids", [])]
            references += [(v, "action") for v in metadata.get("action_ids", [])]
            references += [(v, "item") for v in metadata.get("item_ids", [])]
            references += [(v, "action") for v in metadata.get("depends_on", [])]
            for key, kind in (("goal_id", "goal"), ("item_id", "item")):
                if key in metadata:
                    references.append((metadata[key], kind))
            for target, kind in references:
                if target not in by_id or (kind and by_id[target][1]["type"] != kind):
                    raise StoreError("missing_reference", f"{relative} references missing {kind or 'document'} ID: {target}")
            if "role_id" in metadata and metadata["role_id"] not in roles:
                raise StoreError("missing_reference", f"Unknown role_id {metadata['role_id']} in {relative}")
            if metadata["type"] in INTERVIEW_TYPES:
                self._interview_scope(relative, metadata, records)
            if metadata["type"] == "assessment":
                for criterion in metadata["criteria"]:
                    if criterion["status"] not in {"supported", "partial"}:
                        continue
                    for evidence in criterion["evidence"]:
                        source = records.get(evidence, {})
                        if source.get("type") in {"note", "stage-summary"}:
                            raise StoreError("unconfirmed_evidence", f"Notes and stage reflections alone do not establish capability: {evidence}")
                        if source.get("type") in {"learning-log", "work-log"} and source.get("evidence_status") != "confirmed":
                            raise StoreError("unconfirmed_evidence", f"Activity logs alone do not establish capability: {evidence}")
        actions = {k: m.get("depends_on", []) for k, (_, m) in by_id.items() if m["type"] == "action"}
        self._acyclic(actions, "dependency_cycle")
        sources = {p: [s for s in self._source_paths(m) if s in records] for p, m in records.items()}
        self._acyclic(sources, "source_cycle")

    @staticmethod
    def _interview_scope(relative, metadata, records):
        """Resolve identity through existing records, never treating IDs as paths."""
        goals = [p for p, m in records.items() if m["type"] == "goal" and
                 m.get("role_id", m["id"]) == metadata["role_id"]]
        if len(goals) != 1:
            raise StoreError("invalid_scope", "Interview material needs exactly one goal for its role")
        goal = PurePosixPath(goals[0])
        base = goal.parent
        if goal.name != "goal.md" or len(base.parts) != 3 or base.parts[:2] != ("future", "roles"):
            raise StoreError("invalid_scope", "Interview role must use future/roles/<role>/goal.md")
        location = PurePosixPath(relative).parent
        if "company_id" not in metadata:
            expected = base / "common" / "interviews"
            if metadata["type"] == "interview-story":
                expected /= "stories"
        else:
            matches = [PurePosixPath(p).parent for p, m in records.items()
                       if m["type"] in {"jd", "application"} and
                       all(m.get(key) == metadata[key] for key in ("role_id", "company_id", "opportunity_id"))]
            parents = set(matches)
            if len(parents) != 1:
                raise StoreError("invalid_scope", "Interview company/opportunity must identify one existing JD/application folder")
            opportunity = parents.pop()
            if not opportunity.is_relative_to(base):
                raise StoreError("invalid_scope", "Interview opportunity must belong to the selected role")
            remainder = opportunity.relative_to(base).parts
            if len(remainder) != 3 or remainder[0] != "companies":
                raise StoreError("invalid_scope", "Interview opportunity must use <role>/companies/<company>/<opportunity>/")
            expected = opportunity / "interviews" / metadata["round_id"]
        if location != expected:
            raise StoreError("invalid_scope", "Interview material path belongs to a different role/company/opportunity/round: " + relative)

    @staticmethod
    def _acyclic(graph, code):
        done, active = set(), set()
        for first in graph:
            stack = [(first, False)]
            while stack:
                node, exiting = stack.pop()
                if exiting:
                    active.remove(node)
                    done.add(node)
                elif node not in done:
                    if node in active:
                        raise StoreError(code, f"Cycle includes {node}")
                    active.add(node)
                    stack.append((node, True))
                    stack.extend((child, False) for child in reversed(graph.get(node, [])))

    def _verify_base(self, base):
        identity = self.manifest()
        if not isinstance(base, dict) or base.get("workspace_id") != identity["workspace_id"] or not isinstance(base.get("files"), dict):
            raise StoreError("wrong_workspace", "Draft base must identify this workspace and its read file revisions")
        conflicts = []
        for relative, expected in base["files"].items():
            self._canonical(relative)
            if expected is not None and (not isinstance(expected, str) or not REV_RE.fullmatch(expected)):
                raise StoreError("base", f"Invalid base revision: {relative}")
            actual = self._revision(relative)
            if not _revision_equal(expected, actual):
                conflicts.append({"path": relative, "expected": expected, "actual": actual})
        if conflicts:
            raise StoreError("conflict", "Files changed since this draft was read; reread and prepare a new draft", conflicts)

    def _validate_draft(self, draft):
        if not isinstance(draft, dict):
            raise StoreError("draft", "Draft must be an object")
        _string(draft.get("title"), "draft title")
        writes = draft.get("writes")
        if not isinstance(writes, list) or not 1 <= len(writes) <= 100:
            raise StoreError("draft", "Draft needs 1..100 Markdown writes")
        self._verify_base(draft.get("base"))
        current = {d["path"]: d["metadata"] for d in self.index()["documents"]}
        resulting = copy.deepcopy(current)
        contents = {}
        for write in writes:
            if not isinstance(write, dict) or set(write) != {"path", "content"}:
                raise StoreError("draft", "Each write needs exactly path and full Markdown content")
            relative, content = write["path"], write["content"]
            self._canonical(relative, allow_original=False)
            if relative in contents:
                raise StoreError("draft", f"Repeated write path: {relative}")
            if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_DOCUMENT_BYTES:
                raise StoreError("draft", f"Invalid or oversized Markdown content: {relative}")
            if relative not in draft["base"]["files"]:
                raise StoreError("missing_base", f"Read before writing; missing baseline for {relative}")
            metadata, _ = parse_document(content)
            self._metadata(metadata, relative)
            old = current.get(relative)
            if old:
                for key in ("id", "type", "role_id", "company_id", "opportunity_id"):
                    if key in old and metadata.get(key) != old[key]:
                        raise StoreError("identity_change", f"Stable {key} cannot change on {relative}")
                if old["type"] in INTERVIEW_TYPES and old.get("round_id") != metadata.get("round_id"):
                    raise StoreError("identity_change", f"Stable round_id cannot change on {relative}")
                if not set(old.get("sources", [])).issubset(metadata.get("sources", [])):
                    raise StoreError("source_history", f"Keep prior sources when updating {relative}")
                if old["type"] == "application" and metadata.get("history", [])[:len(old["history"])] != old["history"]:
                    raise StoreError("history", f"Application history is append-only: {relative}")
            for source in self._source_paths(metadata):
                if source not in draft["base"]["files"]:
                    raise StoreError("missing_base", f"Draft must include revision of used source: {source}")
            resulting[relative] = metadata
            contents[relative] = content.encode("utf-8")
        # A selected source may itself depend on an original or a current log's
        # artifact. Freeze that actual used lineage, without reading other bodies.
        used = set()
        def include_sources(relative):
            if relative in used:
                return
            used.add(relative)
            if relative not in draft["base"]["files"]:
                raise StoreError("missing_base", f"Draft must include revision of used source: {relative}")
            for source in self._source_paths(resulting.get(relative, {})):
                include_sources(source)
        for relative in contents:
            include_sources(relative)
        self._graph(resulting, contents)
        for relative in contents:
            metadata = resulting[relative]
            if metadata["type"] in {"note", "stage-summary"}:
                old_revisions = current.get(relative, {}).get("source_revisions", {})
                for source, revision in metadata.get("source_revisions", {}).items():
                    # Preserve an unchanged historical citation when editing a
                    # note. New/revised citations must match the reviewed bytes.
                    if old_revisions.get(source) != revision:
                        actual = digest(contents[source]) if source in contents else draft["base"]["files"].get(source)
                        if not _revision_equal(revision, actual):
                            raise StoreError("conflict", f"New source revision does not match reviewed bytes: {source}")
            if metadata["type"] == "application":
                previous = current.get(relative, {}).get("history", [])
                for event in metadata["history"][len(previous):]:
                    if event.get("resume_ref") is not None:
                        self._resume_ref(event["resume_ref"], metadata, resulting)
        return contents

    @contextlib.contextmanager
    def _lock(self):
        self.manifest()
        lock = self.path(".luji/write.lock")
        lock.parent.mkdir(parents=True, exist_ok=True)
        unlock = None
        try:
            import fcntl
        except ImportError:
            fcntl = None
            try:
                import msvcrt
            except ImportError as exc:
                raise StoreError("unsupported_lock", "Canonical writes require POSIX flock or Windows msvcrt locking") from exc
        fd = os.open(lock, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            try:
                if fcntl is not None:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                else:
                    # msvcrt locks byte ranges, including a stable first byte.
                    if os.fstat(fd).st_size == 0:
                        os.write(fd, b"\0")
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    def unlock():
                        os.lseek(fd, 0, os.SEEK_SET)
                        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            except OSError as exc:
                import errno
                if isinstance(exc, BlockingIOError) or exc.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise StoreError("locked", "Another workspace write is in progress") from exc
                raise StoreError("lock_failed", f"Cannot lock workspace: {exc}") from exc
            yield
        finally:
            if unlock is not None:
                with contextlib.suppress(OSError):
                    unlock()
            os.close(fd)

    def propose(self, draft):
        with self._lock():
            self._recover_pending()
            self._validate_draft(draft)
            proposal_id = "p-" + uuid.uuid4().hex
            result = {"status": "pending", "proposal_id": proposal_id,
                      "created_at": dt.datetime.now(dt.timezone.utc).isoformat(), "draft": copy.deepcopy(draft)}
            atomic_write(self.path(f".luji/proposals/{proposal_id}.json"), json_bytes(result))
            return result

    def _rollback(self, folder, journal):
        conflicts = []
        for entry in reversed(journal["files"]):
            relative = entry["path"]
            self._canonical(relative, allow_original=False)
            actual = self._revision(relative)
            if _revision_equal(actual, entry["before_revision"]):
                continue
            if not _revision_equal(actual, entry["after_revision"]):
                conflicts.append(relative)
                continue
            if entry["before_revision"] is None:
                self.path(relative).unlink()
                _sync_dir(self.path(relative).parent)
            else:
                backup = self.path(folder.relative_to(self.root).as_posix() + "/before/" + relative)
                raw = backup.read_bytes()
                if digest(raw) != entry["before_revision"]:
                    raise StoreError("recovery_conflict", f"History backup is damaged: {relative}")
                atomic_write(self.path(relative), raw)
        journal["state"] = "recovery_conflict" if conflicts else "rolled_back"
        atomic_write(self.path(folder.relative_to(self.root).as_posix() + "/journal.json"), json_bytes(journal))
        if conflicts:
            raise StoreError("recovery_conflict", "External edits were preserved; inspect the interrupted transaction before retrying", conflicts)

    def _recover_pending(self):
        for folder, journal in self._pending():
            self._rollback(folder, journal)

    def apply(self, proposal_id, confirmed=False):
        if confirmed is not True:
            raise StoreError("confirmation_required", "Show this concrete draft and obtain explicit confirmation before applying it")
        if not isinstance(proposal_id, str) or not re.fullmatch(r"p-[0-9a-f]{32}", proposal_id):
            raise StoreError("proposal", "Invalid proposal ID")
        with self._lock():
            self._recover_pending()
            proposal_path = self.path(f".luji/proposals/{proposal_id}.json")
            proposal = read_json(proposal_path)
            if not isinstance(proposal, dict) or proposal.get("proposal_id") != proposal_id:
                raise StoreError("proposal", "Proposal identity mismatch")
            history = self.path(f".luji/history/{proposal_id}")
            journal_path = self.path(f".luji/history/{proposal_id}/journal.json")
            if proposal.get("status") == "applied":
                return dict(proposal["result"], status="already_applied")
            # A crash can occur after a retry committed but before the proposal
            # marker was saved. Search every retained attempt before retrying.
            for folder in sorted(self.path(".luji/history").iterdir()):
                if folder.name != proposal_id and not folder.name.startswith(proposal_id + "-retry-"):
                    continue
                candidate = self.path(folder.relative_to(self.root).as_posix() + "/journal.json")
                if candidate.exists():
                    committed = read_json(candidate)
                    if committed.get("state") == "committed" and committed.get("proposal_id") == proposal_id:
                        proposal.update(status="applied", result=committed["result"])
                        atomic_write(proposal_path, json_bytes(proposal))
                        return dict(committed["result"], status="already_applied")
            if journal_path.exists():
                previous = read_json(journal_path)
                if previous.get("state") == "committed":
                    proposal.update(status="applied", result=previous["result"])
                    atomic_write(proposal_path, json_bytes(proposal))
                    return dict(previous["result"], status="already_applied")
                if previous.get("state") == "rolled_back":
                    # Retain recovered history; a new attempt uses a fresh history directory.
                    history = self.path(f".luji/history/{proposal_id}-retry-{uuid.uuid4().hex[:8]}")
                    journal_path = history / "journal.json"
            contents = self._validate_draft(proposal["draft"])
            base = proposal["draft"]["base"]
            history.mkdir(parents=True, exist_ok=True)
            history_relative = history.relative_to(self.root).as_posix()
            for relative, expected in base["files"].items():
                raw = self._bytes(relative, missing=True)
                if not _revision_equal(None if raw is None else digest(raw), expected):
                    raise StoreError("conflict", f"Source changed while staging: {relative}")
                if raw is not None:
                    atomic_write(self.path(history_relative + "/baseline/" + relative), raw)
            entries = []
            for relative, content in contents.items():
                before = self._bytes(relative, missing=True)
                if before is not None:
                    atomic_write(self.path(history_relative + "/before/" + relative), before)
                atomic_write(self.path(history_relative + "/after/" + relative), content)
                entries.append({"path": relative, "before_revision": None if before is None else digest(before), "after_revision": digest(content)})
            journal = {"state": "prepared", "proposal_id": proposal_id, "files": entries, "base": base}
            atomic_write(journal_path, json_bytes(journal))
            try:
                self._verify_base(base)
                journal["state"] = "writing"
                atomic_write(journal_path, json_bytes(journal))
                for entry in entries:
                    relative = entry["path"]
                    if not _revision_equal(self._revision(relative), entry["before_revision"]):
                        raise StoreError("conflict", f"File changed during apply: {relative}")
                    atomic_write(self.path(relative), contents[relative])
                for relative, expected in base["files"].items():
                    wanted = digest(contents[relative]) if relative in contents else expected
                    if not _revision_equal(self._revision(relative), wanted):
                        raise StoreError("conflict", f"File changed during apply: {relative}")
                result = {"status": "applied", "proposal_id": proposal_id,
                          "changed_paths": list(contents), "revision": digest(json_bytes({p: digest(v) for p, v in contents.items()}))}
                journal.update(state="committed", result=result)
                atomic_write(journal_path, json_bytes(journal))
            except Exception as exc:
                try:
                    self._rollback(history, journal)
                except Exception as recovery:
                    raise StoreError("recovery_required", "Apply failed and recovery needs attention; no success was reported", {"error": str(exc), "recovery": str(recovery), "proposal_id": proposal_id}) from recovery
                if isinstance(exc, StoreError):
                    raise
                raise StoreError("apply_failed", "Apply failed; canonical changes were rolled back", str(exc)) from exc
            proposal.update(status="applied", result=result)
            atomic_write(proposal_path, json_bytes(proposal))
            return result

    def import_source(self, file, kind="reference"):
        _enum(kind, "source kind", SOURCE_KINDS)
        supplied = Path(file).expanduser()
        if supplied.is_symlink():
            raise StoreError("unsafe_source", "Import an actual regular file, not a symlink")
        try:
            with _open_regular(supplied) as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_SOURCE_BYTES:
                    raise StoreError("unsafe_source", "Source must be a regular file at most 50 MiB")
                raw = stream.read(MAX_SOURCE_BYTES + 1)
            if len(raw) > MAX_SOURCE_BYTES:
                raise StoreError("unsafe_source", "Source exceeds 50 MiB")
        except OSError as exc:
            raise StoreError("read_failed", f"Cannot import supplied file: {exc}") from exc
        extension = supplied.suffix.lower()
        if not re.fullmatch(r"\.[a-z0-9]{1,12}", extension):
            extension = ".bin"
        source = f"past/originals/{kind}/source-{uuid.uuid4().hex}{extension}"
        receipt = {"source_path": source, "sha": digest(raw), "original_name": supplied.name,
                   "kind": kind, "bytes": len(raw), "imported_at": dt.datetime.now(dt.timezone.utc).isoformat()}
        with self._lock():
            self._recover_pending()
            atomic_write(self.path(source), raw)
            try:
                atomic_write(self.path(source + ".receipt.json"), json_bytes(receipt))
            except Exception:
                self.path(source).unlink()
                raise
        return receipt

    def _warnings(self, records):
        warnings = []
        for relative, metadata in records.items():
            if metadata["type"] not in {"portrait", "assessment", "check", "note", "stage-summary"} | INTERVIEW_TYPES:
                continue
            missing, changed = [], []
            for source in metadata.get("sources", []):
                expected = metadata.get("source_revisions", {}).get(source)
                if expected is None:
                    missing.append(source)
                elif not _revision_equal(expected, self._revision(source)):
                    changed.append(source)
            if missing:
                warnings.append({"code": "untracked_sources", "path": relative, "sources": missing,
                                 "message": "Source revisions were not recorded; this interpretation needs freshness review"})
            if changed:
                warnings.append({"code": "stale_sources", "path": relative, "sources": changed,
                                 "message": "Sources changed or disappeared; reevaluation is needed"})
        return warnings

    def validate(self):
        identity, records, warnings = {}, {}, []
        try:
            identity = self.manifest()
            records = {d["path"]: d["metadata"] for d in self.index()["documents"]}
            # A requested full validation also verifies body encoding/readability;
            # index itself deliberately never reads those bodies.
            documents = self.read(list(records))["documents"]
            if {d["path"] for d in documents} != set(records):
                raise StoreError("conflict", "Documents disappeared during validation; reread the workspace")
            records = {d["path"]: d["metadata"] for d in documents}
            warnings = self._warnings(records)
            self._graph(records)
            for relative, metadata in records.items():
                if metadata["type"] == "application":
                    for pos, event in enumerate(metadata["history"]):
                        if event.get("resume_ref") is not None:
                            try:
                                self._resume_ref(event["resume_ref"], metadata, records)
                            except StoreError as exc:
                                warnings.append({"code": "resume_reference_unavailable", "path": relative,
                                                 "history_index": pos, "resume_ref": event["resume_ref"],
                                                 "reason": exc.as_dict(), "message": "Historical binding preserved; inspect before reusing this artifact"})
            return {"ok": True, "workspace_id": identity["workspace_id"], "documents_count": len(records), "warnings": warnings}
        except StoreError as exc:
            return {"ok": False, "workspace_id": identity.get("workspace_id"), "documents_count": len(records),
                    "warnings": warnings, "errors": [exc.as_dict()]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--language", choices=("zh", "en"), default="zh")
    init.add_argument("--skill-root")
    index = commands.add_parser("index")
    index.add_argument("--area", choices=sorted(AREAS))
    index.add_argument("--type", action="append", dest="types")
    read = commands.add_parser("read")
    read.add_argument("--path", action="append", required=True)
    context = commands.add_parser("context")
    context.add_argument("--path", action="append", required=True)
    source = commands.add_parser("import-source")
    source.add_argument("file")
    source.add_argument("--kind", default="reference", choices=sorted(SOURCE_KINDS))
    propose = commands.add_parser("propose")
    propose.add_argument("--file", required=True)
    apply = commands.add_parser("apply")
    apply.add_argument("id")
    apply.add_argument("--confirmed", action="store_true")
    commands.add_parser("validate")
    args = parser.parse_args(argv)
    try:
        workspace = Workspace(args.workspace)
        if args.command == "init":
            result = workspace.initialize(args.language, args.skill_root)
        elif args.command == "index":
            result = workspace.index(args.area, args.types)
        elif args.command == "read":
            result = workspace.read(args.path)
        elif args.command == "context":
            result = workspace.context(args.path)
        elif args.command == "import-source":
            result = workspace.import_source(args.file, args.kind)
        elif args.command == "propose":
            result = workspace.propose(read_json(Path(args.file)))
        elif args.command == "apply":
            result = workspace.apply(args.id, args.confirmed)
        else:
            result = workspace.validate()
        sys.stdout.buffer.write(json_bytes(result))
        return 0 if result.get("ok", True) else 1
    except StoreError as exc:
        sys.stderr.buffer.write(json_bytes({"ok": False, "error": exc.as_dict()}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
