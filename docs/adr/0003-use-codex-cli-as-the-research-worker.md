# Use Codex CLI as the research worker

ResearchOS uses Codex CLI as its AI research worker in both the Local MVP and the future EC2 deployment. Codex performs ingestion analysis, synthesis, external research, and wiki maintenance according to the adapted LLM Wiki pattern, while the application retains deterministic responsibilities such as source storage, job state, and access control; using the same worker locally and in production avoids maintaining a separate direct-model integration.
