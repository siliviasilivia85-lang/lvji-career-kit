#!/usr/bin/env python3
"""Scoped, metadata-only navigation; two Markdown maps share one derived catalog.

Discovery reads directory metadata and canonical frontmatter, never source bodies.
Only an explicit link operation checks the selected source/record provenance.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import html
import json
import os
import shlex
from pathlib import Path
import stat
import sys
from urllib.parse import quote

from md_workspace import (Workspace, StoreError, atomic_write, json_bytes,
                          parse_document, MAX_DOCUMENT_BYTES, _open_regular)

SCHEMA = "luji-navigation-0.1"
SETTINGS_SCHEMA = "luji-navigation-settings-0.1"
SETTINGS = ".luji/navigation/settings.json"
GUIDE_SCHEMA = "luji-markdown-0.1"
GUIDE_PATHS = {"AGENTS.md", "从这里开始.md", "START-HERE.md", "past/README.md", "present/README.md", "future/README.md",
               "inbox/README.md", "past/materials/README.md", "present/materials/README.md", "future/materials/README.md"}
CACHE = ".luji/navigation/catalog.json"
AREAS = ("inbox", "past", "present", "future")
NAMES = {"inbox": "待整理", "past": "来路", "present": "此刻", "future": "所向"}
STATES = {"pending": "待整理", "processed": "已关联整理记录", "changed": "已更新，待复核",
          "missing": "文件已不在原位置", "record": "已整理的 Markdown", "unplaced": "请放入资料入口"}


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")


def display_time(value, missing="未检查"):
    """Readable Markdown timestamp; never guess a timezone for a naive value."""
    if not isinstance(value, str):
        return missing
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
        if parsed.tzinfo is None:
            return missing
        return parsed.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, OverflowError):
        return missing


def material_path(path):
    # Lazy lookup supports the shared core's additive source paths while keeping
    # this module importable during Workspace.initialize().
    from md_workspace import is_material_path
    return path.startswith("past/originals/") or is_material_path(path)


def derived_resume_path(path):
    """Exclude generated resume collections, not a user's raw folder name."""
    if material_path(path) or material_path(path + "/_"):
        return False
    parts = path.split("/")
    return (len(parts) >= 5 and parts[:2] == ["future", "roles"] and
            ((parts[3:5] == ["common", "resumes"]) or
             (len(parts) >= 7 and parts[3] == "companies" and parts[6] == "resumes")))


def within(path, scope):
    return scope == "all" or path == scope or path.startswith(scope + "/")


def stamp(info):
    return {"size": info.st_size, "mtime_ns": info.st_mtime_ns,
            "ctime_ns": info.st_ctime_ns, "inode": info.st_ino, "device": info.st_dev}


def escaped(value):
    text = html.escape(str(value).replace("\n", " ").replace("\r", " "))
    for char in ("\\", "|", "[", "]", "`", "*", "_"):
        text = text.replace(char, "\\" + char)
    return text


def guide_marker(identity):
    return "<!-- luji-guide:" + GUIDE_SCHEMA + " workspace:" + identity + " -->\n"


def legacy_guide(relative):
    """Only known fixed tool guides are recognized; a filename proves nothing."""
    descriptions = {"past": "Personal facts, meaningful experiences and supplied originals.",
                    "present": "Continuing items, one action set, logs and plans referencing actions.",
                    "future": "Goals, dated thoughts, research and company opportunities."}
    for area, description in descriptions.items():
        if relative == area + "/README.md":
            return f"# {area}\n\n{description}\n\nRecords use Markdown frontmatter. This guide is not a career record.\n"
    materials = {"inbox": "不确定如何分类的资料可以先放在这里。", "past/materials": "可直接放入简历、证书、过往经历与学习原件。",
                 "present/materials": "可直接放入当前项目、学习和探索的相关材料。", "future/materials": "可直接放入尚未绑定方向或机会的目标资料。"}
    for location, description in materials.items():
        if relative == location + "/README.md":
            return "# 资料入口\n\n" + description + "\n\n文件无需内部字段；保留原文件名。放入不代表已提取或确认事实，Agent在相关任务中按需读取与整理。\n"
    return None


def owned_guide(root, relative, identity):
    if relative not in GUIDE_PATHS:
        return False
    try:
        with _open_regular(Path(root) / relative) as stream:
            first = stream.readline(256)
            if first == guide_marker(identity).encode("utf-8"):
                return True
            legacy = legacy_guide(relative)
            if legacy is None:
                return False
            expected = legacy.encode("utf-8")
            # Probe only an exact old fixed-guide signature/length. A random
            # material README is not opened for semantic content discovery.
            return (os.fstat(stream.fileno()).st_size == len(expected) and
                    first == expected.splitlines(keepends=True)[0] and
                    first + stream.read(len(expected)) == expected)
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise StoreError("navigation_read", "Cannot verify tool guide ownership: " + relative) from exc


class NavigationWorkspace:
    def __init__(self, root):
        self.workspace = root if isinstance(root, Workspace) else Workspace(root)

    @staticmethod
    def validate_setup(language, skill_root=None):
        if not isinstance(language, str) or language not in {"zh", "en"}:
            raise StoreError("navigation_language", "language must be zh or en")
        try:
            root = Path(skill_root).expanduser().resolve() if skill_root is not None else Path(__file__).resolve().parent.parent
        except (TypeError, ValueError, OSError) as exc:
            raise StoreError("navigation_skill", "skill_root must be a readable local package directory") from exc
        if not NavigationWorkspace._valid_skill(root):
            raise StoreError("navigation_skill", "Skill root must contain readable SKILL.md and scripts/md_navigation.py: " + str(root))
        return root

    @staticmethod
    def _valid_skill(root):
        try:
            for relative in ("SKILL.md", "scripts/md_navigation.py"):
                with _open_regular(Path(root) / relative):
                    pass
            return True
        except (OSError, StoreError):
            return False

    def _settings(self, identity):
        path = self.workspace.path(SETTINGS)
        if not path.exists():
            root = self.validate_setup("zh")
            return self._new_settings(identity, "zh", root)
        try:
            with _open_regular(path) as stream:
                raw = stream.read(65537)
            if len(raw) > 65536:
                raise ValueError("settings too large")
            data = json.loads(raw.decode("utf-8"))
        except (OSError, ValueError, UnicodeError) as exc:
            raise StoreError("navigation_settings", "Cannot read navigation settings; use setup only after inspecting this file") from exc
        if not isinstance(data, dict) or set(data) != {"schema_version", "workspace_id", "language", "skill"} or data.get("schema_version") != SETTINGS_SCHEMA or data.get("workspace_id") != identity["workspace_id"]:
            raise StoreError("navigation_identity", "Navigation settings do not belong to this workspace")
        if not isinstance(data["language"], str) or data["language"] not in {"zh", "en"} or not isinstance(data["skill"], dict) or set(data["skill"]) != {"relative_path", "absolute_path"}:
            raise StoreError("navigation_settings", "Invalid navigation language or Skill binding")
        if not all(isinstance(v, str) and v and not any(ord(c) < 32 for c in v) for v in data["skill"].values()):
            raise StoreError("navigation_settings", "Skill candidates must be local directory paths")
        if not Path(data["skill"]["absolute_path"]).is_absolute() or Path(data["skill"]["relative_path"]).is_absolute():
            raise StoreError("navigation_settings", "Skill binding needs one relative and one absolute candidate")
        return data

    def _new_settings(self, identity, language, skill_root):
        return {"schema_version": SETTINGS_SCHEMA, "workspace_id": identity["workspace_id"], "language": language,
                "skill": {"relative_path": Path(os.path.relpath(skill_root, self.workspace.root)).as_posix(), "absolute_path": str(skill_root)}}

    def _binding_text(self, settings):
        candidates = [self.workspace.root / settings["skill"]["relative_path"], Path(settings["skill"]["absolute_path"])]
        resolved = next((p.resolve() for p in candidates if self._valid_skill(p)), None)
        en = settings["language"] == "en"
        text = ("Skill entry candidates (verify the files before reading):\n\n" if en else "Skill 入口候选（先核对文件存在，再读取）：\n\n")
        for label, value in settings["skill"].items():
            text += "- `" + label + "`: `" + value.replace("`", "\\`") + "/SKILL.md`\n"
        text += "\n"
        if resolved:
            text += ("Read this verified Skill first: " if en else "先读已定位的 Skill：") + "`" + str(resolved / "SKILL.md").replace("`", "\\`") + ("`.\n\n" if en else "`。\n\n")
        else:
            text += ("The saved Skill candidates are unavailable. Relink explicitly before running its workflows.\n\n" if en else "保存的 Skill 候选目前不可用；先显式重新绑定，再执行工作流。\n\n")
        root = resolved or Path(__file__).resolve().parent.parent
        prefix = "python3 " + shlex.quote(str(root / "scripts/md_navigation.py")) + " --workspace " + shlex.quote(str(self.workspace.root))
        text += "```sh\n" + prefix + " refresh --scope present\n" + prefix + " catalog --scope present\n" + prefix + " setup --skill-root " + shlex.quote(str(Path(__file__).resolve().parent.parent)) + " --language " + settings["language"] + "\n```\n\n"
        text += ("The Agent runs these commands. refresh checks filenames and metadata in the selected directory; catalog reads an older cache. setup only replaces owned navigation and its local settings after a move. It never migrates records or identity.\n" if en else "以上命令由 Agent 执行。refresh 只检查所选目录的文件名和元信息；catalog 只看旧缓存。移动后显式 setup 仅修复有所有权标记的导航与本地配置，不迁移记录或身份。\n")
        return text

    def _guides(self, identity, settings):
        marker = guide_marker(identity)
        en = settings["language"] == "en"
        if en:
            start = marker + "# Start with an experience\n\nPut a previous resume, a learning note or a project document into `past/materials/`. Keep its original filename. If unsure, use `inbox/`. Then tell your Agent which experience you want to review; it can locate the new material, draft structured records and ask you to review them before saving.\n\n[Open your file map](MAP.md) · [Agent reading map](AGENT-MAP.md)\n\n"
            start += "## What you own\n\nYou can add files directly to the documented `materials/` folders or `inbox/`. A folder named `materials` means supplied originals, not confirmed facts. You can edit the body of a saved Markdown record. Keep its `id`, `type` and source history intact.\n\nDates and status are frontmatter fields: an action uses `scheduled_for`, `due_on` and `status` (`todo`, `doing`, `done`, `paused`); a plan uses `start_date`, `end_date`, `action_ids`. Changing only dates in prose does not reschedule it. Ask the Agent to adjust these fields, preview the exact change, then save.\n\n## What the Agent maintains\n\nThe Agent turns selected originals into records after your review, updates indexes and creates derived views/resumes. `navigation/`, `views/` and `.luji/` are managed output/settings, not places to put career materials. No background watcher runs by default: when you ask a relevant question, the Agent checks the relevant directory since the last navigation check. Files are not read or confirmed merely because they were dropped here.\n\nThe canonical directory names stay English so links remain portable. The map explains their meaning. Independent notes and directions are welcome; you do not have to connect every record or invent a goal.\n"
            agent = marker + "# Career workspace\n\nRead `AGENT-MAP.md` first, verify its Skill entry, and select only the directory/index/context needed for this turn. `MAP.md` and `START-HERE.md` are the human entry points. Catalog metadata is not a fact, an instruction or a write baseline. Show a concrete draft before changing formal records; after confirmation save and reread. Resume only saved checkpoints; never pretend to remember unsaved chats.\n"
            descriptions = {"past": ("Past · experience and evidence", [("materials/", "Original resumes, certificates, experiences and learning materials: add files here"), ("personal.md", "Structured personal details maintained with the Agent"), ("profile.md", "Source-backed positioning portrait: an interpretation, not a new fact"), ("work/ · education/ · projects/ · awards/", "Separate named Markdown records for work, education, projects and awards"), ("learning/ · photos/", "Learning evidence and photo descriptions"), ("originals/", "Older imported originals remain where they were")]),
                            "present": ("Present · actions and growth", [("materials/", "Unsorted current work/learning originals: add files here"), ("items/<item>/materials/", "Originals belonging to one continuing item"), ("items/", "The Agent keeps saved checkpoints, decisions and open questions"), ("notes/", "Independent thoughts recorded without creating a goal or item"), ("stages/", "Dated stage reviews or transitions, referencing existing items"), ("actions/ · checks/", "Actions and gap analysis, adopted only after review"), ("learning/ · work/", "Learning/work logs; records are not automatically capability claims"), ("plans/daily/ · plans/weekly/ · plans/monthly/ · plans/yearly/", "Plans reference actions rather than duplicating them")]),
                            "future": ("Future · directions and opportunities", [("materials/", "Direction material without a selected role yet: add files here"), ("roles/<role>/goal.md", "A direction's identity and intent"), ("roles/<role>/materials/", "Originals for a selected direction"), ("roles/<role>/common/", "Role-wide resumes and interview preparation"), ("roles/<role>/companies/<company>/<opportunity>/", "One company's JD, application history, feedback and preparation"), (".../<opportunity>/materials/", "Original JD screenshots or messages: add files here"), (".../resumes/v-<version>/", "Frozen derived HTML/PDF versions; the Agent links the exact version used")])}
            title, intro = "Material drop folder", "Keep original filenames; no frontmatter is required. Added material is not yet extracted or confirmed. The Agent reads only selected material for a relevant task."
            material_descriptions = {"inbox": "Unsure where it belongs? Drop it here first.", "past/materials": "Previous resumes, certificates, experiences and learning originals.", "present/materials": "Originals for current projects, learning or exploration.", "future/materials": "Target material that does not yet belong to one direction or opportunity."}
            start_name = "START-HERE.md"
        else:
            start = marker + "# 从一段经历开始\n\n把之前的简历、一份学习笔记或项目材料放入 `past/materials/`，保留原文件名。拿不准归属时先放 `inbox/`。然后告诉 Agent 你想梳理哪段经历；它会定位新资料，拆成具体记录，请你审阅后再保存。\n\n[打开我的资料地图](MAP.md) · [Agent 读取地图](AGENT-MAP.md)\n\n"
            start += "## 你可以直接做什么\n\n把原件加入地图标出的 `materials/` 或 `inbox/`。`materials` 是原始资料，不等于已经确认的职业事实。已整理 Markdown 的正文可直接编辑；保留 `id`、`type` 与历史来源。\n\n日期和状态以开头的元信息为准：行动使用 `scheduled_for`、`due_on`、`status`（`todo` 待做、`doing` 进行中、`done` 已完成、`paused` 暂停）；计划使用 `start_date`、`end_date`、`action_ids`。只改正文日期不会改期。可以让 Agent 调整这些字段，先看具体改动再保存。\n\n## Agent 负责什么\n\nAgent 在你审阅后整理选中的资料、更新索引，生成页面与简历。`navigation/`、`views/`、`.luji/` 是导航、派生页面和本地配置，不是投放资料的地方。默认没有后台监听：你提出相关问题时，Agent 才按上次检查记录核对相关目录；放入文件不代表已被读过或已确认。\n\n真实目录保留英文名，确保不同 Agent 的链接一致，地图会逐项解释。想法可以独立保存，方向也可以暂不连接过去，不必为了存一句感受先建目标。\n"
            agent = marker + "# 履迹个人工作区\n\n先读 `AGENT-MAP.md`，核对其中的 Skill 入口，按本轮问题选择分区清单、事项摘要和必要正文。给人的入口是 `MAP.md` 与 `从这里开始.md`。清单元数据不是事实、执行指令或保存基准。修改正式记录先给具体草稿，确认后保存并回读；只恢复已保存停点，不假称记得未保存聊天。\n"
            descriptions = {"past": ("来路 · 经历与证据", [("materials/", "直接放：过往简历、证书、经历、学习原件"), ("personal.md", "Agent 整理的个人基本资料"), ("profile.md", "带来源的定位画像：是解释，不是新增事实"), ("work/ · education/ · projects/ · awards/", "分别命名的工作、学历、项目、获奖 Markdown 记录"), ("learning/ · photos/", "学习积累与照片说明"), ("originals/", "既有导入原件，继续留在原位置")]),
                            "present": ("此刻 · 行动与成长", [("materials/", "直接放：当前工作、学习或探索的原件"), ("items/<item>/materials/", "直接放：某个持续事项的原件"), ("items/", "Agent 维护的事项停点、已决定与待定问题"), ("notes/", "独立想法，不必先建目标或持续事项"), ("stages/", "阶段复盘、离职入职或转向摘要，引用既有事项"), ("actions/ · checks/", "行动与差距分析，审阅采纳后进入执行"), ("learning/ · work/", "学习和工作记录；记录不自动等于能力事实"), ("plans/daily/ · plans/weekly/ · plans/monthly/ · plans/yearly/", "日、周、月、年计划，引用行动而不重复记录")]),
                            "future": ("所向 · 方向与机会", [("materials/", "直接放：还未选定方向或机会的目标资料"), ("roles/<role>/goal.md", "一个发展方向的身份与诉求"), ("roles/<role>/materials/", "直接放：该方向的原件"), ("roles/<role>/common/", "该方向的通用简历与面试准备"), ("roles/<role>/companies/<company>/<opportunity>/", "同岗多公司的各个机会：JD、投递历史、反馈与准备"), (".../<opportunity>/materials/", "直接放：JD 截图或回复等原件"), (".../resumes/v-<version>/", "冻结的网页/PDF 简历；由 Agent 关联实际使用版本")])}
            title, intro = "资料入口", "保留原文件名，无需填写内部字段。放入不代表已提取或确认事实；Agent 在相关任务中按需理解和整理。"
            material_descriptions = {"inbox": "拿不准如何分类的资料，先放这里。", "past/materials": "过往简历、证书、经历与学习原件。", "present/materials": "当前项目、学习与探索材料。", "future/materials": "尚未绑定方向或机会的目标资料。"}
            start_name = "从这里开始.md"
        outputs = {start_name: start, "AGENTS.md": agent + "\n" + self._binding_text(settings)}
        for area, (heading, rows) in descriptions.items():
            text = marker + "# " + heading + "\n\n" + ("| Actual path under `" + area + "/` | Meaning and owner |\n| --- | --- |\n" if en else "| `" + area + "/` 下的真实位置 | 放什么 / 谁负责 |\n| --- | --- |\n")
            text += "".join("| `" + path + "` | " + meaning + " |\n" for path, meaning in rows)
            text += "\n" + ("[File map](../MAP.md). The Agent manages structured records after review; people can always add originals to materials/.\n" if en else "[回到总地图](../MAP.md)。Agent 在审阅后维护结构化记录；人始终可以直接补充 materials/ 原件。\n")
            outputs[area + "/README.md"] = text
        for location, description in material_descriptions.items():
            outputs[location + "/README.md"] = marker + "# " + title + "\n\n" + description + "\n\n" + intro + "\n"
        return outputs

    def setup(self, language=None, skill_root=None):
        with self.workspace._lock():
            identity = self.workspace.manifest()
            self.workspace._assert_readable()
            previous = self._settings(identity)
            language = previous["language"] if language is None else language
            # A language-only setup keeps a valid existing package binding. If
            # both saved candidates moved, use the package running this explicit
            # repair; --skill-root selects a different package deliberately.
            if skill_root is None:
                candidates = [self.workspace.root / previous["skill"]["relative_path"], Path(previous["skill"]["absolute_path"])]
                skill_root = next((candidate for candidate in candidates if self._valid_skill(candidate)), None)
            root = self.validate_setup(language, skill_root)
            settings = self._new_settings(identity, language, root)
            catalog = self._load(identity)
            publication = self._publish(catalog, settings=settings, include_guides=True)
            return {"status": "navigation_setup", "workspace_id": identity["workspace_id"], "language": language,
                    "settings_path": SETTINGS, "skill": settings["skill"], "career_records_changed": False,
                    "manifest_changed": False, "scan_performed": False,
                    "preserved_user_guides": publication["preserved_user_guides"], "written_navigation": publication["written"]}

    def _scope(self, scope):
        if scope == "all":
            return scope
        if not isinstance(scope, str):
            raise StoreError("navigation_scope", "Choose an explicit workspace area or directory")
        scope = scope.rstrip("/")
        self.workspace.path(scope)
        parts = scope.split("/")
        if parts[0] not in AREAS or derived_resume_path(scope):
            raise StoreError("navigation_scope", "Navigation checks only inbox/past/present/future directories, excluding derived resumes")
        return scope

    def _empty(self, identity):
        return {"schema_version": SCHEMA, "workspace_id": identity["workspace_id"],
                "updated_at": None, "checks": {}, "entries": {}}

    def _load(self, identity):
        path = self.workspace.path(CACHE)
        if not path.exists():
            return self._empty(identity)
        try:
            with _open_regular(path) as stream:
                raw = stream.read(16 * 1024 * 1024 + 1)
            if len(raw) > 16 * 1024 * 1024:
                raise ValueError("catalog exceeds 16 MiB")
            data = json.loads(raw.decode("utf-8"))
        except (OSError, ValueError, UnicodeError) as exc:
            raise StoreError("navigation_catalog", "Cannot read the previous navigation catalog") from exc
        if not isinstance(data, dict) or data.get("schema_version") != SCHEMA or data.get("workspace_id") != identity["workspace_id"]:
            raise StoreError("navigation_identity", "Catalog format/identity differs; do not reuse it in another workspace")
        if not isinstance(data.get("entries"), dict) or not isinstance(data.get("checks"), dict):
            raise StoreError("navigation_catalog", "Catalog entries/checks are damaged")
        if set(data) != {"schema_version", "workspace_id", "updated_at", "checks", "entries"}:
            raise StoreError("navigation_catalog", "Unexpected catalog fields; it is not career master data")
        if data["updated_at"] is not None:
            try:
                dt.datetime.fromisoformat(data["updated_at"])
            except (ValueError, TypeError):
                raise StoreError("navigation_catalog", "Invalid catalog generation timestamp")
        for scope, checked_at in data["checks"].items():
            self._scope(scope)
            try:
                dt.datetime.fromisoformat(checked_at)
            except (ValueError, TypeError):
                raise StoreError("navigation_catalog", "Invalid catalog check timestamp")
        for relative, entry in data["entries"].items():
            self.workspace.path(relative)
            if relative.split("/")[0] not in AREAS or not isinstance(entry, dict) or entry.get("path") != relative:
                raise StoreError("navigation_catalog", "Catalog contains an invalid entry")
            if (entry.get("area") != relative.split("/")[0] or entry.get("kind") not in {"material", "record", "unplaced"}
                    or entry.get("state") not in STATES or not isinstance(entry.get("title"), str)
                    or set(entry) - {"path", "area", "kind", "title", "state", "checked_at", "stat", "metadata", "link"}):
                raise StoreError("navigation_catalog", "Invalid metadata-only catalog entry")
            if not isinstance(entry.get("stat"), dict) or set(entry["stat"]) != {"size", "mtime_ns", "ctime_ns", "inode", "device"} or any(type(v) is not int for v in entry["stat"].values()):
                raise StoreError("navigation_catalog", "Invalid file metadata in catalog")
            if entry["kind"] == "record":
                self.workspace._metadata(entry.get("metadata"), relative)
            if "link" in entry:
                link = entry["link"]
                if not isinstance(link, dict) or not isinstance(link.get("records"), list) or not link["records"] or not isinstance(link.get("revision"), str) or not isinstance(link.get("stat"), dict):
                    raise StoreError("navigation_catalog", "Invalid source/record association")
                for record in link["records"]:
                    self.workspace._canonical(record, allow_original=False)
        return data

    def _header(self, relative):
        try:
            with _open_regular(self.workspace.path(relative)) as stream:
                first = stream.readline().decode("utf-8")
                if first.rstrip("\r\n") != "---":
                    raise StoreError("frontmatter", "Formal Markdown needs frontmatter; put ordinary notes in a materials/ entry: " + relative)
                lines, total = [first], len(first.encode("utf-8"))
                for raw_line in stream:
                    line = raw_line.decode("utf-8")
                    total += len(raw_line)
                    if total > MAX_DOCUMENT_BYTES:
                        raise StoreError("too_large", "Frontmatter exceeds the read limit: " + relative)
                    lines.append(line)
                    if line.rstrip("\r\n") == "---":
                        break
            metadata, _ = parse_document("".join(lines))
        except (OSError, UnicodeError) as exc:
            raise StoreError("navigation_read", "Cannot read formal metadata: " + relative) from exc
        self.workspace._metadata(metadata, relative)
        return metadata

    def _scan(self, scope, checked_at):
        entries = {}
        starts = AREAS if scope == "all" else (scope,)
        for start in starts:
            start_path = self.workspace.path(start)
            if not start_path.exists():
                if start == "inbox":
                    continue  # Older MD workspaces may not have used this entry.
                raise StoreError("navigation_scope_missing", "Directory is missing: " + start)
            if not start_path.is_dir():
                raise StoreError("navigation_scope", "refresh expects a directory: " + start)
            pending = [start]
            while pending:
                directory = pending.pop()
                try:
                    with os.scandir(self.workspace.path(directory)) as stream:
                        children = sorted(stream, key=lambda entry: entry.name)
                except OSError as exc:
                    raise StoreError("navigation_read", "Cannot list directory: " + directory) from exc
                for child in children:
                    relative = directory + "/" + child.name
                    path = self.workspace.path(relative)  # Rejects symlink components.
                    try:
                        info = path.lstat()
                    except OSError as exc:
                        raise StoreError("navigation_read", "Cannot inspect: " + relative) from exc
                    if stat.S_ISDIR(info.st_mode):
                        if not derived_resume_path(relative) and (material_path(relative + "/_") or child.name not in {".luji", "views", "__pycache__"}):
                            pending.append(relative)
                        continue
                    if not stat.S_ISREG(info.st_mode):
                        raise StoreError("not_regular", "Navigation refuses special files: " + relative)
                    if child.name == ".DS_Store" or (relative.startswith("past/originals/") and child.name.endswith(".receipt.json")):
                        continue
                    if child.name == "README.md" and owned_guide(self.workspace.root, relative, self.workspace.manifest()["workspace_id"]):
                        continue
                    entry = {"path": relative, "area": relative.split("/")[0],
                             "checked_at": checked_at, "stat": stamp(info)}
                    if material_path(relative):
                        entry.update(kind="material", title=child.name, state="pending")
                    elif child.name.endswith(".md"):
                        metadata = self._header(relative)
                        if stamp(path.stat()) != entry["stat"]:
                            raise StoreError("navigation_changed", "Formal metadata changed during discovery; retry: " + relative)
                        entry.update(kind="record", title=metadata["title"], state="record", metadata=metadata)
                    else:
                        # Unexpected binary/text files remain visible; they are
                        # not silently admitted as canonical fact sources.
                        entry.update(kind="unplaced", title=child.name, state="unplaced")
                    entries[relative] = entry
        return entries

    def _marker(self, identity):
        return "<!-- luji-navigation:" + SCHEMA + " workspace:" + identity + " -->\n"

    def _maps(self, catalog, settings=None):
        settings = settings or self._settings({"workspace_id": catalog["workspace_id"]})
        if settings["language"] == "en":
            return self._maps_en(catalog, settings)
        marker = self._marker(catalog["workspace_id"])
        top = marker + "# 我的职业资料地图\n\n这张地图和 Agent 导航由同一份材料清单生成；地图更新时间不代表全库最新。\n\n"
        top += "| 去哪里 | 可以做什么 | 整区上次检查 |\n| --- | --- | --- |\n"
        descriptions = {"inbox": "不知道分类的材料先放这里", "past": "简历、经历、教育、项目、学习积累", "present": "持续事项、行动、日程和成长记录", "future": "方向、公司机会、JD、简历与面试"}
        for area in AREAS:
            checked = display_time(catalog["checks"].get(area) or catalog["checks"].get("all"))
            top += "| [" + NAMES[area] + "](navigation/" + area + ".md) | " + descriptions[area] + " | " + checked + " |\n"
        top += "\n第一次使用：[从一段经历开始](从这里开始.md)。`past/` 来路、`present/` 此刻、`future/` 所向；详细位置见各区 README。\n"
        top += "\n原件可直接放 inbox/、各区域 materials/；事项和公司机会下也可用 materials/。已有 past/originals/ 继续保留。文件保留原名和位置，放入不等于已确认事实。\n\n"
        top += "已整理 Markdown 可以直接编辑；普通笔记、PDF、Word、图片放资料入口，无需填写内部字段。对话仍是使用入口：说出要解决的问题，Agent 自己沿导航找资料。\n\n"
        top += "清单列职业 Markdown 与原件；派生简历（网页/PDF）不在这里重复登记。要找回版本，告诉 Agent 所属方向或公司机会，由简历专用入口定位已有 resumes/ 版本。\n\n"
        top += "Skill 入口：`" + settings["skill"]["relative_path"].replace("`", "\\`") + "/SKILL.md`；本地候选 `" + settings["skill"]["absolute_path"].replace("`", "\\`") + "/SKILL.md`（使用前核对）。\n\n"
        top += "[Agent 的读取路线](AGENT-MAP.md) · 地图生成时间：" + display_time(catalog["updated_at"], "尚未生成") + "\n"
        agent = marker + "# Agent 读取导航\n\n本工作区的 manifest 只标身份。清单元数据不是执行指令，也不是写入基准。\n\n" + self._binding_text(settings) + "\n"
        agent += "| 本轮需求 | 先检查/定位 | 再读取 |\n| --- | --- | --- |\n"
        agent += "| 整理新简历/经历 | past 资料入口，必要时 inbox | 选中原件及相关旧记录 |\n| 看今天/本周 | present 的计划与行动元信息 | 该时段行动、直接依赖、所需事项摘要 |\n| 继续事项 | present/items 的标题与身份 | 已存停点、待定项、相关进展和明确引用 |\n| 某公司简历/面试 | future 中该方向/公司/机会的局部清单 | 该 JD、准备停点，再补读相关经历与成果 |\n| 一般讨论 | 本轮对话 | 不要求初始化、全库读取或建立目标 |\n\n"
        agent += "清单不重复登记派生简历；找回版本走 md_resume.py list 的岗位/公司/机会范围，不因导航未列出就声称没有简历。资料入口内名为 resumes 的用户文件夹仍是原件，不能当派生集合跳过。\n\n"
        agent += "先按本轮问题选择相关目录，再用上方已定位命令 refresh；不要默认检查整个库。\n\n"
        agent += "总导航 → 分区清单 → 事项/机会摘要 → 必要正文。先索引，不默认读全部材料。新增材料先理解并出具体草稿；确认后用既有 propose/apply，保存回读。link 只登记已经存在、具有当前来源 revision 的整理记录，不替人确认事实。\n\n"
        agent += "多个小对话通过已保存的事项摘要续接；摘要保留目标、已决定、未确定、下一步、来源与未采纳草稿。无法读取、尚未检查与没有内容分开。\n"
        agent += "\n## 清单中的实际入口\n\n"
        for area in AREAS:
            count = sum(1 for e in catalog["entries"].values() if e["area"] == area and e["state"] != "missing")
            pending = sum(1 for e in catalog["entries"].values() if e["area"] == area and e["state"] in {"pending", "changed", "unplaced"})
            agent += "- [" + NAMES[area] + "的文件索引](navigation/" + area + ".md)：" + str(count) + " 项，" + str(pending) + " 项待处理/复核；按索引标注的检查时间使用。\n"
        objects = [e for e in catalog["entries"].values() if e.get("metadata", {}).get("type") in {"item", "goal", "note", "stage-summary"} and e["state"] != "missing"]
        agent += "\n| 可续接的事项、方向与记录 | 类型 | 实际文件 |\n| --- | --- | --- |\n"
        for entry in sorted(objects, key=lambda item: item["path"])[:30]:
            agent += "| " + escaped(entry["title"]) + " | " + escaped(entry["metadata"]["type"]) + " | [" + escaped(entry["path"]) + "](" + quote(entry["path"], safe="/") + ") |\n"
        if len(objects) > 30:
            agent += "\n此处仅列按路径排列的前30项，不代表优先级。完整对象按对应 scope 查询清单。\n"
        maps = {"MAP.md": top, "AGENT-MAP.md": agent}
        for area in AREAS:
            records = [e for e in catalog["entries"].values() if e["area"] == area]
            body = marker + "# " + NAMES[area] + " · 材料目录\n\n"
            body += "整区上次检查：" + display_time(catalog["checks"].get(area) or catalog["checks"].get("all")) + "。\n"
            partial = [(s, t) for s, t in catalog["checks"].items() if s.startswith(area + "/")]
            if partial:
                body += "最近局部检查：" + "；".join(escaped(s) + "（" + display_time(t) + "）" for s, t in sorted(partial)) + "。\n"
            body += "\n只列路径与元信息，不含正文；状态是上次核对结果，内容版本须在实际使用时重读。\n\n"
            body += "| 名称 | 位置 | 状态 | 关联整理记录 |\n| --- | --- | --- | --- |\n"
            for entry in sorted(records, key=lambda item: item["path"]):
                relative = entry["path"]
                label = escaped(entry.get("title", Path(relative).name))
                location = escaped(relative)
                linked = entry.get("link", {}).get("records", [])
                links = "、".join("[" + escaped(p) + "](../" + quote(p, safe="/") + ")" for p in linked) or "—"
                body += "| [" + label + "](../" + quote(relative, safe="/") + ") | " + location + " | " + STATES.get(entry["state"], escaped(entry["state"])) + " | " + links + " |\n"
            if not records:
                body += "\n该清单尚无条目；请结合上方检查时间判断，未检查不能当作空库。\n"
            body += "\n[返回总地图](../MAP.md)\n"
            maps["navigation/" + area + ".md"] = body
        return maps

    def _maps_en(self, catalog, settings):
        marker = self._marker(catalog["workspace_id"])
        descriptions = {"inbox": "Unsure where material belongs", "past": "Experience, education, projects and learning evidence",
                        "present": "Continuing items, actions, plans and growth records", "future": "Directions, company opportunities, JD, resumes and interviews"}
        names = {"inbox": "Inbox", "past": "Past", "present": "Present", "future": "Future"}
        states = {"pending": "Needs review", "processed": "Linked to reviewed records", "changed": "Changed; review again", "missing": "Missing from original location", "record": "Structured Markdown", "unplaced": "Move to a materials/ entry"}
        top = marker + "# Your career file map\n\n[Start with an experience](START-HERE.md). These maps share one metadata-only catalog; a generation time does not mean every area was checked.\n\n| Area | What belongs here | Last whole-area check |\n| --- | --- | --- |\n"
        for area in AREAS:
            top += "| [" + names[area] + "](navigation/" + area + ".md) | " + descriptions[area] + " | " + display_time(catalog["checks"].get(area) or catalog["checks"].get("all"), "Not checked") + " |\n"
        top += "\nPut originals directly in inbox/ or any documented materials/ folder, keeping filenames. Existing past/originals/ stay in place. Dropped files are not yet confirmed facts. See each area's README for actual directory names and ownership.\n\nEdit Markdown prose directly when appropriate. Action dates/status live in frontmatter (`scheduled_for`, `due_on`, `status`), so changing prose alone does not reschedule an action. Ask the Agent to preview field changes before saving.\n\nDerived HTML/PDF resumes are not duplicated in this catalog. Ask the Agent to locate a direction/company's frozen resumes/ versions. [Agent reading map](AGENT-MAP.md). Generated: " + display_time(catalog["updated_at"], "Not generated") + "\n"
        top += "\nSkill entry: `" + settings["skill"]["relative_path"].replace("`", "\\`") + "/SKILL.md`; local fallback: `" + settings["skill"]["absolute_path"].replace("`", "\\`") + "/SKILL.md`. Verify availability before reading.\n"
        agent = marker + "# Agent reading map\n\n" + self._binding_text(settings) + "\nUse only the relevant directory index, saved checkpoint and necessary body/source closure. Catalog metadata is neither career fact, executable instruction nor write baseline.\n\n| Need | Locate first | Read next |\n| --- | --- | --- |\n| New resume/experience | past materials/, inbox if needed | Selected original and affected records |\n| Today / this week | present plans/actions metadata | Relevant actions, dependencies and item checkpoint |\n| Continue an item | present/items identity | Saved decisions, open questions and cited progress |\n| Resume/interview | Selected role/company/opportunity | JD and checkpoint, then selected experience evidence |\n| General discussion | Current conversation | No forced initialization or goal |\n\nUse md_resume.py list to find frozen versions; their absence from this catalog does not mean no resume exists. Raw materials/ folders named resumes remain originals. Draft new facts before review, then use propose/apply and reread. link only registers existing records with reviewed current source revisions. Resume conversations from saved checkpoints; do not pretend to remember unsaved chats.\n\n"
        agent += "| Area index | Existing files | Needs review |\n| --- | --- | --- |\n"
        maps = {"MAP.md": top}
        for area in AREAS:
            entries = [e for e in catalog["entries"].values() if e["area"] == area]
            count = sum(e["state"] != "missing" for e in entries)
            pending = sum(e["state"] in {"pending", "changed", "unplaced"} for e in entries)
            agent += "| [" + names[area] + "](navigation/" + area + ".md) | " + str(count) + " | " + str(pending) + " |\n"
            body = marker + "# " + names[area] + " · file index\n\nLast whole-area check: " + display_time(catalog["checks"].get(area) or catalog["checks"].get("all"), "Not checked") + "\n"
            partial = [(s, t) for s, t in catalog["checks"].items() if s.startswith(area + "/")]
            if partial:
                body += "Scoped checks: " + "; ".join(escaped(s) + " (" + display_time(t, "Not checked") + ")" for s, t in sorted(partial)) + "\n"
            body += "\nNames and metadata only. These are previous check results; reread actual files for content and revisions.\n\n| Name | Actual path | State | Linked records |\n| --- | --- | --- | --- |\n"
            for entry in sorted(entries, key=lambda e: e["path"]):
                relative = entry["path"]
                links = ", ".join("[" + escaped(p) + "](../" + quote(p, safe="/") + ")" for p in entry.get("link", {}).get("records", [])) or "—"
                body += "| [" + escaped(entry["title"]) + "](../" + quote(relative, safe="/") + ") | " + escaped(relative) + " | " + states[entry["state"]] + " | " + links + " |\n"
            if not entries:
                body += "\nNo entries in this catalog; an unchecked area is not an empty workspace.\n"
            maps["navigation/" + area + ".md"] = body + "\n[Back to file map](../MAP.md)\n"
        objects = [e for e in catalog["entries"].values() if e.get("metadata", {}).get("type") in {"item", "goal", "note", "stage-summary"} and e["state"] != "missing"]
        agent += "\n| Saved work, directions and checkpoints | Type | Actual record |\n| --- | --- | --- |\n"
        for entry in sorted(objects, key=lambda e: e["path"])[:30]:
            agent += "| " + escaped(entry["title"]) + " | " + escaped(entry["metadata"]["type"]) + " | [" + escaped(entry["path"]) + "](" + quote(entry["path"], safe="/") + ") |\n"
        if len(objects) > 30:
            agent += "\nOnly the first 30 paths are shown, not priority order. Query the relevant scope for all objects.\n"
        maps["AGENT-MAP.md"] = agent
        return maps

    def _publish(self, catalog, settings=None, include_guides=False):
        settings = settings or self._settings({"workspace_id": catalog["workspace_id"]})
        outputs = {path: text.encode("utf-8") for path, text in self._maps(catalog, settings).items()}
        preserved_user_guides = []
        if include_guides:
            for path, text in self._guides(catalog["workspace_id"], settings).items():
                target = self.workspace.path(path)
                if not target.exists() or owned_guide(self.workspace.root, path, catalog["workspace_id"]):
                    outputs[path] = text.encode("utf-8")
                else:
                    preserved_user_guides.append(path)
            outputs[SETTINGS] = json_bytes(settings)
        outputs[CACHE] = json_bytes(catalog)
        if len(outputs[CACHE]) > 16 * 1024 * 1024:
            raise StoreError("navigation_catalog", "Catalog exceeds 16 MiB; narrow the workspace")
        before = {}
        marker = self._marker(catalog["workspace_id"]).encode()
        for relative in outputs:
            target = self.workspace.path(relative)
            if target.exists():
                try:
                    with _open_regular(target) as stream:
                        old = stream.read(16 * 1024 * 1024 + 1)
                except OSError as exc:
                    raise StoreError("navigation_read", "Cannot preserve previous map: " + relative) from exc
                if relative in GUIDE_PATHS and not owned_guide(self.workspace.root, relative, catalog["workspace_id"]):
                    raise StoreError("navigation_owned", "Guide ownership changed during setup: " + relative)
                if relative not in {CACHE, SETTINGS} and relative not in GUIDE_PATHS and not old.startswith(marker):
                    raise StoreError("navigation_owned", "Will not overwrite a user-authored or foreign map: " + relative)
                before[relative] = old
            else:
                before[relative] = None
        attempted = []
        try:
            for relative, value in outputs.items():
                # Recheck to avoid replacing a manual edit after preflight.
                target = self.workspace.path(relative)
                current = target.read_bytes() if target.exists() else None
                if current != before[relative]:
                    raise StoreError("navigation_conflict", "Map changed during generation: " + relative)
                # atomic_write can replace the destination and then report a
                # directory-fsync error. Include that attempted destination in
                # recovery even when the call never returns successfully.
                attempted.append(relative)
                atomic_write(target, value)
        except (StoreError, OSError):
            for relative in reversed(attempted):
                target = self.workspace.path(relative)
                current = target.read_bytes() if target.exists() else None
                if current != outputs[relative]:
                    continue  # Preserve an external edit during recovery.
                if before[relative] is None:
                    target.unlink()
                else:
                    atomic_write(target, before[relative])
            raise
        return {"written": sorted(outputs), "preserved_user_guides": preserved_user_guides}

    def _result(self, catalog, scope, status):
        selected_areas = AREAS if scope == "all" else (scope.split("/")[0],)
        return {"status": status, "workspace_id": catalog["workspace_id"], "scope": scope,
                "catalog_updated_at": catalog["updated_at"], "checked_scopes": catalog["checks"],
                "freshness": "checked_names_and_metadata_not_contents" if status == "refreshed" else "cached_not_refreshed",
                "entries": [copy.deepcopy(e) for p, e in sorted(catalog["entries"].items()) if within(p, scope)],
                "maps": ["MAP.md", "AGENT-MAP.md"] + ["navigation/" + area + ".md" for area in selected_areas],
                "read_bodies": False, "not_a_write_baseline": True}

    def refresh(self, scope="all"):
        scope = self._scope(scope)
        with self.workspace._lock():
            identity = self.workspace.manifest()
            self.workspace._assert_readable()
            old = self._load(identity)
            checked = now()
            found = self._scan(scope, checked)
            catalog = copy.deepcopy(old)
            for relative, entry in found.items():
                previous = old["entries"].get(relative, {})
                link = previous.get("link")
                if link and entry["kind"] == "material":
                    entry["link"] = link
                    unchanged = entry["stat"] == link.get("stat")
                    for record in link["records"]:
                        target = self.workspace.path(record)
                        try:
                            current = stamp(target.stat()) if target.exists() else None
                        except OSError as exc:
                            raise StoreError("navigation_read", "Cannot inspect linked record: " + record) from exc
                        unchanged = unchanged and current == link.get("record_stats", {}).get(record)
                    entry["state"] = "processed" if unchanged else "changed"
                catalog["entries"][relative] = entry
            for relative, previous in old["entries"].items():
                if within(relative, scope) and relative not in found:
                    entry = copy.deepcopy(previous)
                    entry.update(state="missing", checked_at=checked)
                    catalog["entries"][relative] = entry
            catalog["checks"][scope] = checked
            catalog["updated_at"] = checked
            if self.workspace.manifest()["workspace_id"] != identity["workspace_id"]:
                raise StoreError("navigation_identity", "Workspace identity changed during discovery")
            self._publish(catalog)
            return self._result(catalog, scope, "refreshed")

    def catalog(self, scope="all"):
        scope = self._scope(scope)
        identity = self.workspace.manifest()
        self.workspace._assert_readable()
        return self._result(self._load(identity), scope, "indexed")

    def link(self, material, records):
        self.workspace.path(material)
        if not material_path(material):
            raise StoreError("navigation_material", "Choose an original in a documented material entry")
        if not isinstance(records, (list, tuple)) or not records or not all(isinstance(p, str) for p in records):
            raise StoreError("navigation_records", "Choose explicit existing formal records")
        records = list(dict.fromkeys(records))
        with self.workspace._lock():
            identity = self.workspace.manifest()
            previous = self._load(identity)
            try:
                before_stats = {relative: stamp(self.workspace.path(relative).stat()) for relative in [material, *records]}
            except FileNotFoundError as exc:
                raise StoreError("missing_source", "A selected material or record is missing") from exc
            context = self.workspace.context([material, *records])
            by_path = {d["path"]: d for d in context["documents"]}
            revision = context["draft_base"]["files"].get(material)
            if revision is None:
                raise StoreError("missing_source", "Material is missing: " + material)
            for relative in records:
                doc = by_path.get(relative)
                metadata = doc.get("metadata", {}) if doc else {}
                expected = metadata.get("source_revisions", {}).get(material)
                if metadata.get("type") == "source" or material not in metadata.get("sources", []) or not isinstance(expected, str):
                    raise StoreError("navigation_link", "A formal record must explicitly cite this material and its reviewed source revision: " + relative)
                if expected.removeprefix("sha256:") != revision.removeprefix("sha256:"):
                    raise StoreError("conflict", "Material changed since the record's reviewed source version: " + material)
            self.workspace._verify_base(context["draft_base"])
            try:
                after_stats = {relative: stamp(self.workspace.path(relative).stat()) for relative in before_stats}
            except FileNotFoundError as exc:
                raise StoreError("conflict", "A selected material or record disappeared during linking") from exc
            if after_stats != before_stats:
                raise StoreError("conflict", "A selected material or record changed during linking; reread before registering it")
            material_stat = before_stats[material]
            record_stats = {relative: before_stats[relative] for relative in records}
            checked = now()
            entry = {"path": material, "area": material.split("/")[0], "kind": "material", "title": Path(material).name,
                     "checked_at": checked, "stat": material_stat, "state": "processed",
                     "link": {"records": records, "revision": revision, "stat": material_stat, "record_stats": record_stats, "linked_at": checked}}
            catalog = copy.deepcopy(previous)
            catalog["entries"][material] = entry
            catalog["updated_at"] = checked
            if self.workspace.manifest()["workspace_id"] != identity["workspace_id"]:
                raise StoreError("navigation_identity", "Workspace identity changed during linking")
            self._publish(catalog)
            return {"status": "linked", "workspace_id": identity["workspace_id"], "entry": entry,
                    "semantic_confirmation": "Agent must obtain user review; this command verifies structure and source version only"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("refresh", "catalog"):
        command = commands.add_parser(name)
        command.add_argument("--scope", default="all")
    setup = commands.add_parser("setup")
    setup.add_argument("--language", choices=("zh", "en"))
    setup.add_argument("--skill-root")
    command = commands.add_parser("link")
    command.add_argument("--material", required=True)
    command.add_argument("--record", action="append", required=True, dest="records")
    args = parser.parse_args(argv)
    try:
        nav = NavigationWorkspace(args.workspace)
        if args.command == "setup":
            result = nav.setup(language=args.language, skill_root=args.skill_root)
        elif args.command == "link":
            result = nav.link(args.material, args.records)
        else:
            result = getattr(nav, args.command)(args.scope)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (StoreError, OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"status": "error", "code": getattr(exc, "code", "navigation_error"),
                          "message": str(exc), "previous_catalog_preserved_on_read_failure": True}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
