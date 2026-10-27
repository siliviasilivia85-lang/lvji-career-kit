#!/usr/bin/env python3
"""Export a portable, fictional, read-only demo site; never publish a workspace.

Private fixtures are built in a temporary directory and destroyed. Only explicit
HTML pages and the bundled fictional avatars enter the output. No model,
network, personal workspace, deployment account or browser is used.
"""
from __future__ import annotations

import argparse
from datetime import date as Date, timedelta
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile
from urllib.parse import unquote, urlsplit

from demo_gallery import (AVATARS, AVATAR_ASSETS, DESCRIPTIONS, embedded_preview,
                          load_references, render_gallery, run as build_gallery)
from md_views import build_snapshot
from md_workspace import StoreError, Workspace
from resume_layout import TEMPLATES

PACKAGE = Path(__file__).resolve().parents[1]
DEMO_DATE = "2030-04-12"  # A fictional Friday, not the build or validation date.
VIEWS = {"overview": "总览", "plan": "统一计划", "roles": "所向", "applications": "投递进展"}
STATUS = {"todo": "待开始", "doing": "进行中", "done": "已完成", "paused": "已暂停"}
STAGES = {"researching": "了解中", "preparing": "准备中", "applied": "已投递",
          "screening": "筛选中", "interview": "面试中", "offer": "收到 Offer", "closed": "已结束"}


def new_destination(value):
    supplied = Path(value).expanduser().absolute()
    if os.path.lexists(supplied):
        raise ValueError("Demo output must be a new, nonexistent directory.")
    for part in supplied.parents:
        if part.is_symlink() and not (str(part), str(part.resolve())) in {
                ("/tmp", "/private/tmp"), ("/var", "/private/var")}:
            raise ValueError("Demo output cannot traverse a symlink.")
    destination = supplied.resolve()
    if os.path.lexists(destination):
        raise ValueError("Demo output must be a new, nonexistent directory.")
    if not destination.parent.is_dir():
        raise ValueError("The demo output parent directory must already exist.")
    return destination


def source_name(path):
    return sha256(path.encode("utf-8")).hexdigest()[:24] + ".html"


def _style():
    markup = (PACKAGE / "assets/md_workspace.html").read_text(encoding="utf-8")
    found = re.findall(r"<style>([\s\S]*?)</style>", markup)
    if len(found) != 1:
        raise ValueError("Workspace CSS changed; update the public adapter explicitly.")
    return found[0]


def _link(label, target, kind=""):
    return '<a' + (' class="' + kind + '"' if kind else "") + ' href="' + escape(target, quote=True) + '">' + escape(label) + '</a>'


def _page(title, body, *, location="index.html", view=None):
    depth = len(PurePosixPath(location).parts) - 1
    back = "../" * depth
    nav = '<nav class="demo-nav" aria-label="演示导航">'
    nav += _link("对话示例", back + "index.html") + _link("工作台", back + "workbench/overview.html") + _link("简历样式", back + "gallery/index.html") + '</nav>'
    if view:
        body = '<nav class="demo-nav" aria-label="工作区视图">' + ''.join(
            '<a href="' + key + '.html"' + (' aria-current="page"' if key == view else '') + '>' + value + '</a>'
            for key, value in VIEWS.items()) + '</nav><div style="margin-top:24px">' + body + '</div>'
    template = (PACKAGE / "assets/demo_intro.html").read_text(encoding="utf-8")
    for key, value in {"__DEMO_TITLE__": escape(title), "__DEMO_STYLE__": _style(), "__DEMO_NAV__": nav, "__DEMO_BODY__": body}.items():
        if template.count(key) != 1:
            raise ValueError("Demo page needs exactly one " + key)
        template = template.replace(key, value)
    return template


def _record_link(doc, prefix="../"):
    return _link(doc["metadata"]["title"], prefix + "records/" + source_name(doc["path"]))


def _list_records(documents, empty="尚无记录。"):
    if not documents:
        return '<p class="small muted">' + empty + '</p>'
    return '<ul class="demo-record-list">' + ''.join('<li>' + _record_link(d) + '</li>' for d in documents) + '</ul>'


def _card(doc, detail=None):
    m = doc["metadata"]
    return '<article class="demo-card"><h3>' + _record_link(doc) + '</h3>' + (
        '<p class="small muted">' + escape(detail) + '</p>' if detail else '') + '<p class="demo-reading">' + escape(doc.get("body", "")) + '</p></article>'


def _overview(snapshot):
    facts = [d for d in snapshot["documents"] if d["path"].startswith("past/")]
    return '<div class="section-head"><div><h1>从眼前的一步继续</h1><p class="muted">把一次谈话，留下为可以继续的积累。</p></div></div><div class="demo-facts"><section><h2>正在推进</h2>' + ''.join(
        _card(d, STATUS.get(d["metadata"].get("status"), "")) for d in snapshot["items"]) + '</section><section><h2>最近留下的成果</h2>' + ''.join(
        _card(d, "虚构成果记录 · 完成任务与确认能力分别处理") for d in snapshot["logs"]) + '</section></div><details class="demo-source"><summary>来路与当前理解</summary>' + _list_records(facts) + '</details>'


def _plan(snapshot):
    anchor = Date.fromisoformat(snapshot["as_of"])
    start = anchor - timedelta(days=anchor.weekday())
    days = []
    for offset in range(7):
        date = (start + timedelta(days=offset)).isoformat()
        actions = [d for d in snapshot["actions"] if d["metadata"].get("scheduled_for") == date]
        content = ''.join('<article>' + _record_link(d) + '<p class="small muted">' + escape(STATUS[d["metadata"]["status"]]) + ' · ' + str(d["metadata"].get("minutes", 0)) + ' 分钟</p></article>' for d in actions)
        days.append('<section class="demo-day"><h3>' + ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][offset] + ' · ' + date[5:] + '</h3>' + (content or '<p class="small muted">留白</p>') + '</section>')
    return '<h1>把准备放进真实的一周</h1><p class="muted">示例用户每周可投入五小时；三项行动共300分钟。这里展示固定虚构周计划，不支持在线改期或保存。</p><div class="demo-week">' + ''.join(days) + '</div><details class="demo-source"><summary>同一行动在日、周、月、年里的安排</summary>' + _list_records(snapshot["plans"]) + '</details>'


def _roles(snapshot, resumes):
    cards = []
    for role in snapshot["roles"]:
        count = role["counts"]
        counts = '支持 ' + str(count["supported"]) + ' · 部分支持 ' + str(count["partial"]) + ' · 缺口 ' + str(count["gap"]) + ' · 未知 ' + str(count["unknown"])
        related = [d for d in snapshot["documents"] if d["metadata"].get("role_id") == role["id"] and d["metadata"]["type"] in {"jd", "assessment", "interview-story", "interview-prep"}]
        cards.append('<article class="demo-card"><h2>' + _record_link(role["goal"]) + '</h2><p class="muted">' + escape(counts if role["assessment"] else '资料还不充分，尚未评估；未知不等于不匹配。') + '</p>' + _list_records(related) + '</article>')
    return '<h1>可以靠近的方向</h1><p class="muted">要求、证据、信息充分度与个人偏好分开看；这些判断不是录用概率。</p><div class="demo-facts">' + ''.join(cards) + '</div><section class="demo-source"><h2>已有的示例简历</h2><p class="small muted">只是可查看的虚构版本，不代表已实际发送。</p>' + ''.join('<p>' + _link(label, '../' + path) + '</p>' for label, path in resumes) + '</section>'


def _applications(snapshot):
    cards = []
    for doc in snapshot["applications"]:
        m = doc["metadata"]
        history = ''.join('<li><strong>' + escape(STAGES.get(h["stage"], h["stage"])) + '</strong> · ' + escape(h["note"]) + '</li>' for h in m["history"])
        feedback = [d for d in snapshot["documents"] if d["metadata"]["type"] == "feedback" and d["metadata"].get("company_id") == m["company_id"]]
        cards.append('<article class="demo-card"><h2>' + _record_link(doc) + '</h2><p><span class="pill">' + escape(STAGES[m["stage"]]) + '</span></p><p>下一步：' + escape(m["next_action"]) + '</p><details><summary>已记录的虚构节点</summary><ol>' + history + '</ol><p class="small muted">本例未记录实际用版，不能推断为最新简历。</p></details>' + _list_records(feedback, "尚无反馈。") + '</article>')
    return '<h1>每次反馈，都带回一个下一步</h1><p class="muted">公司与机会各自留档。演示中的节点是固定编排，不进行真实投递或联系招聘方。</p><div class="demo-facts">' + ''.join(cards) + '</div>'


def _intro(snapshot):
    by_id = {d["metadata"]["id"]: d for d in snapshot["documents"]}
    scenes = [
        ("01 / 过去 · 先找回已有的积累", "这是我之前的简历和学习计划，帮我整理一下。", "我会保留原件，拆出工作、项目和学习记录。旧计划里没做过的事，不会写成已经具备的能力。", "查看整理后的经历", "records/" + source_name(by_id["project-search"]["path"])),
        ("02 / 未来 · 方向可以慢慢形成", "我想探索 AI 产品经理，但还没有想清楚。", "先讨论你喜欢怎样的工作，再比较要求和已有证据。方向可以保留探索状态，也可以先只存一个想法，不急着排满日程。", "看方向与依据", "workbench/roles.html"),
        ("03 / 现在 · 放进能做到的一周", "我本周只能拿出五小时，该先做什么？", "把检索评估作品拆成样本、错误归因和说明三步，共五小时。先看这份具体安排，你确认后再保存；其他目标先留白。", "看固定虚构周计划", "workbench/plan.html"),
        ("04 / 回流 · 把结果带到下一次选择", "我完成了样本记录，也收到了初筛反馈。", "先核对真实产出支持什么，再用于简历和面试。反馈留在对应机会里，并带回下一步准备；任务完成本身不等于能力已经被证明。", "看机会、准备与反馈", "workbench/applications.html"),
    ]
    body = '<section id="demo-hero" class="demo-hero"><p class="eyebrow">A career that keeps growing.</p><h1>让你的 Agent，成为长期职业发展顾问。</h1><p class="muted">从走过的路找到线索，把未来的可能放进今天，再把每一次实践留下来。</p><p id="demo-loop" class="demo-summary" aria-label="职业顾问协作过程"><span class="pill">聊清方向</span><span aria-hidden="true">→</span><span class="pill">拆成行动</span><span aria-hidden="true">→</span><span class="pill">留下积累</span></p><div class="demo-ctas">' + _link("看一段对话如何留下积累", "#conversation", "button") + _link("打开示例工作台", "workbench/overview.html", "button") + '</div></section><section id="conversation" class="demo-flow" aria-label="编排的对话示例">'
    for index, (title, user, agent, label, href) in enumerate(scenes):
        identifier = ("step-past", "step-future", "step-present", "step-feedback")[index]
        body += '<article id="' + identifier + '" class="demo-scene"><h2 class="scene-label">' + title + '</h2><div class="dialogue"><span class="speaker">你</span><p>' + escape(user) + '</p><span class="speaker">Agent</span><p>' + escape(agent) + '</p></div><p class="scene-result">这一步可以留下：' + _link(label, href) + '</p></article>'
    return body + '</section><p class="small muted" style="margin-top:22px">上方是使用方式的编排示例，不是在线聊天服务或真实用户对话。安装 Skill 后，实际讨论、材料理解和执行由你使用的 Agent 完成。</p>'


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def public_snapshot(snapshot, ws):
    """Use stable bundled-source names, not random import IDs or machine paths."""
    known = {}
    for name in ("resume.md", "learning-plan.md", "jd-starbridge.md", "jd-farhill.md", "evaluation-notes.md"):
        path = PACKAGE / "examples" / name
        known[sha256(path.read_bytes()).hexdigest()] = ("examples/" + name, name)
    for avatar, name in AVATAR_ASSETS.items():
        path = PACKAGE / "assets" / name
        known[sha256(path.read_bytes()).hexdigest()] = ("assets/avatar-" + avatar + ".png", "AI虚构头像 " + avatar.upper())
    formal = {d["path"] for d in snapshot["documents"]}
    aliases, originals = {}, {}
    for relative in snapshot["source_links"]:
        if relative in formal:
            continue
        path = ws.path(relative)
        selected = known.get(sha256(path.read_bytes()).hexdigest())
        if selected is None:
            raise ValueError("A demo source is not one of the bundled fictional inputs.")
        alias, title = selected
        aliases[relative] = alias
        originals[alias] = (path, title)

    def rebase(value):
        if isinstance(value, str):
            for original, alias in aliases.items():
                value = value.replace(original, alias)
            return value
        if isinstance(value, list):
            return [rebase(item) for item in value]
        if isinstance(value, dict):
            return {rebase(key): rebase(item) for key, item in value.items()
                    if key not in {"absolute_path", "href", "workspace_id", "workspace_path", "generated_at", "revision", "source_revisions"}}
        return value
    clean = rebase(snapshot)
    return clean, originals


def public_resume(raw, *, avatar, image_href, back_href):
    page = embedded_preview(raw).decode("utf-8")
    page = re.sub(r'<details class="claim-sources">[\s\S]*?</details>', '', page)
    page, count = re.subn(r'<details class="source-index">[\s\S]*?</details>', '', page)
    if count != 1:
        raise ValueError("Resume source index changed; update public adapter explicitly.")
    page, photos = re.subn(r'src="data:image/[^;]+;base64,[A-Za-z0-9+/=]+"', 'src="' + escape(image_href or '', quote=True) + '"', page)
    if photos != (0 if avatar == "none" else 1):
        raise ValueError("Unexpected photo in public fictional resume.")
    csp = "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'; object-src 'none'"
    page = re.sub(r'<meta http-equiv="Content-Security-Policy" content="[^"]*">', '<meta http-equiv="Content-Security-Policy" content="' + escape(csp, quote=True) + '">', page, count=1)
    page = page.replace('alt="用户指定的简历照片"', 'alt="AI生成的虚构示例头像"')
    banner = '<p style="max-width:210mm;margin:14px auto;padding:0 16px;font:12px/1.6 sans-serif;color:#657083">虚构排版示例 · 非真实个人简历' + (' · ' + _link("返回演示", back_href) if back_href else '') + '</p>'
    return re.sub(r'(<body[^>]*>)', r'\1' + banner, page, count=1)


class _URLs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.external_assets = []
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {"href", "src", "action"} and value:
                self.urls.append(value)
                if key == "src" and urlsplit(value).scheme not in {"", "data"}:
                    self.external_assets.append(value)


def validate_public_site(root, private_root=None):
    """Validate the actual portable output, including JS-driven gallery paths."""
    root = Path(root).resolve()
    count = 0
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Public demo contains a symlink.")
        if not path.is_file():
            continue
        if path.suffix not in {".html", ".png"} and path.name != ".nojekyll":
            raise ValueError("Unexpected public demo file: " + str(path.relative_to(root)))
        count += 1
        if path.suffix != ".html":
            continue
        text = path.read_text(encoding="utf-8")
        forbidden = ["file://", "/Users/", "/home/", "/var/folders/", "/private/var/", ".luji/", "workspace_id", "workspace_path", "manifest.json", "approval_token", "generated_at", "checked_at"]
        if private_root:
            forbidden.append(str(private_root))
        if any(token in text for token in forbidden):
            raise ValueError("A local/runtime reference reached the public demo: " + str(path.relative_to(root)))
        parser = _URLs()
        parser.feed(text)
        if parser.external_assets or re.search(r'url\(\s*[\"\']?https?://', text, re.I):
            raise ValueError("The public demo must not depend on external assets.")
        urls = parser.urls
        if path == root / "gallery/index.html":
            matched = re.search(r'<script id="gallery-data" type="application/json">([\s\S]*?)</script>', text)
            if not matched:
                raise ValueError("Missing public gallery data.")
            data = json.loads(matched.group(1))
            urls += [data["workbench_url"]]
            urls += [a["thumbnail"] for a in data["avatars"] if a.get("thumbnail")]
            for template in data["templates"]:
                urls += list(template["variants"].values()) + list(template["embedded_variants"].values())
        for value in urls:
            parsed = urlsplit(value)
            if parsed.scheme:
                if parsed.scheme != "https" or parsed.username or parsed.password:
                    raise ValueError("Unsafe public demo link.")
                continue
            if parsed.netloc or value.startswith("/") or "\\" in value:
                raise ValueError("Demo links must be relative to support project subpaths.")
            if not parsed.path:
                continue
            target = (path.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(root) or not target.is_file():
                raise ValueError("Broken public demo link: " + str(path.relative_to(root)) + " -> " + value)
    return count


def _build(stage, gallery):
    ws = Workspace(gallery / "fixtures/a")
    snapshot, originals = public_snapshot(build_snapshot(ws, DEMO_DATE), ws)
    for avatar, filename in AVATAR_ASSETS.items():
        target = stage / "assets" / ("avatar-" + avatar + ".png")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PACKAGE / "assets" / filename, target)

    # Explicitly publish record text as escaped read-only pages, not a workspace.
    for relative in snapshot["source_links"]:
        doc = next((d for d in snapshot["documents"] if d["path"] == relative), None)
        if doc is None:
            source, title = originals[relative]
            title += " · 虚构原始材料"
            if source.suffix.lower() == ".md":
                body = '<div class="demo-reading">' + escape(source.read_text(encoding="utf-8")) + '</div>'
            else:
                body = '<p>AI生成的虚构示例头像，不作为职业经历或能力的事实依据。</p><img style="max-width:220px;border-radius:18px" src="../assets/avatar-a.png" alt="AI生成虚构头像A">'
        else:
            title = doc["metadata"]["title"]
            body = '<div class="demo-reading">' + escape(doc["body"]) + '</div>'
            sources = list(dict.fromkeys(Workspace._source_paths(doc["metadata"])))
            if sources:
                body += '<section class="demo-source"><h2>本例引用的来源</h2><p class="small muted">原件使用公开样例的稳定名称，不包含本机导入标识。</p><ul>' + ''.join('<li>' + _link(p, source_name(p)) + '</li>' for p in sources) + '</ul></section>'
        location = "records/" + source_name(relative)
        body = '<h1>' + escape(title) + '</h1><p class="small muted">只读虚构记录</p>' + body
        _write(stage / location, _page(title, body, location=location))

    resumes = []
    for i, version in enumerate(snapshot["resumes"]):
        if not version.get("html_relative_path"):
            continue
        location = "resumes/" + ("common" if version["scope"]["company_id"] is None else "company-" + str(i)) + ".html"
        raw = ws.path(version["html_relative_path"]).read_bytes()
        _write(stage / location, public_resume(raw, avatar="a", image_href="../assets/avatar-a.png", back_href="../workbench/roles.html"))
        resumes.append(("岗位通用示例" if version["scope"]["company_id"] is None else "公司定向示例", location))
    for view, body in {"overview": _overview(snapshot), "plan": _plan(snapshot), "roles": _roles(snapshot, resumes), "applications": _applications(snapshot)}.items():
        location = "workbench/" + view + ".html"
        _write(stage / location, _page(VIEWS[view], body, location=location, view=view))
    _write(stage / "index.html", _page("把过去、现在和未来接起来", _intro(snapshot)))

    for avatar in AVATARS:
        for identifier in TEMPLATES:
            raw = (gallery / "previews" / avatar / (identifier + ".html")).read_bytes()
            image = None if avatar == "none" else "../../../assets/avatar-" + avatar + ".png"
            public = public_resume(raw, avatar=avatar, image_href=image, back_href="../../index.html")
            _write(stage / "gallery/previews" / avatar / (identifier + ".html"), public)
            # An embedded sample has no navigation that could nest the gallery
            # recursively inside its own iframe.
            embedded = public_resume(raw, avatar=avatar, image_href=image, back_href=None)
            _write(stage / "gallery/embedded-previews" / avatar / (identifier + ".html"), embedded)
    payload = {"default_template": "profile-split", "default_avatar": "a",
               "templates": [{"id": key, "name": name, "description": DESCRIPTIONS[key],
                              "variants": {a: "previews/" + a + "/" + key + ".html" for a in AVATARS},
                              "embedded_variants": {a: "embedded-previews/" + a + "/" + key + ".html" for a in AVATARS}}
                             for key, name in TEMPLATES.items()],
               "avatars": [{"id": "a", "name": "头像 A", "thumbnail": "../assets/avatar-a.png"},
                           {"id": "b", "name": "头像 B", "thumbnail": "../assets/avatar-b.png"},
                           {"id": "none", "name": "不放头像", "thumbnail": None}],
               "references": load_references(PACKAGE / "references/resume-samples.json"),
               "workbench_url": "../workbench/overview.html"}
    template = (PACKAGE / "assets/resume_gallery.html").read_text(encoding="utf-8")
    template = template.replace(" file:", "").replace("打开预览 / 打印 ↗", "打开只读样例 ↗")
    template = template.replace("<title>履迹 · 简历样式</title>", "<title>履迹 LüJi · 虚构简历样式</title>")
    template = template.replace("选择样式不会修改职业资料或保存一份正式简历。", "虚构只读演示，不连接 Agent、保存资料或生成正式简历。")
    _write(stage / "gallery/index.html", render_gallery(template, payload))
    (stage / ".nojekyll").write_bytes(b"")
    return {"records": len(snapshot["source_links"]), "resume_examples": len(resumes)}


def run(output):
    destination = new_destination(output)
    # All generated identities, proposals, hashes and local paths stay here.
    with tempfile.TemporaryDirectory(prefix=".lvji-demo-build-", dir=destination.parent) as tmp:
        temporary = Path(tmp)
        gallery = temporary / "private-gallery"
        build_gallery(gallery, DEMO_DATE)
        stage = temporary / "public"
        stage.mkdir()
        counts = _build(stage, gallery)
        files = validate_public_site(stage, temporary)
        destination.mkdir(exist_ok=False)
        owned_inode = destination.stat().st_ino
        try:
            # Exclusive creation cannot overwrite a file appearing during copy.
            for source in sorted(stage.rglob("*")):
                target = destination / source.relative_to(stage)
                if source.is_dir():
                    target.mkdir(exist_ok=False)
                else:
                    with source.open("rb") as reader, target.open("xb") as writer:
                        shutil.copyfileobj(reader, writer)
            validate_public_site(destination, temporary)
        except Exception:
            if destination.exists() and not destination.is_symlink() and destination.stat().st_ino == owned_inode:
                shutil.rmtree(destination)
            raise
    return {"status": "generated_not_opened", "fictional_only": True, "read_only": True,
            "published": False, "output": str(destination), "index": str(destination / "index.html"),
            "files": files, "views": len(VIEWS), "gallery_combinations": 18, **counts,
            "note": "Portable static HTML only. Dialogue is a scripted example; no live Agent, writeback, model or personal workspace is included."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="A new, nonexistent site directory with an existing parent")
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.output), ensure_ascii=False, indent=2))
    except (ValueError, StoreError, OSError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
