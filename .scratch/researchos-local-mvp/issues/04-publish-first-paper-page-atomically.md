# 04 — Publish the first paper page atomically

**What to build:** The first complete ingest, in which Codex follows the versioned LLM Wiki conventions to turn a Markdown derivative into a cited paper page and publishes the entire wiki update as one validated Git commit or not at all.

**Blocked by:** 03 — Create page-addressable Markdown derivatives.

**Status:** ready-for-agent

- [ ] The repository versions one LLM Wiki skill with explicit ingest, query, and lint workflows, and vault-level guidance requires its use.
- [ ] Ingest reads the current index and the new derivative while treating paper text as untrusted evidence rather than executable instructions.
- [ ] The generated paper page has stable identity and minimal frontmatter plus metadata, summary, findings, methods, datasets, limitations, related pages, contradictions/open questions, citations, and a final researcher-annotation section.
- [ ] Every factual claim has a Markdown footnote naming the paper, stable source identity, and valid physical PDF page.
- [ ] The ingest updates the content index and appends an activity entry naming the source, affected pages, contradictions, and possible duplicates.
- [ ] Codex writes only to a staged wiki from a fixed Git snapshot and has no network access during ingest.
- [ ] Publication validates metadata, page-addressable citations, explicit wikilinks or possible-duplicate flags, index/log updates, and protected annotation boundaries.
- [ ] A successful ingest appears in Library and publishes exactly one Git commit containing the complete wiki update.
- [ ] A Codex failure, malformed result, or validation failure leaves the live wiki, index, activity log, and Git head unchanged.
- [ ] The original PDF, derivative, manifests, job records, and process output remain outside wiki Git history.
- [ ] A prompt-injection fixture inside a PDF cannot alter the prescribed ingest workflow or permissions.
- [ ] Public-boundary tests use the fake Codex executable and assert durable artifacts rather than private calls or exact prose.
