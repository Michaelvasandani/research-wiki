# Publish wiki updates atomically

ResearchOS stages each ingest's complete wiki update away from the live wiki, validates it, and publishes the update as one Git commit only if the entire set succeeds. The same one-update-per-commit rule applies to wiki lint and filed analysis. A failed operation retains its failure state but exposes none of its partial wiki edits, preventing inconsistent pages, citations, links, index entries, or activity-log records; Git provides rollback and detailed history while `log.md` remains the researcher-facing narrative.
