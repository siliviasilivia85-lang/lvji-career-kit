# 履迹 LüJi

[简体中文](README.md) · English · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md)

**Let your familiar Agent become a career adviser: know you first, then break goals into daily doable steps.**

AI lets us imagine many versions of ourselves; LüJi helps you put that imagination into each day’s schedule.

Send this sentence to your Agent (Claude Code, Codex, Cursor, or another Agent that can read and write local files):

```text
请从 https://github.com/siliviasilivia85-lang/lvji-career-kit 安装并启用这个 Skill，先陪我梳理一段经历。
```

[Installation and host options](references/install.md) · Install once, then just say what you need.

It will:

1. **Know you first:** Read your résumé, current work, and projects you have done, and organize them into records you can check.
2. **Set goals with you:** A promotion, leading a project, learning a new skill, or trying a new direction are all fine. You can start talking even if you have not thought it through.
3. **Break them into daily tasks:** Schedule by the time you can actually spare this week. If you are busy, shrink one step instead of starting over.
4. **Pick up where you left off:** Finished work is archived after you confirm it. In a new conversation, it continues from where you stopped.

![Fictional demo: a unified plan that schedules actions by the time you can spare each week](assets/readme-plan.jpg)

Your materials stay on your own computer · No extra model key required · It does not apply or contact anyone for you · MIT open source

## Why LüJi

AI is lowering the barrier to learning and hands-on practice. One person can try more things; abilities that once belonged to different roles now cross and combine; the boundaries of a career are changing too. More choices do not necessarily make the direction clearer: time is still limited, and which knowledge is worth learning, which projects are worth doing, and where past experience can still be used all have to be seen more clearly through trying.

Career development does not only happen when you are looking for a job. Working toward a promotion, taking on greater responsibility, or moving into a new field all need everyday accumulation. We already bring these questions to AI; it can talk with us and help us analyse. But if ideas stay only in scattered conversations, the Agent can refer only to the part spoken at the time. Advice easily remains generic, and a new conversation or tool means explaining everything again.

LüJi packages a career-development method, a materials directory, and file tools into a Skill for the Agent you already use. It starts from your existing experience and abilities, discusses direction with you, breaks down the knowledge and practice a goal needs, and fits that work into the time you can spare each day. Outputs you have checked, learning records, and real feedback are saved. As those records accumulate, it understands your experience, preferences, and real constraints in more specific terms, and you can inspect, add to, and correct that understanding at any time.

![LüJi: a career-development framework connecting past, present, and future](assets/career-overview.svg)

## How LüJi works

### Past: organize existing experience and keep real evidence

Give the Agent earlier résumés, work and project materials, learning notes, education records, or awards—or place them directly in the workspace material folders. The Agent organizes them by topic, keeps the originals and their sources, and draws out specific experiences. You can add missing details and correct its understanding at any time.

Past plans, work actually completed, and confirmed outcomes are recorded separately. When you want to sort out personal traits or abilities, the Agent offers a judgment based on the actual materials, for you to check and revise. Those judgments can also change as new practice comes in.

### Present: break goals into everyday work and learning

You can start from current work, a project you want to do, or a direction you have not yet thought through. The Agent uses your experience, current progress, the goal’s requirements, and the time you can give it to help you find knowledge and practice worth adding, then breaks them into concrete projects, stage outcomes, and daily, weekly, and monthly actions.

Learning progress, work outputs, and feedback can be added as they happen. Reviewing a plan keeps the existing arrangements; a small adjustment changes only the related items. If time runs short, a goal changes, or progress stalls, decide together whether to shrink, postpone, pause, or continue. You can begin without a complete archive of the past.

### Future: explore directions and prepare for career change

You may want a promotion, new responsibilities, another role, or a project of your own. Save the direction and the thinking behind it at the time. You do not need an existing job description to discuss a goal. When a specific role is involved, gather requirements, compare directions and companies, and connect them with your experience and current accumulation to sort out evidence, gaps, and questions still to answer.

When you actually enter a job search—and need to tend several directions, multiple résumé versions, interviews, and progress at once—all of that can reuse the same accumulation:

- **Résumés:** Choose relevant experience and confirmed outcomes for a role or company, and generate an independently saved HTML résumé. There are six layouts; use a photograph you specify, or none. After you review that exact web version, export the same version as a PDF with already installed Chrome/Chromium.
- **Interview preparation:** Organize project stories, role questions, and talking points. Prepare materials by company and round, practise question by question, and keep a review after the actual interview.
- **Opportunity tracking:** Record each company’s and role’s application stage, the résumé version actually used, feedback, and the next step. You can view overall progress or a single role or opportunity. Real feedback can also return to the present as new practice and action suggestions.

### Keep going: let each discussion connect to the next

Experience, actions, plans, and outcomes live in readable local files. You and the Agent each have a materials map. New files can go straight into the folders; when the Agent handles a related question, it checks that range for changes and reads what it needs. Important content becomes a concrete draft first, and is kept after you confirm it.

In a new conversation, the Agent recovers the goal, where you stopped, and the next step from saved item summaries. What it knows about you comes from the experience, outcomes, and discussion results you choose to save; unsaved chats are not treated as long-term memory. You can check sources, edit records, and adjust how it understands you.

## Quick start: begin with one piece of experience

The first time, pick something you know well: a project you did, a period of work, or a piece of learning. Part of an existing résumé, a project review, or learning notes is enough. If you have no document at hand, you can write down what happened. You do not need a complete career archive in one go.

If you have no past materials yet, you can start from what you want to do now. Experience can be added later; an idea that is not yet decided can also be saved on its own.

1. **Install and create a workspace.** Send the sentence at the top to your Agent. It will install the Skill; when materials need to be saved, it creates your personal workspace outside the install directory (new users: `~/lvji-workspace/`) and generates a first-use guide and map in Chinese or English, as you choose. The Chinese entrance is `从这里开始.md`; the English entrance is `START-HERE.md`. This is only for first use; after that, talk as usual. If you have already downloaded the package locally, you can also ask the Agent to install from the current folder. The full file workflow needs an Agent that can read, write, and execute local files, plus Python 3.10+.
2. **Put this experience’s materials in.** Place them in the workspace `past/materials/`; if you do not yet know how to classify them, use `inbox/`. You can also give the Agent an attachment and ask it to import and organize it. Originals you drop in keep their names and locations. Ordinary notes, PDFs, Word files, or images do not need internal fields; whether an attachment can be read reliably depends on the Agent you use.
3. **Organize and check it together.** The Agent extracts what you did, what you owned, and what you produced, drafts an experience record, and marks sources and open questions. You add missing pieces, correct its understanding, and after you confirm it, the draft is saved as a readable Markdown record; the original stays. You can also edit the record body yourself. Task dates and status have dedicated fields; asking the Agent to adjust them is the easiest path.
4. **Look at it in Overview.** Ask the Agent to generate and show the workbench. In “Overview → past and current understanding,” open the record you just organized and check the body and sources. If something is inaccurate, ask the Agent to change it, or edit the Markdown yourself and regenerate the page. The web page is currently for viewing and selection; edits go through the Agent or the files, and are not saved directly in the page.
5. **Take a next step from this accumulation.** Using what you want to do now and the time you can spare, discuss a project or action worth moving forward. It can connect to a future direction, or stand on its own. After you decide to save it, check the arrangement in the unified plan.

When this first pass is done, you should be able to find the original, read the organized record, know how to correct it, and continue from here in the next discussion. To try the flow with fictional materials first, ask the Agent to follow the [trial guide](examples/try-it.md) in a new temporary directory.

## FAQ

**What kind of Agent do I need?** An Agent that can read, write, and execute local files, such as Claude Code, Codex, or Cursor. The file helpers need Python 3.10+. A chat-only host can discuss and draft, but cannot finish local saving. See the [host notes](references/hosts.md) for each environment.

**Do I need an API key?** No extra model key is required. LüJi reuses the conversation and tool abilities of the Agent you already use. The local file helpers do not call a model.

**Where does my data live?** In a personal workspace on your computer, as readable Markdown files, not published with the source. Conversation content is still sent to the model service of the Agent you use, in that Agent’s usual way.

**Can I use it without a résumé?** Yes. Start from what you want to do now, and add experience later.

**Is it only for people preparing to look for a job?** No. Promotions, leading a project, learning a new skill, or trying a new direction can all start from the work in front of you.

**If I open a new conversation, does it still remember?** It remembers what you chose to save: experience, outcomes, decisions, and item summaries. Unsaved chats are not treated as long-term memory.

**Will it remind me of daily tasks?** There is currently no built-in background reminder or live sync. When you need it, open the workbench, or ask the Agent what to do today. Notifications depend on the host.

**Will it apply or contact employers for me?** No. Application progress is updated only from actual events you provide.

## Further details

The following is for people who have already started, or who want the file-level detail. Expand a section to read it.

<details>
<summary><strong>Where everyday materials go</strong></summary>

All paths below are inside your personal career workspace. New users should use `~/lvji-workspace/`, outside the Skill install directory. Existing workspaces keep their current path; nothing is moved automatically.

| What you have | Where to put it |
| --- | --- |
| Old résumés, certificates, past work and project materials, learning notes | `past/materials/`; you can add topic subfolders |
| Shared current materials, or materials for an item in progress | `present/materials/` or `present/items/<item>/materials/` |
| Job descriptions or direction research not yet assigned | `future/materials/` |
| A direction’s or company opportunity’s JD, screenshots, and feedback | The `materials/` folder under that direction or opportunity |
| Anything you cannot yet classify | `inbox/` |

Workspace `MAP.md` is the materials map for you; `AGENT-MAP.md` is the Agent’s reading guide. Both come from the same catalog. You can drop files in directly. The next time the Agent handles a related question, it checks that range for changes, reads what it needs, and reviews the organized result with you. Finding a file, understanding the material, and confirming an experience are different steps.

Section guides, the materials map, and the first-use entrance are generated in Chinese or English. Physical paths stay `past/`, `present/`, and `future/`; the map explains in the language you chose what belongs where. Your own filenames and subfolders can use your preferred language. That way, changing language or Agent does not break existing references and versions, and you do not need to move the materials.

[Materials map for people](references/map.en.md) · [Agent reading route](references/agent-map.en.md) · [Directories and material status](references/navigation.md)

</details>

<details>
<summary><strong>What visualizations exist now</strong></summary>

**The main workbench is four views in the same web page, generated together at `views/overview.html` in your personal workspace.** Open that one file and switch with the top tabs.

| View | What you see | Where to continue |
| --- | --- | --- |
| **Overview** | Active items, today’s actions, recent learning and work progress, plus expandable completed or paused items, ideas, and stage reviews | Open items and sources; past records expand under “past and current understanding” |
| **Unified plan** | Daily actions, weekly calendar, monthly calendar, yearly month cards, plus the related plan notes and actual records | Switch time scale and inspect actions; ask the Agent when the schedule needs to change |
| **Directions** | Career directions in a horizontal layout, related requirements and evidence support, information coverage, and your preferences | Sort and compare, open direction and company JD details, and view résumé and interview materials |
| **Applications** | Each company opportunity’s stage, next step, history, the résumé version actually used, and feedback | View all opportunities, or filter by direction, company, opportunity, and stage; if the version used was not recorded, it stays explicitly empty |

A few kinds of content are easy to mistake for separate panels:

- **Past experience** expands inside Overview. There is currently no separate top-level “past” page; find originals and organization status from `MAP.md`.
- **Interview materials** open inside direction or application details. There is no second interview home page.
- **Web résumés** are independently saved HTML. The common version for a role lives in `future/roles/<role>/common/resumes/<version>/`; a company version lives in that opportunity’s `resumes/<version>/`. Enter them from “existing résumé versions” in the details. The six templates are six layouts, not six workbenches.

Pages are generated on demand from saved files. Filtering, sorting, and viewing can happen in the page. Changes to a record body, a task date, or an application status go to the Agent, which shows the diff; you confirm, then refresh—or edit the Markdown yourself. “Ask the Agent to adjust” is a compatibility control that copies a request; you do not need to copy commands from the page in everyday use. The current page does not write materials back, and has no drag-to-save scheduling.

A filter only changes what is on screen. A full snapshot still contains the career materials read when it was generated; it is not a share link isolated by role. For an external view, ask the Agent to generate a separate document with an explicit content scope.

Entrances, generation, and the operations actually supported are collected in the [visualization guide](references/views.md). The template source is `assets/md_workspace.html`; it becomes a usable page only after workspace data is filled in. You do not need to open the template to look for your own materials.

### Résumé layouts can be previewed first

Before you make a résumé, you can ask the Agent to generate a fictional style gallery: the same experience shown as intro sidebar, classic single column, evidence archive, plain text, projects first, and experience first. You can switch two AI-generated fictional portraits, or use none. When you have chosen, tell the Agent the layout name, then replace the demo with your own experience and photograph.

The gallery also includes seven GitHub web-résumé references, with official samples, suggested uses, and license links. They are external references, shown separately from the six built-in layouts. See the [résumé flow](references/resume.md) for how to open and generate them.

</details>

<details>
<summary><strong>Fictional demo site</strong></summary>

Conversations in the local demo are clearly labeled as fictional examples. The demo strings together “organize experience → explore directions → break into actions → keep the accumulation,” then opens the plan, directions, and résumés to show the result. The demo pages themselves do not run an online Agent, and do not save visitor data.

Maintainers can generate a version suitable for static hosting:

```text
python3 scripts/demo_site.py --output _site
```

The output directory must be new. The demo contains only fictional read-only pages and local assets; it does not export machine paths, a personal workspace, or runtime history. After the repository exists, choose GitHub Actions in Pages, then run the [demo publish workflow](.github/workflows/pages.yml) by hand. Upload only `_site/`, not the whole repository or a career-data directory. Having the workflow ready does not mean a live site already exists.

</details>

<details>
<summary><strong>How files are kept</strong></summary>

```text
lvji-career-kit/              Downloaded Skill package
├── README.md                Guide for users
├── README.en.md             English guide
├── README.ja.md             日本語のガイド
├── README.ko.md             한국어 안내
├── README.es.md             Guía en español
├── SKILL.md                 Agent working entrance
├── AGENTS.md                Folder collaboration entrance
├── references/              Workflows for materials, planning, directions, résumés, interviews, and views
├── prompts/                 Prompts for portrait, gap analysis, interview prep, and review
├── scripts/                 Local file helpers
├── assets/                  Editable page templates
└── examples/                A few fictional trial materials

~/lvji-workspace/             Personal career files, separate from the Skill install directory, not published with the source
├── MAP.md               Materials map
├── AGENT-MAP.md         Agent navigation
├── 从这里开始.md         Chinese first-use entrance; English is START-HERE.md
├── inbox/               Materials not yet classified
├── past/                Past experience and learning
├── present/             Current items, actions, plans, ideas, and stage reviews
├── future/roles/        Directions, company opportunities, résumés, and interview materials
├── views/overview.html  Unified visualization workbench
└── .luji/               Tool-maintained drafts, history, and navigation cache
```

Experience and actions each have their own main file; different directions and daily, weekly, and monthly plans reference the same accumulation. In a new conversation, the Agent recovers the goal, stopping point, and next step from saved item summaries; unsaved chats are not treated as long-term memory. You keep your original materials, and you can view and edit the organized files.

You can edit a record body directly. Action dates and status follow the `scheduled_for`, `due_on`, and `status` metadata. Changing a date only in the prose does not change the schedule. You can ask the Agent to make a local adjustment; if you edit yourself, keep stable IDs, valid JSON values, and existing history.

Some ideas are not yet goals; they can live in `present/notes/`. When a stretch of work, learning, or job search comes to a pause, you can save a stage review in `present/stages/`, citing real outcomes, recording how choices changed, and deciding what is worth carrying into the next stage. It does not automatically close a project or schedule the next round of tasks for you.

A new conversation can open your own workspace directly. It records a verifiable Skill location; if you later move the Skill package, ask the Agent to reconnect it using the [navigation repair notes](references/navigation.md). You do not need to rebuild your career files.

</details>

<details>
<summary><strong>Scope and current progress</strong></summary>

LüJi reuses the conversation, attachment understanding, and tool abilities of an existing Agent. It does not ship a separate model service. Local file helpers need no model key; the full experience depends on the host’s file reading, writing, execution, and display. Pages can be viewed in a host file panel, in the conversation, or in a browser; they are currently local snapshots with a generation time.

Résumés offer six layouts, defaulting to a compact two-column design. A photograph is optional; content keeps its real sources. After you review the exact web version, you can export the same version as a PDF with already installed Chrome/Chromium. Interview preparation reuses the same experience and outcomes; see the [résumé flow](references/resume.md) and [interview flow](references/interview.md). Application progress is updated from actual events you provide; résumés are not sent, and employers are not contacted automatically.

Each build is an independent saved version. A PDF export receipt is bound to that exact version and file; older PDFs or hand-added files without a trusted receipt are marked unverified. Updating a template does not invalidate intact historical HTML; whether career sources have changed is reported separately. Application history can link to the résumé file actually used; when that is unknown, it is recorded as not recorded, not inferred as the latest version.

The README is available in Simplified Chinese, English, Japanese, Korean, and Spanish. Workspace first-use guides and maps currently exist in Chinese and English; choose `zh` or `en` at setup. You can talk with the Agent in your own language; actual understanding depends on the host. Physical directory names stay compatible. Fixed copy on the web workbench is still mainly Chinese, and operational references are mainly in Chinese. This README translation does not mean the full interface is localized.

There is currently no built-in background reminder or live sync; notifications, voice, and similar capabilities depend on the host. Required host capabilities, display fallbacks, and what has actually been verified are in the [host notes](references/hosts.md). Old workspace formats are kept and are not migrated automatically. Tests and gaps are in [TESTING.md](TESTING.md).

</details>

Trial materials are all fictional. Personal career files are not distributed with the source. Page and tool provenance is in [ASSETS.md](ASSETS.md). The project uses the [MIT](LICENSE) license, which permits commercial use.
