# 09 — Research across ingested sources

**What to build:** One persisted, streaming research thread in which Codex prioritizes the lab's ingested evidence, synthesizes across papers, and remains unable to mutate persistent wiki knowledge.

**Blocked by:** 07 — Compound knowledge across two papers.

**Status:** ready-for-agent

- [ ] Research exposes one conversational thread that persists across application and container restarts.
- [ ] A question is answered from the latest fully published wiki snapshot and ingested derivatives, using the index, explicit relationships, backlinks, and ordinary file search.
- [ ] An answer supported by two papers performs cross-paper synthesis and cites the relevant ingested sources.
- [ ] The interface streams the answer and concise progress states without exposing raw shell output, tool calls, or hidden reasoning.
- [ ] Lab evidence is visibly grouped as Lab sources.
- [ ] If relevant evidence is still queued or processing, chat states that the pending source is not yet available.
- [ ] Research remains usable while an ingest job runs and does not observe partially staged changes.
- [ ] The Codex research process receives read-only access to the live wiki and cannot edit or commit wiki pages.
- [ ] An ordinary chat response never creates an automatic wiki update.
- [ ] Tests attempt prompt-driven writes and verify that the vault contents and Git head remain unchanged.
