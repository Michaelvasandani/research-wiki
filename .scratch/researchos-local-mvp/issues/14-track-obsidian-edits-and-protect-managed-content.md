# 14 — Track Obsidian edits and protect managed content

**What to build:** Automatic tracking of Obsidian edits that commits legitimate researcher annotations and detects edits to AI-managed content before an automatic writer can overwrite them.

**Blocked by:** 13 — Preserve researcher annotations during updates.

**Status:** ready-for-agent

- [ ] A filesystem watcher detects completed Obsidian saves to the vault and debounces temporary or repeated write events.
- [ ] An annotation-only edit produces one researcher-edit Git commit without requiring manual Git commands.
- [ ] Watcher activity does not commit source PDFs, derivatives, manifests, jobs, chat transcripts, editor temporaries, or unrelated application state.
- [ ] A human edit outside the protected annotation section is preserved in Git and records a page conflict.
- [ ] A page conflict is visible to the researcher in the application.
- [ ] Ingest, filed-analysis, and lint writers pause changes to a conflicted page instead of overwriting it.
- [ ] Unconflicted pages may continue to update when doing so does not make the complete publication invalid.
- [ ] Restarting the application retains conflict state and does not duplicate researcher-edit commits.
- [ ] Tests cover annotation-only saves, rapid repeated saves, managed-content edits, paused writers, ignored files, and restart behavior.
