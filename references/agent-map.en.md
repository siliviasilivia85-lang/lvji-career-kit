# Agent reading map

Use this as the English routing map. Shared behavior is defined by [SKILL.md](../SKILL.md) and the [turn protocol](turn-protocol.md). Operational references may be in Chinese; respond and draft records in the user’s language.

Fix the confirmed absolute workspace path and identity first. A workspace’s `AGENT-MAP.md` locates the actual Skill and its regional catalogs. If the binding is invalid after a move, follow [navigation setup](navigation.md); do not scan private directories or initialize over existing data.

## Read in layers

1. Workspace Agent map: choose the relevant area.
2. Refresh only the relevant directory scope, then use its catalog to select objects. A cached catalog is not a current file revision or proof of understanding.
3. Read the selected summary and necessary sources. For saving, use `md_workspace.py context` to get the actual recursive source closure and draft base.

| Request | Start with | Then read only what is needed | Workflow |
| --- | --- | --- | --- |
| New résumé or learning material | Selected material entry, or `inbox/` | The selected original and likely duplicate records | [Past](past.md) |
| Resume current work | The selected item or standalone note | Saved stopping point, related actions, latest logs, relevant materials | [Present](present.md) |
| Today’s or this week’s plan | Plans for the requested dates | Referenced actions and necessary dependencies | [Present](present.md) |
| Compare directions | Selected goals and JDs | Relevant experience, confirmed outcomes, existing assessment | [Future](future.md) |
| Draft a résumé | Exact role/opportunity | Necessary identity, education, work/projects, confirmed outcomes | [Résumé](resume.md) |
| Interview preparation | Exact opportunity and round | JD, saved preparation, stories, underlying evidence | [Interview](interview.md) |
| Record an application event | Exact application and user-provided event | Exact artifact binding if known; never infer latest | [Future](future.md) |
| Review a stage | Chosen items and date scope | Actual logs, results, feedback, earlier summaries | [Stage review](stages.md) |
| Show a view | The saved records required for that view | Explicitly authorized snapshot scope | [Views](views.md) |

No past data is required to start planning. A possible wish is not an adopted direction. Negative statements, historical wishes, and someone else’s plans must not create the user’s goals. Offer only the missing information that matters now; allow skipping it.

An idea may remain a conversation, or become a reviewed `note` in `present/notes/`. A stage review is `stage-summary` in `present/stages/`. Neither is a résumé fact source. Saving them does not create tasks or change existing statuses.

Directly added originals retain names and locations and need no frontmatter. Detecting or hashing a file does not mean understanding it. Save factual records only after presenting a concrete draft and obtaining confirmation for that version; do not repeat confirmation already received. Apply, read back, link source revisions where appropriate, and refresh the relevant maps. Report saving, map generation, and page display as separate results.

Resume new conversations from saved summaries and actual files. Do not claim memory of unsaved chats. Keep the current focus, confirmed decisions, open questions, next step, and references distinct. See [human map](map.en.md) and [file contract](workspace.md) when commands or fields are needed.
