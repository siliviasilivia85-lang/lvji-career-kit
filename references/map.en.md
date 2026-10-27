# Your map

Start with one familiar experience and its materials. Ask the Agent to organize it, review the draft, and save only what you agree with. After the first setup, use ordinary conversation; no per-conversation command needs copying.

## Where things belong

| What you have | Where you can put it | What the Agent can organize |
| --- | --- | --- |
| Old résumé, certificate, project, learning notes | `past/materials/` | Separate experience, education, work, project, and learning records |
| Material for current work | `present/materials/` or `present/items/<item>/materials/` | The item summary, actions, and actual progress |
| Research or JD without a chosen direction | `future/materials/` | A candidate direction or opportunity, if you decide to keep it |
| JD, screenshot, or feedback for an opportunity | That direction’s or opportunity’s `materials/` | Its JD, application event, or feedback |
| Something not yet classified | `inbox/` | Help choosing a home when a related task begins |

Ordinary files need no internal fields. Keep your originals and filenames. Discovery is not confirmation that the Agent has read or understood them. Generated folder guides are separate; your own material named `README.md` is discoverable.

Ideas you decide to save without a project or goal go to `present/notes/`. Ongoing work lives in `present/items/`. Reflections at the end of a stage live in `present/stages/`. These formal Markdown records are created through the Agent’s reviewed-draft workflow; you do not need to construct their metadata yourself.

## Useful everyday requests

| Your question | What should happen |
| --- | --- |
| I added my résumé; help me understand my experience | Check the relevant material entry, read the selected file, compare relevant records, and offer analysis or a draft |
| I might change direction, but I am unsure | Discuss possibilities without forcing a goal or timetable |
| Save this idea without starting a project | Draft a standalone note, with no required future link |
| Continue the project from last time | Recover its saved goal, stopping point, open questions, and next step |
| What am I doing today or this week? | Show existing actions without silently rescheduling them |
| Move this action to Friday | Show that action’s date change and direct effects, then save the approved version |
| Help me prepare for this interview | Locate this opportunity, its round, JD, and relevant experience |
| I sent this version yesterday | Record the actual event and exact résumé artifact, if known |
| Let us review this stage | Summarize real outcomes and changed judgments, with optional next steps |

## Find things again

Open your workspace’s `START-HERE.md` and `MAP.md`. The map and area lists show actual paths, material states, and check times. Pending, linked, changed, and missing are distinct states. Unchecked areas retain their previous check time. The Agent checks relevant areas when needed; there is no background listener.

Completed or paused work is still available in the Overview’s review area and in the Markdown files. A new conversation can resume from saved summaries; unsaved conversation is not long-term memory. The workspace includes a Skill locator. If it becomes invalid after moving files, reconnect it once instead of recreating the workspace.

You may edit record bodies. Action dates and status live in metadata (`scheduled_for`, `due_on`, `status`); editing prose alone does not change the plan. The easiest route is to ask the Agent for a precise adjustment. Keep IDs and existing history intact when editing manually.

Workbench pages are snapshots. Filters do not remove other data from the file; prepare a separate scoped document before sharing. Read [README.en.md](../README.en.md) for the four views and [host capabilities](hosts.md) for display options.
