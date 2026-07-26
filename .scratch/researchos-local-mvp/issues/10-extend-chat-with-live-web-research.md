# 10 — Extend chat with live web research

**What to build:** Research chat that retains Codex's broader research capability by searching the web when the ingested collection is insufficient, while keeping external findings visibly and operationally separate from wiki evidence.

**Blocked by:** 09 — Research across ingested sources.

**Status:** ready-for-agent

- [ ] Codex may use live web search from Research chat when the ingested evidence cannot adequately answer a question.
- [ ] Ingest, filed-analysis writers, and wiki lint continue to run without network access.
- [ ] A response that uses the web names the relevant gap in the ingested collection.
- [ ] The response visibly separates Lab sources from External sources and cites both groups appropriately.
- [ ] External research sources do not become ingested sources, source manifests, Markdown derivatives, or wiki pages automatically.
- [ ] The live wiki and Git head remain unchanged after an externally supported answer.
- [ ] The deterministic fake Codex can simulate web-search progress and external citations without real network access.
- [ ] Public-boundary tests cover lab-only answers, externally extended answers, gap naming, evidence grouping, and absence of persistent writes.
