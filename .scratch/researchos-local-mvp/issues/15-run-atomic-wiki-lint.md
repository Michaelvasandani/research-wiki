# 15 — Run atomic wiki lint

**What to build:** A researcher-triggered Codex health check that identifies and safely repairs maintainable knowledge-base problems without scheduling itself or bypassing the wiki's publication safeguards.

**Blocked by:** 07 — Compound knowledge across two papers; 14 — Track Obsidian edits and protect managed content.

**Status:** ready-for-agent

- [ ] The researcher can explicitly start Wiki lint and see queued, processing, completed, or failed status.
- [ ] Lint inspects contradictions, stale claims, orphan pages, missing cross-references, possible duplicates, and evidence gaps.
- [ ] Lint follows the repository-versioned LLM Wiki skill and reads only ingested evidence with network access disabled.
- [ ] Proposed repairs preserve competing claims, possible duplicates, and researcher annotations rather than resolving scientific ambiguity automatically.
- [ ] Conflicted pages are not overwritten and cause an understandable skipped or failed outcome.
- [ ] A successful lint updates affected pages, the index, and the append-only activity log through one staged publication.
- [ ] A successful lint produces exactly one Git commit; a Codex or validation failure exposes no partial changes.
- [ ] Lint is never run on a schedule in the Local MVP.
- [ ] Public-boundary tests cover problem detection, a successful repair, annotation preservation, conflict handling, disabled networking, and atomic failure.
