# LüJi · A career that keeps growing

[简体中文](README.md) · English · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md)

**Make your Agent a personal career adviser, connecting past experience, today’s actions and future directions.**


```text
Install lvji-career-kit from https://github.com/siliviasilivia85-lang/lvji-career-kit and help me make sense of one past experience.
```

[Installation and host options](references/install.md) · Install once, then speak naturally.

## Why LüJi

Many of us begin thinking seriously about our next role only when our current work no longer leaves room to grow.

Then everything arrives at once: finding old projects, rewriting a résumé, choosing a direction, preparing for interviews. We have done and learned a great deal, but the records are scattered. It is hard to explain what that experience adds up to. Exploring several kinds of roles means preparing several different résumés, often before we have understood what we want from the next step.

A résumé can change in a few days. Meaningful practice and transferable skills take longer. As AI changes the boundaries of work, career development needs a place in everyday life, well before an urgent job search.

**LüJi helps you build a continuous path of career growth: recover what you have learned, bring future possibilities into present action, and carry the results into your next choice.**

It gives an Agent you already use a method, local file tools, and visual snapshots, so it can work with you as a personal career adviser. Your experience stays in readable files that you can inspect, correct, and keep.

## Connect the past, present, and future

**Past — understand the ground you stand on.** Preserve work, projects, education, and learning in small, named records. Keep original materials and their sources, add forgotten details, and revisit what your experience suggests about your strengths and preferences. Your next direction may also depart from your past.

**Present — give growth a place in a real week.** Start with what you want to do and the time you can actually spare. Break a project into useful outcomes and manageable actions. Daily, weekly, monthly, and yearly plans refer to the same actions. When life changes, adjust the relevant commitment rather than rebuilding everything.

**Future — let several possibilities share the same growing experience.** Compare directions and specific opportunities, see what is supported by evidence and what remains unknown, and turn worthwhile gaps into present work. When you decide to apply, reuse your experience and confirmed outcomes to prepare role-specific or company-specific résumés and interview materials. Bring actual feedback back into your next decisions.

Completing a task records progress. A concrete result, checked with you, can support a claim about your abilities. Keeping that distinction makes this path useful over time. You can explore without creating a goal, save an idea without starting a project, and close a stage without committing to another one.

## Start with one piece of experience

Choose something familiar: a past project, a period of work, or a learning experience. An old résumé, a project retrospective, or a few notes are enough. You do not need a complete career archive.

If you have no past materials to add, start with what you want to explore now. You can add experience later, or save an idea on its own without creating a goal or schedule.

1. **Set up a workspace.** Open or authorize access to this downloaded package in your usual Agent. Ask it to read the root `AGENTS.md` and `SKILL.md`, create a personal workspace in English, and show its map. This is a first-use step; ordinary conversation is enough afterward. The full file workflow requires local file reading, writing, execution, and Python 3.10+.
2. **Add the material.** Place it in the workspace’s `past/materials/`, or use `inbox/` if you are unsure. You can also give the Agent an attachment and ask it to import and organize it. Directly added originals keep their names and locations. Ordinary Markdown, PDF, Word documents, and images do not need internal metadata. Attachment understanding depends on the host Agent.
3. **Review the account together.** The Agent drafts what happened, what you contributed, and what you produced, with sources and uncertainties. Correct it and approve the specific draft before it becomes a formal Markdown record. Originals remain available.
4. **Look at the result.** Ask for the workbench. In Overview, expand the past records area and open the saved record and its sources. Correct it through the Agent or by editing the Markdown, then regenerate the snapshot. The web page currently supports viewing and selection; it does not save edits directly.
5. **Choose a useful next step.** Discuss a project or action that fits your current circumstances. It may support a future direction or stand on its own. Once approved, the same actions appear in the unified plan.

By the end, you should know where the original lives, understand the saved record, be able to correct it, and have a clear place to resume. To try the flow with fictional materials first, ask the Agent to follow [the trial guide](examples/try-it.md) in a new temporary directory.

## Where to put materials

All paths below are inside your career workspace. For new users, `~/lvji-workspace/` is a suggested location outside the installed Skill. Existing workspaces keep their confirmed paths; no move is automatic.

| Material | Location |
| --- | --- |
| Old résumés, certificates, work/project materials, learning notes | `past/materials/`; create your own topic folders if useful |
| Shared current materials | `present/materials/` |
| Material for a specific ongoing project | `present/items/<item>/materials/` |
| Direction research or job descriptions not yet assigned | `future/materials/` |
| A direction’s or company opportunity’s JD, screenshots, feedback | Its own `materials/` folder |
| Anything you cannot yet classify | `inbox/` |

`START-HERE.md` is the English workspace entrance. `MAP.md` explains the actual files to you; `AGENT-MAP.md` helps the Agent locate only what this task needs. Area guides and maps use the Chinese or English option selected during setup. Physical directory names stay `past/`, `present/`, and `future/`, so changing language does not break references. Your own filenames and topic folders can use your preferred language.

The Agent checks the relevant folder when a related task begins. There is no background watcher. Discovering a file, understanding it, and confirming a factual account are separate steps. A user-supplied `README.md` inside a material folder is a material too; only recognized generated guides are excluded from discovery.

[User map](references/map.en.md) · [Agent map](references/agent-map.en.md) · [Host capabilities and fallbacks](references/hosts.md)

## One workbench, four views

The main workbench is generated at **`views/overview.html`** in your workspace. Its four tabs share one snapshot.

| View | What it shows |
| --- | --- |
| Overview | Active items, today’s actions, recent work/learning, expandable completed or paused items, saved ideas, and stage reviews |
| Unified plan | A daily list, weekly calendar, monthly calendar, and yearly overview, all using the same action records |
| Directions | Horizontally arranged directions; separate sorting by evidence support, information coverage, and your priorities; company JDs, résumés, and interview materials |
| Applications | Actual stages, next steps, event history, feedback, and the precise résumé version used when it is known; filter by direction, company, opportunity, or stage |

Past records are expandable within Overview. Interview materials live within direction or opportunity details. Résumés are separate, versioned HTML files. The six layouts are not six separate workbenches.

Filtering, sorting, and opening details happen inside the page. To change a date, status, or record, tell the Agent what to adjust, review the change, save it, and regenerate. The optional “Ask Agent” control copies a request; you do not need to copy it for everyday use. These pages are dated snapshots, with no direct writeback or drag-to-save scheduling.

**A filter changes the display, not the data included in the file.** A full workbench may contain all records read when it was generated. For sharing, prepare a separate document with an explicit content scope.

The README is available in Simplified Chinese, English, Japanese, Korean, and Spanish. Generated workspace guides and maps currently support Chinese or English only; choose `zh` or `en` during setup. You can use your own language with the Agent, depending on its language capabilities. The workbench’s fixed interface labels remain mainly Chinese, and operational references are mainly in Chinese. README translations do not imply full interface localization.

## Résumés and interview preparation

Ask for a résumé for a role or a particular company. The Agent selects actual experience and confirmed outcomes, drafts clearly separated education/work/project/skill sections, and keeps sources. It does not turn JD requirements or simulated interview answers into your experience.

Six built-in layouts are available. A separate fictional gallery previews all six with avatar A, avatar B, or no portrait, and links to seven external GitHub references. Reference links are not installed templates. The fictional AI portraits belong only in clearly marked demonstrations; a real résumé uses your chosen photograph or no photograph.

Each build creates an independent version. After you review that exact HTML and approve it, an already installed Chrome/Chromium can export the same version to PDF. An export receipt records its integrity; an old or manually supplied PDF without a receipt is shown as unverified. Upgrading a renderer does not invalidate unchanged historical HTML. Changed career sources are reported separately, so you can distinguish an intact old version from a current draft that needs review.

Application events can reference the exact file used. Unknown means “not recorded,” never an assumption that the latest version was sent. Interview stories, company-round preparation, practice, and actual feedback reuse the same underlying evidence. The Agent does not send applications or contact employers.

Detailed workflows: [résumés](references/resume.md) · [interviews](references/interview.md). These operational references are currently written in Chinese; the Agent follows them and responds in your language.

## Explore the fictional demo

The conversations in the local demo are clearly labeled as fictional examples. The demo connects experience, direction, manageable actions, and saved learning, then opens plans, opportunities, and résumés as results. The web demo does not run an online Agent or save visitor data.

Maintainers can generate a portable static site:

```text
python3 scripts/demo_site.py --output _site
```

Use a new output directory. The export includes only fictional read-only pages and local assets, with no machine paths, personal workspace, or runtime history. After creating the repository, select GitHub Actions as its Pages source and manually run the [demo workflow](.github/workflows/pages.yml). Publish only `_site/`, not the repository or a career workspace. A prepared workflow does not mean a live site has been published.

## Keep a path you can return to

```text
lvji-career-kit/               The downloaded Skill package
├── README.md / README.en.md   Human guides
├── README.ja.md / README.ko.md / README.es.md   Japanese, Korean, Spanish guides
├── SKILL.md / AGENTS.md       Agent entry points
├── references/                Task-specific workflows
├── prompts/                   Portrait, gap analysis, interview and review guidance
├── scripts/                   Local standard-library helpers
├── assets/                    Editable page templates and fictional demo portraits
└── examples/                  Small fictional source materials

~/lvji-workspace/             Personal career files, separate from the installed Skill; not distributed
├── START-HERE.md          English start guide; Chinese: 从这里开始.md
├── MAP.md / AGENT-MAP.md  Two maps from the same catalog
├── inbox/                 Unclassified originals
├── past/                  Experience and earlier learning
├── present/               Items, actions, plans, logs, notes, stage reviews
├── future/roles/          Directions → companies → opportunities
├── views/overview.html    Rebuildable workbench
└── .luji/                 Drafts, history, and derived navigation settings
```

A small idea can stay in `present/notes/`. A stage review in `present/stages/` brings together what happened, actual results, changed judgments, and what you may want to continue. It references existing records rather than moving or duplicating them. Saving a review does not automatically close projects or schedule a new stage.

In a new conversation, open your workspace. Its entry files locate the Skill and saved context. If you move the package, ask the Agent to reconnect it using [the navigation setup flow](references/navigation.md). Existing identities and career records stay in place. The Agent resumes from saved summaries, not from imaginary memory of unsaved chats.

You may edit record bodies directly. Schedule dates and status come from action metadata: `scheduled_for`, `due_on`, and `status`. Changing a date only in prose does not reschedule an action. Ask the Agent to make that adjustment, or edit the appropriate field while keeping IDs and JSON values intact.

## Requirements and current limits

The local helpers need Python 3.10+ and no model key or third-party Python packages. Conversation and attachment understanding come from your existing Agent. Local storage does not mean the host model is offline. Preview can use the host’s inline/file panel or an ordinary browser, depending on what it supports.

There is no built-in background reminder, continuous listener, or live page synchronization. Old workspace formats are preserved and are not automatically migrated. Automated checks, isolated Agent exercises, browser checks, and real first-use testing are distinguished in [TESTING.md](TESTING.md); not every host or operating system has been tested.

All examples are fictional. Personal workspaces and runtime histories are excluded from source releases. See [ASSETS.md](ASSETS.md) for provenance and [LICENSE](LICENSE) for the MIT license, which permits commercial use.
