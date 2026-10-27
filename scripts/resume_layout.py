#!/usr/bin/env python3
"""LuJi original six offline resume layouts and optional local Chromium compiler.

Fact storage is deliberately separate. No dependencies, remote assets or model calls.
The layouts preserve supplied strings and use only system fonts.
"""
from __future__ import annotations
import base64
import hashlib
import html
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
from md_workspace import StoreError

TEMPLATES = {
    "evidence-archive": "证据档案",
    "classic-single": "经典单栏",
    "ats-minimal": "简洁文本",
    "project-first": "项目优先",
    "profile-split": "简介侧栏",
    "experience-first": "经历优先",
}
MAX_PHOTO = 5 * 1024 * 1024
MAX_HTML = 12 * 1024 * 1024
MAX_PDF = 50 * 1024 * 1024
VERSION_RE = re.compile(r"^v-[0-9a-f]{32}$")
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
PRINT_SCRIPT = "document.getElementById('print').addEventListener('click',function(){window.print();});"
def _error(code, message):
    raise StoreError(code, message)


def _read(path, limit):
    try:
        if not path.is_file() or path.is_symlink() or path.stat().st_size > limit:
            raise OSError()
        raw = path.read_bytes()
        if len(raw) > limit:
            raise OSError()
        return raw
    except OSError:
        _error("read_failed", "Cannot read a regular local file within its size limit: " + path.name)


def read_photo(path):
    """Accept only an explicitly supplied local PNG/JPEG/WebP, never SVG/HTML."""
    photo = Path(path).expanduser().absolute()
    check = Path(photo.anchor)
    for part in photo.parts[1:]:
        check /= part
        if check.is_symlink():
            _error("unsafe_path", "Photo paths must not contain symlinks.")
    raw = _read(photo, MAX_PHOTO)
    extension = None
    if len(raw) >= 24 and raw.startswith(b"\x89PNG\r\n\x1a\n") and raw[12:16] == b"IHDR":
        width, height = struct.unpack(">II", raw[16:24])
        if not (1 <= width <= 20000 and 1 <= height <= 20000):
            _error("invalid_photo", "PNG dimensions are invalid or too large.")
        extension = "png"
    elif len(raw) >= 4 and raw.startswith(b"\xff\xd8\xff") and raw.endswith(b"\xff\xd9"):
        extension = "jpg"
    elif (len(raw) >= 20 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"
          and raw[12:16] in {b"VP8 ", b"VP8L", b"VP8X"}
          and int.from_bytes(raw[4:8], "little") == len(raw) - 8):
        extension = "webp"
    if extension is None:
        _error("invalid_photo", "Photo bytes must have a PNG, JPEG, or WebP signature within 5 MiB.")
    return "photo." + extension, raw


def _source_note(paths):
    # Preserve the claim/source relationship without making file paths part of
    # the visible resume layout. Native details works offline and without JS.
    return ('<details class="claim-sources"><summary>来源</summary><small>'
            + " · ".join(html.escape(p) for p in paths) + '</small></details>')


def _sidebar_section(title):
    """Recognize only explicit education/skills headings; unknowns stay primary."""
    normalized = re.sub(r"[\s/&+|:：·—–_-]+", "", title.strip().casefold())
    return normalized in {
        "教育", "教育经历", "教育背景", "学历", "学历背景", "教育与资格",
        "技能", "专业技能", "核心技能", "技能清单", "技能与工具", "工具与技能", "技能与证书", "技能与方法",
        "education", "educationbackground", "academicbackground", "educationqualifications",
        "skills", "technicalskills", "coreskills", "skillsandtools", "toolsandskills", "skillstools",
        "教育经历education", "教育背景education", "education教育经历", "education教育背景",
        "专业技能skills", "技能skills", "skills专业技能", "skills技能",
    }


def _work_section(title):
    """Prioritize explicit work headings without treating education as employment."""
    normalized = re.sub(r"[\s/&+|:：·—–_-]+", "", title.strip().casefold())
    return any(word in normalized for word in ("工作", "任职", "职业经历")) or normalized in {
        "experience", "workexperience", "professionalexperience", "employment",
        "employmenthistory", "workhistory", "careerexperience",
    }


def render_html(content, template, source_revisions, photo_name=None, photo_raw=None):
    """All templates render the same supplied strings and sources, without remote assets."""
    if template not in TEMPLATES:
        _error("invalid_template", "Unknown resume layout.")
    esc = html.escape
    person = content["person"]
    portrait = ""
    if photo_name:
        mime = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}[photo_name.rsplit(".", 1)[1]]
        portrait = '<img class="photo" alt="用户指定的简历照片" src="data:' + mime + ';base64,' + base64.b64encode(photo_raw).decode("ascii") + '">'
    sections = []
    # Reorder sections only; no title, claim, date or source is inferred/rewritten.
    indexed = list(enumerate(content["sections"]))
    if template == "project-first":
        indexed.sort(key=lambda pair: (not any(w in pair[1]["title"].lower() for w in ("项目", "project")), pair[0]))
    elif template == "experience-first":
        indexed.sort(key=lambda pair: (not _work_section(pair[1]["title"]), pair[0]))
    for _, section in indexed:
        items = []
        for item in section["items"]:
            items.append('<article><h3>' + esc(item["heading"]) + '</h3><p>' + esc(item["body"]) + '</p>' + _source_note(item["source_paths"]) + '</article>')
        sections.append((section["title"], '<section><h2>' + esc(section["title"]) + '</h2><div class="section-content">' + "".join(items) + '</div></section>'))
    summary = ""
    if content["summary"]["text"].strip():
        summary = '<section class="summary"><h2>个人简介</h2><div class="section-content"><p>' + esc(content["summary"]["text"]) + '</p>' + _source_note(content["summary"]["source_paths"]) + '</div></section>'
    sidebar = [markup for title, markup in sections if _sidebar_section(title)]
    primary = [markup for title, markup in sections if not _sidebar_section(title)]
    if template == "profile-split" and (summary or sidebar) and primary:
        body = ('<div class="resume-body two-column"><aside class="sidebar">' + summary + "".join(sidebar)
                + '</aside><div class="sections primary-column">' + "".join(primary) + '</div></div>')
    else:
        # No empty column when the content only needs a single reading flow.
        body = '<div class="resume-body single-column"><div class="sections">' + summary + "".join(markup for _, markup in sections) + '</div></div>'
    all_sources = "".join('<li><code>' + esc(path) + '</code><br><small>' + esc(source_revisions[path]) + '</small></li>' for path in sorted(source_revisions))
    script_hash = base64.b64encode(hashlib.sha256(PRINT_SCRIPT.encode()).digest()).decode("ascii")
    csp = "default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'sha256-" + script_hash + "'; base-uri 'none'; form-action 'none'; connect-src 'none'; object-src 'none'"
    # Original CSS using system fonts. Page geometry remains identical between
    # the self-contained preview and Chromium print; no third-party assets.
    css = """
@page{size:A4;margin:12.5mm}
*{box-sizing:border-box}
html{color:#303030;background:#e9eaec;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei','Noto Sans CJK SC',Arial,sans-serif;font-size:9.5pt;line-height:1.6}
body{margin:0;-webkit-print-color-adjust:exact;print-color-adjust:exact}
main{width:210mm;max-width:calc(100% - 32px);min-height:297mm;margin:18px auto 28px;padding:12.5mm;background:#fff;box-shadow:0 4px 24px rgba(0,0,0,.08)}
header{display:flex;align-items:center;gap:8mm;padding-bottom:11pt;margin-bottom:15pt;border-bottom:.5pt solid #cfcfcf;break-inside:avoid;page-break-inside:avoid}
.identity{flex:1;min-width:0}
h1{font-size:24pt;line-height:1.2;letter-spacing:.02em;font-weight:650;color:#222;margin:0 0 6pt;overflow-wrap:anywhere}
.headline{font-size:10.8pt;line-height:1.45;color:#303030;margin:0 0 5pt}
.contacts{display:flex;flex-wrap:wrap;column-gap:12pt;row-gap:1pt;color:#666;font-size:9pt;line-height:1.5}
.contacts span{display:inline-block;overflow-wrap:anywhere;max-width:100%}
.photo{width:26mm;height:33mm;object-fit:cover;object-position:center 35%;flex:none;display:block;border-radius:1.5mm}
.resume-body{min-width:0}
.resume-body.two-column{display:grid;grid-template-columns:minmax(0,30fr) minmax(0,70fr);column-gap:8mm;align-items:start}
.sidebar,.sections,.section-content{min-width:0}
.sidebar{padding:5mm;background:#f3f4f4;border-radius:1.5mm}
section{margin:0 0 14pt;break-inside:auto}
section:last-child{margin-bottom:0}
h2{font-size:10.8pt;line-height:1.4;font-weight:650;color:#222;margin:0 0 6pt;padding-bottom:3pt;border-bottom:.5pt solid #cfcfcf;break-after:avoid;page-break-after:avoid}
h3{font-size:9.5pt;line-height:1.5;font-weight:650;color:#303030;margin:0 0 2pt;white-space:pre-wrap;overflow-wrap:anywhere;break-after:avoid;page-break-after:avoid}
p{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;orphans:3;widows:3}
article{margin:0;break-inside:avoid-page;page-break-inside:avoid}
article+article{margin-top:9pt}
.claim-sources{margin:3pt 0 0;color:#666;font-size:8pt;line-height:1.4;overflow-wrap:anywhere}
.claim-sources summary{display:list-item;cursor:pointer;width:fit-content}
.claim-sources small{font-size:inherit}
.source-index{margin-top:18pt;padding-top:9pt;border-top:.5pt solid #dedede;color:#666;font-size:8.5pt;overflow-wrap:anywhere}
.source-index summary{cursor:pointer}
.source-index p{margin:5pt 0}
.source-index ul{padding-left:16pt;margin:5pt 0 0}
.source-index li{margin:5pt 0}
.source-index code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:8pt}
.tools{width:210mm;max-width:calc(100% - 32px);margin:18px auto 0;display:flex;justify-content:space-between;align-items:center;gap:12px;color:#666;font-size:10pt}
button{font:inherit;color:#303030;border:1px solid #c7c7c7;background:#fff;border-radius:4px;padding:8px 13px;min-height:40px;cursor:pointer}
button:focus-visible,summary:focus-visible{outline:2px solid #536a7a;outline-offset:3px}
body.profile-split .sidebar h2{font-size:10pt;border:0;padding-bottom:0;margin-bottom:5pt;color:#4d5357}
body.profile-split .sidebar section{margin-bottom:14pt}
body.profile-split .primary-column h2{border-bottom-color:#bfc5c8}
body.evidence-archive header{align-items:flex-start;border-bottom:1pt solid #353b3f}
body.evidence-archive .headline{max-width:135mm}
body.evidence-archive .photo{width:28mm;height:28mm;border-radius:50%}
body.evidence-archive .sections>section{display:grid;grid-template-columns:27mm minmax(0,1fr);column-gap:6mm;padding-top:9pt;margin-bottom:15pt;border-top:.5pt solid #d7dadb}
body.evidence-archive .sections>section:first-child{padding-top:0;border-top:0}
body.evidence-archive h2{font-size:9.5pt;line-height:1.6;letter-spacing:.04em;border:0;padding:0;margin:0;color:#5b6266}
body.classic-single header{display:grid;grid-template-columns:26mm minmax(0,1fr) 26mm;gap:5mm;border-bottom:1pt solid #333;padding-bottom:10pt}
body.classic-single .identity{grid-column:2;text-align:center}
body.classic-single .contacts{justify-content:center}
body.classic-single .photo{grid-column:3;grid-row:1;width:24mm;height:30mm;border-radius:0}
body.classic-single h1{font-size:23pt;letter-spacing:.08em}
body.classic-single h2{font-size:10.5pt;border-bottom:.7pt solid #777;padding-bottom:4pt}
body.ats-minimal header{border:0;padding-bottom:0;margin-bottom:16pt}
body.ats-minimal h1{font-size:22pt;letter-spacing:0}
body.ats-minimal .headline,body.ats-minimal .contacts{color:#303030}
body.ats-minimal h2{border:0;padding:0;margin-bottom:5pt;font-size:10.5pt}
body.ats-minimal section{margin-bottom:13pt}
body.ats-minimal .photo{border-radius:0;width:24mm;height:30mm}
body.project-first header{border-bottom:1.4pt solid #3f4e59}
body.project-first h2{border:0;border-left:2pt solid #516473;padding:0 0 0 7pt;margin-bottom:7pt;font-size:10.5pt}
body.project-first h3{font-size:10pt}
body.project-first .photo{border-radius:3mm}
body.experience-first header{border-bottom:0;margin-bottom:16pt}
body.experience-first h2{display:flex;align-items:center;gap:9pt;border:0;padding:0;margin-bottom:7pt;font-size:10.5pt}
body.experience-first h2::after{content:"";height:.5pt;background:#bcc2c6;flex:1}
body.experience-first h3{font-size:10pt;font-weight:700}
body.experience-first article{border-left:1pt solid #d7dcdf;padding-left:9pt}
body.experience-first .summary .section-content{border-left:1pt solid #d7dcdf;padding-left:9pt}
body.experience-first .photo{border-radius:50%;width:30mm;height:30mm}
@media screen and (max-width:650px){html{font-size:10pt}main{max-width:100%;min-height:0;margin:12px 0 0;padding:22px;box-shadow:none}.tools{max-width:calc(100% - 32px);margin:12px auto 0;font-size:9pt}.resume-body.two-column{display:block}.sidebar{margin-bottom:16pt}.photo{width:24mm;height:30mm}header{gap:6mm}h1{font-size:22pt}body.evidence-archive .sections>section{display:block}body.evidence-archive h2{margin-bottom:6pt}body.classic-single header{grid-template-columns:minmax(0,1fr) auto;gap:4mm}body.classic-single .identity{grid-column:1;text-align:left}body.classic-single .contacts{justify-content:flex-start}body.classic-single .photo{grid-column:2}body.classic-single h1{letter-spacing:.02em}}
@media print{html,body{background:#fff}main{width:auto;max-width:none;min-height:0;margin:0;padding:0;box-shadow:none}.tools,details,.claim-sources{display:none!important}a{color:inherit;text-decoration:none}.resume-body.two-column{grid-template-columns:minmax(0,30fr) minmax(0,70fr)}section{break-inside:auto}header{break-inside:avoid}h2,h3{break-after:avoid}p{orphans:3;widows:3}}
"""
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="' + esc(csp, quote=True) + '">'
            '<title>' + esc(person["name"]) + ' · 简历草稿</title><style>' + css + '</style></head>'
            '<body class="' + template + '"><div class="tools"><span>简历草稿 · 请先核对正文与来源</span>'
            '<button id="print" type="button">打印 / 另存为 PDF</button></div><main><header><div class="identity">'
            '<h1>' + esc(person["name"]) + '</h1><p class="headline">' + esc(person["headline"]) + '</p><div class="contacts">'
            + "".join('<span>' + esc(contact) + '</span>' for contact in person["contacts"]) + '</div></div>' + portrait + '</header>'
            + body + '<details class="source-index"><summary>核对来源（打印时隐藏）</summary><p>请核对 content.json 中的正文、姓名与联系方式。以下列出实际使用的本地来源及版本。</p><ul>'
            + all_sources + '</ul></details></main><script>' + PRINT_SCRIPT + '</script></body></html>\n').encode("utf-8")


def find_browser(explicit=None):
    candidates = ([str(Path(explicit).expanduser())] if explicit is not None else [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        *[shutil.which(name) for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome")],
    ])
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return str(Path(candidate).resolve())
    return None


def compile_chromium(executable, source, output, profile):
    command = [executable, "--headless", "--disable-gpu", "--disable-background-networking",
               "--disable-component-update", "--disable-default-apps", "--disable-extensions",
               "--disable-sync", "--no-first-run", "--no-default-browser-check",
               "--metrics-recording-only", "--safebrowsing-disable-auto-update",
               "--password-store=basic", "--use-mock-keychain", "--host-resolver-rules=MAP * ~NOTFOUND",
               "--no-pdf-header-footer", "--print-to-pdf-no-header",
               "--user-data-dir=" + str(profile), "--print-to-pdf=" + str(output), source.as_uri()]
    try:
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90, check=False)
    except (OSError, subprocess.TimeoutExpired):
        _error("pdf_failed", "The local browser could not finish PDF export. No PDF was saved.")
    if process.returncode != 0:
        _error("pdf_failed", "The local browser reported a PDF export failure. No PDF was saved.")


