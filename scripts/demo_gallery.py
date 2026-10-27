#!/usr/bin/env python3
"""Build an offline résumé gallery using only bundled fictional demo material.

Each avatar has its own isolated fixture. Preview layouts are derived files,
not additional résumé versions in those fixtures or changes to a user workspace.
"""
from __future__ import annotations

import argparse
from datetime import date as Date
import json
import os
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import urlparse

from demo import run as build_demo
from md_workspace import StoreError, Workspace
from resume_layout import PRINT_SCRIPT, TEMPLATES, read_photo, render_html

PACKAGE = Path(__file__).resolve().parents[1]
AVATARS = ("a", "b", "none")
AVATAR_ASSETS = {"a": "demo-avatar.png", "b": "demo-avatar-b.png"}
DESCRIPTIONS = {
    "profile-split": "简介、教育与技能在侧栏，主栏保留完整经历。",
    "classic-single": "正式单栏与细线分区，适合顺序阅读和打印。",
    "evidence-archive": "窄标题栏与清晰分区，突出经历的结构和依据。",
    "ats-minimal": "克制的文本排版，适合偏好少装饰的使用者。",
    "project-first": "优先展示项目，把作品与实践放到读者面前。",
    "experience-first": "优先展开工作经历，适合已有连续职业积累的人。",
}
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _https(value, field):
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an HTTPS URL.")
    parsed = urlparse(value)
    if (parsed.scheme != "https" or not parsed.hostname
            or parsed.username or parsed.password
            or any(ord(ch) < 32 for ch in value)):
        raise ValueError(f"{field} must be an HTTPS URL without credentials.")
    return parsed


def load_references(path):
    """Read a small public link catalog; never retrieve its external URLs."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("items"), list):
        raise ValueError("The reference catalog needs an items list.")
    if not 1 <= len(value["items"]) <= 30:
        raise ValueError("The reference catalog must have 1–30 entries.")
    seen = set()
    for item in value["items"]:
        if not isinstance(item, dict):
            raise ValueError("Each reference must be an object.")
        identifier = item.get("id")
        if not isinstance(identifier, str) or not ID_RE.fullmatch(identifier) or identifier in seen:
            raise ValueError("Reference IDs must be unique simple slugs.")
        seen.add(identifier)
        for key in ("title", "usage", "license"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f"Reference {identifier} needs {key}.")
        repo = _https(item.get("repo_url"), "repo_url")
        if repo.hostname != "github.com" or len(repo.path.strip("/").split("/")) != 2:
            raise ValueError("Reference repositories must be GitHub repository URLs.")
        _https(item.get("license_url"), "license_url")
        for key, url in item.items():
            if key.endswith("_url") and url is not None:
                _https(url, key)
    return value["items"]


def json_for_html(value):
    """Keep untrusted catalog text inside its JSON script element."""
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            .replace("&", "\\u0026").replace("<", "\\u003c")
            .replace(">", "\\u003e").replace("\u2028", "\\u2028")
            .replace("\u2029", "\\u2029"))


def render_gallery(template, payload):
    if template.count("__GALLERY_DATA__") != 1:
        raise ValueError("Gallery template must contain one data placeholder.")
    return template.replace("__GALLERY_DATA__", json_for_html(payload))


def embedded_preview(page):
    """A sandboxed style sample has no controls requiring disabled scripts.

    Only this derived copy changes. The full sample and registered resume
    versions keep their original print control and byte-level provenance.
    """
    text = page.decode("utf-8")
    text, count = re.subn(r'<div class="tools">.*?</div>', "", text, count=1, flags=re.S)
    if count != 1 or text.count('<script>' + PRINT_SCRIPT + '</script>') != 1:
        raise ValueError("Resume preview toolbar changed; update its sandbox adapter explicitly.")
    return text.replace('<script>' + PRINT_SCRIPT + '</script>', "").encode("utf-8")


def _new_destination(value):
    supplied = Path(value).absolute()
    # lexists also refuses dangling symlinks, without listing existing contents.
    if os.path.lexists(supplied):
        raise ValueError("Gallery output must be a new, nonexistent directory.")
    # Match Workspace's root canonicalization, including normal OS aliases such
    # as macOS /var -> /private/var. The canonical destination must also be new.
    destination = supplied.resolve()
    if os.path.lexists(destination):
        raise ValueError("Gallery output must be a new, nonexistent directory.")
    return destination


def run(output, date="2026-10-27"):
    destination = _new_destination(output)
    Date.fromisoformat(date)
    references = load_references(PACKAGE / "references/resume-samples.json")
    template = (PACKAGE / "assets/resume_gallery.html").read_text(encoding="utf-8")
    if template.count("__GALLERY_DATA__") != 1:
        raise ValueError("Gallery template must contain one data placeholder.")
    # Fail before creating output if a bundled avatar is absent or invalid.
    for filename in AVATAR_ASSETS.values():
        read_photo(PACKAGE / "assets" / filename)
    if set(TEMPLATES) != set(DESCRIPTIONS) or not all(ID_RE.fullmatch(key) for key in TEMPLATES):
        raise ValueError("Gallery descriptions must match the fixed template IDs.")

    destination.mkdir(parents=True, exist_ok=False)
    (destination / "avatars").mkdir()
    for avatar, filename in AVATAR_ASSETS.items():
        shutil.copyfile(PACKAGE / "assets" / filename, destination / "avatars" / f"{avatar}.png")

    previews = []
    fixture_validation = {}
    for avatar in AVATARS:
        fixture = destination / "fixtures" / avatar
        report = build_demo(fixture, date, avatar=avatar)
        fixture_validation[avatar] = report["validation"]
        if not report["validation"]["ok"] or report["validation"]["warnings"]:
            raise ValueError(f"Fictional fixture {avatar} did not validate cleanly.")
        ws = Workspace(fixture)
        common = ws.path(report["resumes"]["common"])
        content = json.loads((common / "content.json").read_text(encoding="utf-8"))
        manifest = json.loads((common / "manifest.json").read_text(encoding="utf-8"))
        photos = [name for name in manifest["files"] if name.startswith("photo.")]
        if len(photos) != (0 if avatar == "none" else 1):
            raise ValueError(f"Fixture {avatar} has an unexpected photo count.")
        photo_name, photo_raw = read_photo(common / photos[0]) if photos else (None, None)
        folder = destination / "previews" / avatar
        folder.mkdir(parents=True)
        (destination / "embedded-previews" / avatar).mkdir(parents=True)
        for identifier in TEMPLATES:
            relative = f"previews/{avatar}/{identifier}.html"
            page = render_html(content, identifier, manifest["source_revisions"], photo_name, photo_raw)
            (destination / relative).write_bytes(page)
            (destination / "embedded-previews" / avatar / f"{identifier}.html").write_bytes(embedded_preview(page))
            previews.append(relative)

    payload = {
        "default_template": "profile-split", "default_avatar": "a", "generated_on": date,
        "templates": [{"id": key, "name": name, "description": DESCRIPTIONS[key],
                       "variants": {avatar: f"previews/{avatar}/{key}.html" for avatar in AVATARS},
                       "embedded_variants": {avatar: f"embedded-previews/{avatar}/{key}.html" for avatar in AVATARS}}
                      for key, name in TEMPLATES.items()],
        "avatars": [{"id": "a", "name": "头像 A", "thumbnail": "avatars/a.png"},
                    {"id": "b", "name": "头像 B", "thumbnail": "avatars/b.png"},
                    {"id": "none", "name": "不放头像", "thumbnail": None}],
        "references": references, "workbench_url": "fixtures/a/views/overview.html",
    }
    index = destination / "index.html"
    index.write_text(render_gallery(template, payload), encoding="utf-8")
    return {
        "status": "generated_not_opened", "fictional_only": True,
        "simulated_confirmations": True, "index": str(index),
        "templates": len(TEMPLATES), "avatar_options": list(AVATARS),
        "preview_count": len(previews), "previews": previews,
        "embedded_preview_count": len(previews),
        "reference_count": len(references), "fixture_validation": fixture_validation,
        "note": "Layout previews only; formal demo versions remain one common and one company version per isolated fixture.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="A new, nonexistent gallery directory")
    parser.add_argument("--date", default="2026-10-27")
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.output, args.date), ensure_ascii=False, indent=2))
    except (ValueError, StoreError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
