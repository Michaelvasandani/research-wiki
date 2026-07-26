# 06 — Visualize the explicit knowledge graph

**What to build:** A polished, read-only knowledge graph that helps the researcher see and navigate the relationships Codex deliberately recorded in the wiki.

**Blocked by:** 05 — Browse and search the wiki.

**Status:** ready-for-agent

- [ ] Graph nodes represent published wiki pages and carry stable page identity, title, type, and navigation target.
- [ ] Graph edges are created only from explicit wikilinks; keyword overlap and semantic similarity do not create edges.
- [ ] Paper, topic, and filed-analysis nodes have visually distinct colors.
- [ ] Node size reflects connection count.
- [ ] The force layout supports pan, zoom, hover labels, and click-to-open navigation.
- [ ] Missing or invalid wikilink targets do not crash the graph and are exposed by validation rather than rendered as inferred pages.
- [ ] The graph reads only the latest fully published wiki snapshot.
- [ ] Tests verify graph nodes, explicit-link edges, types, connection counts, labels, and targets without asserting unstable layout coordinates.
