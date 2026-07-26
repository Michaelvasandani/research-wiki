# 12 — Withdraw an ingested source safely

**What to build:** A withdrawal workflow that stops an unreliable or mistakenly added source from informing future research while retaining the evidence and making its historical influence visible.

**Blocked by:** 09 — Research across ingested sources.

**Status:** ready-for-agent

- [ ] Library lets a researcher mark a completed ingested source as withdrawn without deleting its PDF, derivative, manifest, or paper page.
- [ ] The source record retains its stable identity, revisions, metadata, and withdrawal state across restarts.
- [ ] A staged writer marks the paper page and affected wiki knowledge as relying on withdrawn evidence.
- [ ] Historical evidence citations continue to resolve to the exact withdrawn source and physical PDF page.
- [ ] Future research synthesis excludes withdrawn evidence by default and indicates when relevant withdrawn material exists.
- [ ] Withdrawal updates the index and appends a human-readable activity entry.
- [ ] The wiki changes publish as one validated Git commit, or no visible withdrawal changes are published.
- [ ] Pre-ingest uploads may be removed without implying that completed ingested sources can be hard-deleted.
- [ ] Public-boundary tests verify preservation, visible marking, research exclusion, historical citation stability, restart persistence, and atomic failure.
