# 03 — Create page-addressable Markdown derivatives

**What to build:** A serial ingest worker that converts queued text PDFs into immutable, page-addressable Markdown derivatives with reproducibility records and clear recovery behavior when conversion cannot safely proceed.

**Blocked by:** 02 — Upload and identify source PDFs.

**Status:** ready-for-agent

- [ ] One FIFO worker moves an ingest through queued, processing, completed, failed, or unsupported states and never processes two ingests concurrently.
- [ ] Conversion uses pinned MarkItDown and parser dependencies with plugins and network access disabled.
- [ ] The derivative contains an explicit marker for every physical PDF page.
- [ ] A derivative manifest records source and output hashes, converter and dependency versions, configuration, and conversion time.
- [ ] Derivatives are immutable and stored outside the Git-versioned wiki; a converter change creates a new derivative version.
- [ ] Empty, garbled, substantially missing, encrypted, malformed, oversized, or extraction-poor PDFs fail safely before Codex publication.
- [ ] Image-only or scanned PDFs end in a clear OCR-required unsupported state.
- [ ] One transient conversion failure is retried automatically; a second failure is durable and offers manual retry against the same immutable source.
- [ ] Conversion runs with explicit resource limits and treats PDF content as untrusted data.
- [ ] Tests verify page coverage, manifest reproducibility, disabled networking, safe rejection, FIFO execution, restart persistence, retry, and manual recovery.
