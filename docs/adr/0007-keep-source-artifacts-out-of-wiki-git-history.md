# Keep source artifacts out of wiki Git history

ResearchOS Git-tracks the generated wiki and its human-readable activity log, but stores original PDFs and Markdown derivatives in dedicated source storage addressed by content hashes. This keeps immutable binary and extraction artifacts from permanently inflating the wiki repository while preserving verifiable evidence that the web application and Obsidian-facing environment can expose when needed.
