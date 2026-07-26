# 13 — Preserve researcher annotations during updates

**What to build:** A safe collaboration rule in which researcher annotations made through Obsidian survive every automatic writer operation byte-for-byte, including edits made while an update is being prepared.

**Blocked by:** 04 — Publish the first paper page atomically.

**Status:** ready-for-agent

- [ ] Every generated wiki page ends with an unambiguous designated researcher-annotation section.
- [ ] A researcher can edit that section in the Obsidian-compatible vault without using the web application.
- [ ] A later ingest or other staged writer preserves the section byte-for-byte.
- [ ] The publication validator rejects any staged update that modifies, removes, reorders, or ambiguously parses protected annotation content.
- [ ] If an annotation commit lands after a writer takes its starting snapshot, the writer rebases onto the new head and revalidates before publication.
- [ ] A successfully rebased writer publishes one final commit without losing the concurrent annotation.
- [ ] An unresolvable concurrent change leaves the live wiki and Git head at the researcher's committed version and reports a recoverable failure.
- [ ] Contract tests concentrate on annotation boundaries and merge behavior; public-boundary tests verify the observable Obsidian-to-ingest flow.
