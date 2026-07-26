# 16 — Verify the complete real-Codex MVP

**What to build:** A final integrated proof that the Local MVP works as one coherent research system with deterministic automated coverage and a repeatable manual smoke test against real Codex CLI and Obsidian.

**Blocked by:** 05 — Browse and search the wiki; 06 — Visualize the explicit knowledge graph; 08 — Correct metadata and preserve source revisions; 11 — File a supported research analysis; 12 — Withdraw an ingested source safely; 14 — Track Obsidian edits and protect managed content; 15 — Run atomic wiki lint.

**Status:** ready-for-agent

- [ ] The automated acceptance flow starts from clean persistent storage and uploads two related, representative text PDFs.
- [ ] Both PDFs complete conversion and ingest with immutable sources, page-addressable derivatives, cited paper pages, accumulated topic knowledge, explicit graph relationships, activity entries, and one Git commit per ingest.
- [ ] The acceptance corpus exercises ordinary prose and at least some two-column, table, equation, or figure content so extraction weaknesses are visible.
- [ ] Research chat synthesizes across the two papers, can distinguish external research, remains read-only, and can explicitly file a supported analysis.
- [ ] The integrated flow covers metadata correction, source revision, withdrawal, annotation preservation, page conflict, lint, retry, atomic failure, and restart persistence.
- [ ] A UI smoke test covers Library, Research, Wiki, and Graph and confirms the web wiki remains read-only.
- [ ] Security coverage verifies localhost binding, untrusted paper content, writer network isolation, read-only chat permissions, and absence of source artifacts from wiki Git history.
- [ ] The project documents a repeatable manual smoke test using the real Codex CLI, its normal authentication, the versioned LLM Wiki skill, actual permission profiles, chat web search, and Obsidian.
- [ ] The real-Codex smoke test evaluates structural outputs and evidence traceability rather than exact prose.
- [ ] Conversion time, derivative size, and end-to-end ingest duration are captured for the representative papers.
- [ ] A clean-checkout operator can follow the documentation to demonstrate the complete Local MVP without installing a database or vector-search service.
