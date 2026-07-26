# 08 — Correct metadata and preserve source revisions

**What to build:** Library workflows that let the researcher correct authoritative source metadata and associate a corrected or revised PDF without rewriting the identity or history of prior evidence.

**Blocked by:** 04 — Publish the first paper page atomically.

**Status:** ready-for-agent

- [ ] A researcher can correct title, authors, year, and DOI for an ingested source from Library.
- [ ] Corrected metadata is marked authoritative and is not overwritten by later local extraction.
- [ ] A metadata correction updates the corresponding paper page, index, and activity log through the staged validation and atomic publication path.
- [ ] A researcher can identify a newly uploaded PDF as a revision of an existing source.
- [ ] Different PDF bytes always receive a distinct source identity even when their bibliographic metadata matches.
- [ ] Both revisions remain stored and navigable, with an explicit relationship between them.
- [ ] Historical citations continue to point to the exact source revision and physical page that originally supported the claim.
- [ ] A correction or revision failure publishes no partial wiki changes.
- [ ] Public-boundary tests cover extracted metadata, filename fallback, authoritative corrections, revision linking, and historical citation stability.
