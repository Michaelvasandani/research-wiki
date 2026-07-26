# 07 — Compound knowledge across two papers

**What to build:** A second successful ingest that makes the wiki materially smarter by accumulating compatible evidence on substantive topic pages while preserving uncertainty and disagreement.

**Blocked by:** 04 — Publish the first paper page atomically.

**Status:** ready-for-agent

- [ ] Ingesting a related second PDF creates its paper page and updates relevant existing knowledge in one atomic commit.
- [ ] Codex creates or updates topic pages only for substantive concepts or methods with reusable definitions, assumptions, variants, evidence, or relationships.
- [ ] Incidental terminology remains inline rather than becoming low-value topic pages.
- [ ] A topic page can accumulate separately cited evidence from both ingested sources.
- [ ] Incompatible claims are retained together as a contradiction with each claim's source context and evidence citations.
- [ ] Ambiguous concept or method identity remains on separate pages connected by a possible-duplicate flag rather than an unsafe merge.
- [ ] Paper and topic pages use explicit wikilinks that produce correct backlinks and graph edges.
- [ ] The index and activity log describe all pages, contradictions, and possible duplicates affected by the second ingest.
- [ ] The second ingest publishes exactly one commit and preserves the first source's historical citations.
- [ ] A two-paper acceptance test demonstrates one meaningful cross-paper result without relying on exact generated prose.
