# 05 — Browse and search the wiki

**What to build:** A read-only web Wiki where the researcher can inspect published knowledge, follow maintained relationships, search Markdown content, and understand how the wiki changed.

**Blocked by:** 04 — Publish the first paper page atomically.

**Status:** ready-for-agent

- [ ] Wiki renders paper and topic pages from the latest fully published Git snapshot.
- [ ] Frontmatter is presented as useful page metadata rather than raw YAML.
- [ ] Markdown footnotes render as readable evidence citations with paper title, source identity, and physical PDF page.
- [ ] Explicit Obsidian wikilinks resolve to clickable web navigation where the target exists.
- [ ] Each page lists backlinks derived from explicit wikilinks.
- [ ] Ordinary text search returns matching paper and topic pages without a SQL database, vector search, or embedding service.
- [ ] The index and append-only activity log are readable from the web interface.
- [ ] The web interface offers no page-content editing action.
- [ ] An unpublished staged update never appears in rendered pages, search results, or backlinks.
- [ ] Public-boundary tests verify rendering, search, citations, wikilinks, backlinks, activity history, and read-only behavior.
