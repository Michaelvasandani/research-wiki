# 02 — Upload and identify source PDFs

**What to build:** A Library workflow that accepts a PDF, preserves its exact bytes, assigns a content-based source identity, captures useful bibliographic metadata, and immediately exposes the queued ingest to the researcher.

**Blocked by:** 01 — Run the Local MVP shell.

**Status:** ready-for-agent

- [ ] A researcher can upload a PDF from Library and receives a response without waiting for conversion or Codex.
- [ ] The exact uploaded bytes are retained in source storage outside the Git-versioned wiki.
- [ ] Source identity is the SHA-256 digest of the exact PDF content and is recorded in a file-based source manifest.
- [ ] Uploading identical bytes under another filename reuses the existing source identity without creating fragmented evidence.
- [ ] Uploading different bytes under the same filename creates a distinct source identity.
- [ ] Title, authors, year, and DOI are extracted locally when available; uncertain title extraction falls back to the filename.
- [ ] The source manifest distinguishes extracted metadata from later researcher-authoritative metadata.
- [ ] A queued ingest record is created durably and Library shows its status after a restart.
- [ ] Non-PDF input and clearly invalid uploads fail safely with a useful researcher-facing error.
- [ ] Public-boundary tests cover upload, persistence, deduplication, filename collision, metadata fallback, and queued status.
