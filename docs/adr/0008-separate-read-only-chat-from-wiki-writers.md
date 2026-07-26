# Separate read-only research chat from wiki writers

The Codex process serving ordinary research chat receives read-only access to the live wiki. Ingest, wiki lint, and explicitly filing an analysis run as separate constrained writer jobs against a staged copy, then validate and publish one atomic Git commit; this prevents conversational turns from mutating persistent knowledge outside the controlled publication path.
