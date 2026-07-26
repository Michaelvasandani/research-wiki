# ResearchOS Local MVP

Status: ready-for-agent

## Problem Statement

Researchers accumulate papers faster than they can maintain a coherent shared understanding of them. Conventional document chat repeatedly retrieves raw passages and reconstructs answers from scratch, so useful comparisons, contradictions, terminology, and connections disappear into chat history instead of strengthening a durable body of knowledge.

The researcher needs a local proof that ResearchOS can turn deliberately uploaded papers into a persistent, trustworthy, Obsidian-compatible research wiki. The proof must preserve original evidence, make claims traceable to physical PDF pages, use Codex's research capabilities, accumulate cross-paper knowledge, remain safe when automated updates fail, and stay simple enough to run locally without database or retrieval infrastructure.

## Solution

Build a single-user Local MVP that runs through Docker Compose and uses Codex CLI as its AI research worker. A researcher uploads text-based PDFs through a web application. ResearchOS preserves each original PDF, creates an immutable page-addressable Markdown derivative for efficient Codex reading, and immediately queues a serial ingest.

The repository-versioned LLM Wiki skill directs Codex to create and maintain an Obsidian-compatible Markdown vault. Ingest produces paper pages, substantive topic pages, explicit wikilinks, an index, and a human-readable activity log. Claims use Markdown footnotes that identify their supporting paper and physical PDF page. Topic pages accumulate evidence across papers; Codex performs novel cross-paper synthesis in research chat, and a researcher may explicitly file a valuable analysis into the wiki.

All persistent wiki changes use a constrained staged writer. ResearchOS validates the complete update and publishes it as one Git commit or exposes none of it. Ordinary research chat is read-only, prioritizes ingested sources, and may use live web search while labeling external sources separately. The web application provides a paper library, one persisted research thread, a read-only wiki browser, backlinks, and a lightweight force-directed knowledge graph. Researchers use Obsidian to add protected annotations to the same vault.

The MVP is successful when two related PDFs complete the full compounding-wiki loop and the resulting knowledge can be browsed, queried, extended, and safely updated.

## User Stories

1. As a researcher, I want to start ResearchOS locally with one Docker Compose command, so that I can evaluate the complete workflow without provisioning cloud infrastructure.
2. As a researcher, I want the local application bound only to my machine, so that the unauthenticated MVP is not exposed to my network.
3. As a researcher, I want to upload a text-based PDF, so that it can become evidence in the lab's research wiki.
4. As a researcher, I want an upload to return quickly while ingest continues asynchronously, so that I am not blocked by a long Codex operation.
5. As a researcher, I want to see whether an ingest is queued, processing, completed, failed, or unsupported, so that I understand the source's current state.
6. As a researcher, I want ingests processed one at a time, so that concurrent agents cannot create conflicting wiki updates.
7. As a researcher, I want one automatic retry for a transient ingest failure, so that temporary failures do not immediately require intervention.
8. As a researcher, I want a failed ingest to show a useful error and offer manual retry, so that I can recover without uploading the paper again.
9. As a researcher, I want ResearchOS to retain the exact uploaded PDF, so that the original evidence remains authoritative.
10. As a researcher, I want identical PDF bytes recognized as the same source even when filenames differ, so that duplicate uploads do not fragment the wiki.
11. As a researcher, I want two different files with the same filename treated as distinct sources, so that filename collisions cannot corrupt identity.
12. As a researcher, I want corrected or revised PDFs preserved as linked source revisions, so that existing citations continue to identify the exact evidence used.
13. As a researcher, I want title, authors, year, and DOI extracted locally when possible, so that paper pages begin with useful bibliographic metadata.
14. As a researcher, I want extraction to fall back to the PDF filename when bibliographic metadata is uncertain, so that ingest can still proceed.
15. As a researcher, I want to correct source metadata from the library, so that ResearchOS uses authoritative human corrections in future updates.
16. As a researcher, I want source metadata corrections reflected in the paper page, so that the wiki remains consistent with the library.
17. As a researcher, I want a page-addressable Markdown derivative generated from each PDF, so that Codex can read and search papers efficiently.
18. As a researcher, I want every derivative page mapped to a physical PDF page, so that generated claims can carry pinpoint citations.
19. As a researcher, I want converter versions, configuration, and input/output hashes recorded, so that an ingest can be reproduced and audited.
20. As a researcher, I want extraction-poor or image-only PDFs rejected clearly, so that ResearchOS does not publish knowledge from missing text.
21. As a researcher, I want malformed, encrypted, oversized, or otherwise unsafe PDFs to fail safely, so that conversion cannot destabilize the application.
22. As a researcher, I want uploaded paper content treated as untrusted data rather than agent instructions, so that prompt-like text inside a paper cannot control Codex.
23. As a researcher, I want Codex to create a structured paper page, so that the source's metadata, summary, findings, methods, datasets, limitations, relationships, contradictions, and open questions are easy to inspect.
24. As a researcher, I want every factual wiki claim supported by a Markdown footnote naming the paper and physical PDF page, so that I can verify where the claim came from.
25. As a researcher, I want Codex to create a topic page only for a substantive concept or method, so that the graph is not filled with incidental terminology.
26. As a researcher, I want topic pages to accumulate evidence from multiple papers, so that the wiki develops maintained cross-paper knowledge.
27. As a researcher, I want incompatible claims preserved together as a contradiction, so that ResearchOS does not make a scientific judgment on my behalf.
28. As a researcher, I want contradiction entries to retain the context and citations of each claim, so that I can decide how to interpret the disagreement.
29. As a researcher, I want ambiguous concepts or methods kept as separate possible duplicates, so that a mistaken merge cannot silently corrupt accumulated knowledge.
30. As a researcher, I want Codex to create explicit Obsidian wikilinks for material relationships, so that the connection is inspectable and intentional.
31. As a researcher, I want graph edges derived only from explicit wikilinks, so that the visualization does not imply relationships based on noisy keyword overlap.
32. As a researcher, I want the wiki index updated on every successful write operation, so that both Codex and I can navigate current knowledge.
33. As a researcher, I want an append-only activity-log entry for every successful ingest or maintenance update, so that I can follow the wiki's evolution.
34. As a researcher, I want each activity entry to identify the source, affected pages, contradictions, and possible duplicates, so that automatic changes are understandable.
35. As a researcher, I want a failed ingest to publish none of its partial wiki edits, so that the visible vault is always internally consistent.
36. As a researcher, I want every successful ingest published as one Git commit, so that I can inspect or roll back the complete update.
37. As a researcher, I want wiki lint and filed analyses to use the same atomic publication path, so that all persistent changes receive equal safeguards.
38. As a researcher, I want source PDFs and Markdown derivatives kept out of wiki Git history, so that immutable artifacts do not permanently inflate the repository.
39. As a researcher, I want to mark an ingested source withdrawn, so that a retracted, unreliable, or mistakenly added paper is excluded from future synthesis.
40. As a researcher, I want withdrawn evidence and historical citations preserved and visibly marked, so that the wiki does not rewrite its past.
41. As a researcher, I want to open the generated vault in Obsidian, so that I can browse pages, backlinks, and the graph using familiar tooling.
42. As a researcher, I want every wiki page to contain a designated researcher-annotation section, so that I can add expert context that Codex cannot overwrite.
43. As a researcher, I want Obsidian annotation saves committed automatically after a short debounce, so that I do not need to operate Git manually.
44. As a researcher, I want concurrent annotation edits preserved when an ingest publishes, so that automation cannot erase work I made while Codex was running.
45. As a researcher, I want a human edit outside the protected section flagged as a page conflict, so that it is never silently overwritten.
46. As a researcher, I want automatic updates to pause on a conflicted page, so that I can decide whether to move, retain, or absorb my edit.
47. As a researcher, I want to browse paper and topic pages in the web application, so that reading the wiki does not require switching to Obsidian.
48. As a researcher, I want web wiki pages to remain read-only, so that the MVP has one clear editing path through Obsidian.
49. As a researcher, I want wiki search in the web application, so that I can locate relevant paper and topic pages quickly.
50. As a researcher, I want wikilinks and backlinks to be clickable in the web reader, so that I can follow the maintained knowledge graph.
51. As a researcher, I want a visually polished force-directed graph, so that I can see the shape of the research collection.
52. As a researcher, I want graph nodes colored by page type and sized by connection count, so that important hubs and categories are recognizable.
53. As a researcher, I want lightweight graph pan, zoom, hover labels, and click-to-open behavior, so that the visualization is useful without becoming a graph editor.
54. As a researcher, I want one research thread persisted across application restarts, so that I can continue an investigation without losing conversational context.
55. As a researcher, I want research chat to read the latest fully published wiki snapshot, so that answers never depend on partial ingests.
56. As a researcher, I want to continue using chat while an ingest is processing, so that background maintenance does not block exploration.
57. As a researcher, I want chat to state when a pending source is not yet available, so that I do not assume an in-progress paper informed the answer.
58. As a researcher, I want chat to prioritize ingested sources, so that answers begin with the lab's curated evidence.
59. As a researcher, I want Codex to use live web search when ingested evidence is insufficient, so that research chat retains general research capability.
60. As a researcher, I want lab sources and external research sources labeled and cited separately, so that I can distinguish curated evidence from live research.
61. As a researcher, I want chat to name gaps in the ingested evidence, so that I know which additional papers may be worth adding.
62. As a researcher, I want research chat to remain read-only, so that ordinary conversation cannot mutate persistent wiki knowledge.
63. As a researcher, I want to explicitly file a useful chat analysis, so that valuable exploration can become durable wiki knowledge.
64. As a researcher, I want an ordinary chat answer to remain outside the wiki unless I file it, so that transient conversations do not pollute the knowledge base.
65. As a researcher, I want external claims omitted from a filed analysis unless their evidence has first been ingested, so that the persistent wiki retains a closed evidence boundary.
66. As a researcher, I want a filed cross-paper synthesis to cite at least two ingested sources, so that it is more than a single-paper summary.
67. As a researcher, I want responses streamed as Codex works, so that research chat feels responsive.
68. As a researcher, I want concise progress states such as searching the wiki or searching the web, so that I understand what Codex is doing without seeing internal tool output.
69. As a researcher, I want raw shell output, tool calls, and hidden reasoning omitted from the chat UI, so that the interface remains readable and safe.
70. As a researcher, I want to trigger wiki lint explicitly, so that I control when broad maintenance occurs.
71. As a researcher, I want wiki lint to check contradictions, stale claims, orphan pages, missing links, possible duplicates, and evidence gaps, so that the knowledge base remains healthy.
72. As a researcher, I want lint updates staged and published atomically, so that maintenance cannot leave the wiki inconsistent.
73. As a researcher, I want the Local MVP to work without PostgreSQL, so that operational state remains simple and file-based.
74. As a researcher, I want the Local MVP to work without vector search, so that it proves the LLM Wiki workflow before introducing retrieval infrastructure.
75. As a researcher, I want Codex to navigate through the index, wikilinks, and ordinary Markdown search, so that navigation follows the LLM Wiki pattern.
76. As a developer, I want the same Codex CLI execution path locally and on a future EC2 host, so that the MVP validates the intended production worker.
77. As a developer, I want the LLM Wiki skill versioned with ResearchOS, so that ingest, query, and lint behavior changes through reviewed repository history.
78. As a developer, I want one skill with explicit ingest, query, and lint workflows, so that shared schema and evidence conventions do not drift.
79. As a developer, I want vault-level agent guidance to require the skill and preserve non-negotiable invariants, so that every Codex run follows the adapted LLM Wiki pattern.
80. As a developer, I want ingest and lint writers to run without network access, so that automatic wiki evidence can come only from stored sources.
81. As a developer, I want live web access enabled only for research chat, so that broader research capability does not leak into automatic maintenance.
82. As a developer, I want a deterministic fake Codex executable available to automated tests, so that the complete external workflow can be tested without network or model variability.
83. As a developer, I want a manual smoke test against real Codex, so that the adapter, permissions, skill, and research behavior are validated end to end.

## Implementation Decisions

- The Local MVP is a single-user, localhost-only application run through Docker Compose. It has no login flow.
- The application is a Python FastAPI monolith with server-rendered pages, HTMX for uploads, job status, and streamed research interactions, and a small D3 component for the knowledge graph.
- The web application has four primary areas: Library, Research, Wiki, and Graph. No separate dashboard is required.
- Library owns PDF upload, source status, metadata correction, retry, and withdrawal.
- Research owns one persisted Codex research thread, streamed answers, evidence grouping, and the explicit file-analysis action.
- Wiki provides read-only page rendering, ordinary text search, wikilink navigation, backlinks, and access to the activity log.
- Graph renders a read-only force-directed projection of explicit wikilinks. It supports node colors by page type, node size by connection count, hover labels, pan/zoom, and click-to-open; it does not edit or infer relationships.
- The MVP uses file-based manifests, job records, research-thread state, and source/runtime storage. It does not use a SQL database.
- Source storage is behind a small application interface. The Local MVP implementation uses a bind-mounted filesystem volume; a future deployment may implement the same interface with S3.
- The exact uploaded PDF is immutable and authoritative. It is retained in source storage and is not committed to the wiki's Git history.
- Source identity is based on the SHA-256 digest of the exact PDF bytes. The human-facing filename and title do not determine identity.
- Identical content is deduplicated. Different bytes remain distinct, even when filenames or bibliographic metadata match.
- Corrected or revised PDFs are separate source revisions linked to the versions they revise. They never silently replace prior evidence.
- Source metadata includes title, authors, year, and DOI when available. Local extraction populates it, the filename is the uncertainty fallback, and researcher corrections are authoritative.
- Ingested sources use a withdrawal lifecycle rather than ordinary hard deletion. A pre-ingest upload may be removed; a completed ingest is preserved, marked withdrawn, excluded from future synthesis by default, and reflected in affected wiki knowledge.
- Exceptional legal/privacy purge is not implemented in the Local MVP.
- MarkItDown's built-in local PDF converter is the MVP extraction component. MarkItDown and all parser dependencies are pinned.
- Conversion runs with plugins disabled, no network access, least privilege, local input only, and explicit resource limits.
- ResearchOS produces one immutable, page-addressable Markdown derivative per source. Every physical PDF page has an explicit marker.
- A derivative manifest records source digest, output digest, converter/dependency versions, configuration, and conversion timestamp. Converter changes create a new derivative version rather than silently replacing an existing artifact.
- The derivative is Codex's default reading and search representation but is never authoritative evidence.
- Extraction validation detects empty, garbled, missing, or structurally degraded content. Codex may inspect the stored original PDF when figures, equations, tables, or layout matter, but the MVP has no researcher-facing PDF or derivative viewer.
- Scanned/image-only PDFs are unsupported in the MVP. ResearchOS detects inadequate text extraction and records a clear OCR-required failure rather than publishing knowledge.
- Upload immediately creates a file-backed job and returns. One FIFO worker processes one ingest at a time.
- One automatic retry is allowed for a transient conversion or Codex failure. A second failure records the error and exposes manual retry using the same immutable source and derivative.
- Chat continues against the latest published snapshot while jobs run. Pending sources are explicitly unavailable until publication succeeds.
- Codex CLI is the sole AI research worker in both the Local MVP and future EC2 deployment. The application owns deterministic concerns such as storage, job state, validation, permissions, and publication.
- The repository contains and versions one LLM Wiki skill with ingest, query, and lint workflows. The skill operationalizes the conventions in the conceptual LLM Wiki reference.
- Vault-level agent guidance requires use of the skill and states permanent schema and evidence invariants.
- Ingest reads the existing index first, reads the new Markdown derivative, creates or updates relevant pages and relationships, updates the index and activity log, validates the result, and publishes automatically.
- Query reads the current wiki and ingested derivatives as needed. It may use live web search only from research chat.
- Wiki lint runs only when requested by the researcher. It checks contradictions, stale claims, orphan pages, missing cross-references, possible duplicates, and evidence gaps.
- Research chat runs with read-only filesystem permissions for the live wiki. It cannot directly create, edit, or commit wiki pages.
- Ingest, wiki lint, and explicitly filing an analysis run as separate constrained writer jobs against a staged wiki.
- Ingest and lint have network access disabled. Research chat has Codex live web search enabled.
- A filed analysis may contain only claims supported by ingested sources. External research remains conversational until its evidence is deliberately uploaded as a PDF and ingested.
- Writer jobs operate from a fixed Git snapshot, preserve protected annotations, run the complete validation gate, and publish exactly one commit only when all checks succeed.
- The publication gate requires resolvable source/page citations, valid explicit wikilinks or possible-duplicate flags, updated index and activity log, unchanged protected annotations, valid page metadata, and at least two ingested sources for filed cross-paper synthesis.
- Any validation or write failure publishes no partial edits. The live wiki remains on its previous complete commit.
- Successful ingest, lint, and filed-analysis updates each produce one Git commit. Git is the detailed history and rollback mechanism; the Markdown activity log is the researcher-facing narrative.
- Original PDFs, Markdown derivatives, source manifests, job records, and chat transcripts remain outside the Git-versioned vault.
- The vault contains permanent agent guidance, an index, an activity log, paper pages, topic pages, and explicitly filed analysis pages.
- Every wiki page has minimal YAML frontmatter containing page type, stable page identity, title and aliases, supporting source identities, and creation date.
- Paper pages contain bibliographic metadata, a concise summary, key findings, methods, datasets, limitations, related pages, contradictions/open questions, evidence citations, and a final protected researcher-annotation section.
- Topic pages represent only substantive concepts or methods with reusable definitions, assumptions, variants, evidence, or relationships. Incidental terms remain inline on paper pages.
- Topic pages are the primary maintained home for evidence accumulated across papers. Standalone synthesis pages are created only when a researcher explicitly files an analysis.
- Codex creates semantic relationships as explicit Obsidian wikilinks. Obsidian and the web graph render those relationships and backlinks; neither infers semantic edges independently.
- Ambiguous concept/method identity creates separate pages marked as possible duplicates. Codex does not merge them without sufficient confidence.
- Contradictions preserve all incompatible claims with source context and evidence citations. Codex does not select the scientifically correct claim for the researcher.
- Evidence citations use native Markdown footnotes with a human-readable paper title, physical PDF page, and stable source identity. Citations are displayed without an in-app document viewer.
- Every page has a designated researcher-annotation section. Writer jobs preserve it byte-for-byte.
- A filesystem watcher creates a debounced researcher-edit Git commit after Obsidian writes to the vault, so the researcher does not need to operate Git.
- A researcher edit to an AI-managed section is committed for history, creates a page conflict, and pauses automatic updates to that page until resolved.
- If an annotation commit lands during a staged writer operation, the writer rebases onto the new head, revalidates the full change, and publishes only if annotations remain unchanged.
- The index is content-oriented and updated on every successful ingest, lint update, or filed analysis. It lists pages by category with wikilinks and concise summaries.
- The activity log is chronological and append-only. Each entry identifies operation type, source or analysis, affected pages, contradictions, possible duplicates, and outcome.
- Research chat persists one Codex session/thread and transcript as file-based state across application restarts. Multiple named threads are not implemented.
- Research answers prioritize ingested evidence. When live web search is used, the response visibly separates "Lab sources" from "External sources" and names the gap in the lab collection.
- Research chat streams the answer plus concise progress states. Raw tool calls, shell output, and internal reasoning are not exposed.
- Ordinary research answers are not filed automatically. A researcher explicitly requests filing, which launches the staged writer workflow.
- The web wiki is read-only. Researcher annotation editing occurs in Obsidian.
- Obsidian is not embedded in the web application. Both interfaces consume the same Markdown vault, and the web application may provide local Obsidian URI links where useful.
- PostgreSQL, vector search, and embedding infrastructure are deferred. Codex navigates through the index, explicit wikilinks, backlinks, and ordinary Markdown/file search.

## Testing Decisions

- The primary automated seam is the complete public web/API boundary. Tests exercise user-visible workflows from PDF upload through persisted outputs rather than calling converter, queue, wiki, or Git internals directly.
- Automated tests substitute a deterministic fake Codex CLI executable behind the same process interface used in production. The fake emits controlled progress, answers, staged wiki changes, malformed output, failures, and retry outcomes.
- Good tests assert external behavior and durable artifacts: HTTP responses, streamed events, job states, rendered pages, graph data, source manifests, vault contents, activity entries, and Git commits. They do not assert private function calls, internal class structure, exact prompts, or nondeterministic prose.
- Because the repository has no existing application or tests, there is no prior test seam to preserve. The high-level application seam is intentionally introduced as the single primary seam.
- A small set of lower-level contract tests is permitted only where external end-to-end tests cannot cheaply establish safety: the Codex process protocol, page-marker/citation validation, and protected-annotation merge rules.
- The main happy-path acceptance test uploads two related text-based PDFs and verifies: both complete ingest; each has an immutable source record and page-addressable derivative; paper/topic pages are created; cross-paper evidence accumulates; explicit wikilinks produce backlinks and graph edges; citations identify physical pages; index/log are updated; and each ingest produces one commit.
- A research acceptance test asks a question supported by both papers and verifies that the response uses lab citations and performs cross-paper synthesis without writing to the vault.
- An external-research acceptance test asks an unsupported question and verifies that chat names the evidence gap, uses live web search through the fake adapter, labels external citations separately, and leaves the wiki unchanged.
- A filing acceptance test explicitly files a corpus-supported analysis and verifies a separate staged writer job, validation, one atomic commit, index/log updates, and at least two supporting source identities.
- A read-only-chat test attempts to induce wiki edits from ordinary conversation and verifies that the live vault and Git head remain unchanged.
- A failure-atomicity test makes the fake Codex writer edit multiple staged pages and then fail; the live wiki, index, log, and Git head must remain unchanged.
- A validation test supplies missing citations, invalid page locators, broken wikilinks, absent index/log updates, modified annotations, or a one-source cross-paper analysis and verifies that publication is rejected.
- A retry test produces one transient failure followed by success and verifies automatic recovery; a second scenario fails twice and verifies a stable failed state and manual retry.
- A deduplication test uploads identical bytes under different filenames and verifies one source identity, then uploads different bytes under the same filename and verifies distinct identities.
- A revision test uploads a corrected PDF with related metadata and verifies separate source identities linked as revisions without changing historical citations.
- A metadata test verifies local extraction, filename fallback, researcher correction, and propagation of authoritative metadata to the paper page.
- A withdrawal test verifies that a withdrawn source remains stored and historically cited, is visibly marked, and is excluded from future synthesis by default.
- A conversion test verifies a marker for every physical page, recorded hashes and converter versions, safe rejection of scans and extraction-poor PDFs, and no network access from the converter.
- A prompt-injection test embeds agent-like instructions in a paper and verifies that they remain quoted source data and do not alter the ingest workflow.
- An annotation test edits the protected section in Obsidian-visible storage, verifies an automatic researcher commit, runs another ingest, and verifies byte-for-byte preservation.
- A concurrent-edit test lands an annotation while a writer is staged and verifies rebase, revalidation, preservation, and one final writer commit.
- A page-conflict test edits AI-managed content and verifies a flagged conflict and paused automatic update rather than overwrite.
- A persistence test restarts the application and verifies source/job state, the single research thread, transcript, wiki, and Git history remain available.
- A graph test verifies that only explicit wikilinks become edges and that page type, connection count, labels, and navigation data are exposed; it does not test D3 layout coordinates.
- A UI smoke test covers the four primary areas and verifies that the web wiki cannot edit page content.
- A manual real-Codex smoke test runs the same two-paper flow with the versioned skill, real Codex CLI authentication, actual permission profiles, disabled writer networking, chat web search, and Obsidian inspection.
- Real-Codex tests evaluate structural outcomes and citation traceability, not exact prose. The selected two papers must be related enough to produce one meaningful cross-paper result.

## Out of Scope

- Cloud deployment, EC2 provisioning, S3 configuration, production networking, TLS, and operational monitoring.
- Multi-user collaboration, accounts, authentication, authorization, roles, or lab administration.
- PostgreSQL, SQLite, database migrations, vector databases, embeddings, hybrid retrieval, qmd integration, or dedicated keyword-search services.
- More than one research thread, named chats, thread archival UI, or cross-thread coordination.
- Concurrent ingest workers or parallel wiki writers.
- Scanned/image-only PDF support, OCRmyPDF, Tesseract, MarkItDown's generative OCR plugin, or other OCR pipelines.
- Webpage, DOCX, PPTX, dataset, audio, image, or arbitrary-file ingestion. Persistent evidence is PDF-only.
- A researcher-facing PDF viewer, Markdown-derivative viewer, or clickable citation-to-document navigation.
- Web-based wiki editing, annotation editing, graph editing, relationship creation, or drag-and-drop graph layout persistence.
- Advanced graph filters, timelines, communities, clustering, semantic edges, keyword-inferred edges, or large-graph performance optimization.
- Automatic scheduling of wiki lint or other maintenance workflows.
- Automatic filing of ordinary chat answers.
- Automatic ingestion of external web-search results.
- Automatic resolution of contradictions or ambiguous possible duplicates.
- Dedicated researcher or dataset pages unless a later design promotes them.
- Exceptional legal/privacy purge after ingest.
- Obsidian Sync, Obsidian Publish, an embedded Obsidian runtime, or a custom Obsidian plugin.
- High-fidelity scientific PDF parsing guarantees, visual figure understanding guarantees, or a permanent commitment to MarkItDown.
- A Docling migration or parser bake-off beyond recording benchmark hooks and representative acceptance documents.
- Production-grade queue infrastructure, message brokers, distributed locks, or horizontal scaling.
- A separate JavaScript single-page application or standalone frontend service.

## Further Notes

- The conceptual LLM Wiki document remains the source pattern. ResearchOS intentionally adapts it by allowing protected researcher annotations, adding a web interface, using staged atomic writers, and separating live external research from persistent wiki evidence.
- The domain glossary is authoritative for terms such as Local MVP, ingested source, Markdown derivative, paper page, topic page, research chat, filed analysis, possible duplicate, contradiction, and page conflict.
- Existing ADRs govern researcher annotations, chat/wiki evidence separation, Codex CLI, atomic Git publication, Markdown derivatives, source withdrawal, source storage outside Git, and read-only chat.
- The high-level project overview remains aspirational about future cloud architecture. Where it mentions PostgreSQL, vector search, or continuously hosted services, this Local MVP spec takes precedence for the implementation effort.
- MarkItDown is an MVP component rather than a permanent parser choice. Representative papers should include ordinary prose, two-column layouts, tables, equations, and figures so extraction weaknesses become visible early.
- Markdown-first ingestion is expected to reduce repeated multimodal processing for text-heavy work, but no universal token or latency saving is assumed. Capture conversion time, derivative size, and end-to-end ingest duration so later parser decisions have project-specific evidence.
- Original PDFs remain authoritative even though the MVP does not expose a document viewer. Page-level citations are still validated against physical page boundaries during ingest.
- The application should be designed so future database, S3, OCR, authentication, multiple-thread, and hybrid-search implementations can replace infrastructure adapters without changing the LLM Wiki domain model.
