# LüJi · A career that keeps growing

[简体中文](README.md) · English · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md)

**Make your Agent a personal career adviser, connecting past experience, today’s actions and future directions.**


```text
Install lvji-career-kit from https://github.com/siliviasilivia85-lang/lvji-career-kit and help me make sense of one past experience.
```

[Installation and host options](references/install.md) · Install once, then speak naturally.

## Why LüJi

AI is making it easier to learn and put ideas into practice. There are new ways to find knowledge, use tools, and make things. We can try more than before, while skills that once belonged to separate roles increasingly overlap and combine. The boundaries of a career are changing with them.

More choices do not necessarily bring a clearer direction. New tools and opportunities keep appearing, but our time is still limited. Which knowledge is worth learning, which projects are worth pursuing, and where past experience might prove useful are questions we gradually answer by trying.

Looking for a job is only one point along that path. Working toward a promotion, taking on greater responsibility, or moving into a new field also calls for preparation. If we wait until a change is needed, there is little time left to learn, practise, and make mistakes. The faster technology changes, the more career development needs a place in our everyday work and lives.

Granted, we have already grown used to bringing these questions to AI: a thought about changing direction, a setback at work, or a concern about the future. It can talk things through with us and help us analyse them. But when those thoughts remain scattered across conversations, the Agent often has only the part we happened to share at the time. Without concrete experience and outcomes to draw on, advice can stay general. Moving to another conversation or tool can mean explaining again where we left off and which judgments still need to be tested.

A job search brings more things to keep track of at once: different directions lead to different roles and companies, each application may use a different résumé, and there are interviews to prepare for, progress to follow, and feedback to record. A single conversation can help with one of these tasks. But without a shared place to keep materials, versions, and status, it is hard to see the whole picture or bring new feedback back into everyday learning and preparation.

LüJi brings a career development method, a folder structure for your materials, and local file tools together in a Skill for the Agent you already use. Start with your experience and abilities, discuss possible directions together, work out the knowledge and practice a goal calls for, and fit that preparation into the time you can spare each day. Project outcomes, learning records, and real feedback are checked with you before they are saved, so later conversations can find, refer to, and revise them.

As those records accumulate, the Agent can draw on the same body of material to understand your experience, preferences, and practical constraints in more detail. The discussion results, decisions, and progress you choose to save help it recover where you left off and what to do next. You can inspect, add to, and correct its understanding of you. A personal career adviser takes shape through these continuing conversations, practical efforts, and records.

![LüJi’s career development framework, connecting past experience, present action, and future directions](assets/career-overview.svg)

## How LüJi works

### Past: organize your experience and preserve its evidence

Give the Agent earlier résumés, work and project materials, learning notes, education records, or awards—or place them directly in your workspace’s material folders. The Agent organizes them by topic, keeps the originals and their sources, and draws out specific experiences. You can add missing details and correct its understanding at any time.

Past plans, work actually completed, and confirmed outcomes are recorded separately. When you want to understand your strengths or abilities, the Agent draws on the actual materials to offer an interpretation for you to review and revise. That interpretation can change as you gain new experience.

### Present: bring goals into everyday work and learning

Start with your current work, a project you want to pursue, or a direction you have not yet thought through. The Agent considers your experience, current progress, the goal’s requirements, and the time you can give it. Together, you identify useful knowledge and practical work, then break them into concrete projects, milestones, and daily, weekly, and monthly actions.

Add learning progress, work outcomes, and feedback as they happen. Reviewing a plan builds on the existing arrangements; a small adjustment changes only the relevant items. If time becomes scarce, a goal changes, or progress stalls, decide together whether to reduce the scope, postpone, pause, or continue. You can begin without a complete record of your past.

### Future: explore directions and prepare for career changes

You may want to work toward a promotion, take on new responsibilities, move into another role, or try a project of your own. Save the direction and the thinking behind it. You do not need an existing job description to discuss a goal. When a specific role becomes relevant, gather its requirements, compare directions and companies, and connect them with your past experience and current progress to identify supporting evidence, gaps, and open questions.

When you do begin a job search, you can keep drawing on the same accumulated work:

- **Résumés:** Select relevant experience and confirmed outcomes for a role or company, then generate an independently saved HTML résumé version. Choose from six layouts, with your selected photograph or no photograph. After you review and approve that exact HTML version, use an already installed Chrome/Chromium to export the same version as a PDF.
- **Interview preparation:** Organize project stories, role-specific questions, and talking points. Prepare materials for each company and interview round, practise question by question, and save reflections after actual interviews.
- **Application tracking:** For each role at a company, record actual application stages, the exact résumé version used, feedback, and next steps. Review all opportunities or focus on a single role or opportunity. Real feedback can return to the present as suggestions for further practice and action.

### Keep going: pick up where the last conversation left off

Experience, actions, plans, and outcomes live in readable local files, with separate maps for you and your Agent. You can add new materials directly to the folders. When handling a related request, the Agent checks for changes and reads what it needs. Important additions become concrete drafts for you to review before they are saved as formal records.

In a new conversation, the Agent uses saved item summaries to recover the goal, where you stopped, and the next step. Its understanding comes from the experience, outcomes, and discussion results you choose to save; unsaved chats are not treated as long-term memory. You can check sources, edit records, and correct how it understands you.

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
