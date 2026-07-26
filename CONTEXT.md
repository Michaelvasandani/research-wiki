# ResearchOS

ResearchOS is a continuously maintained research knowledge base. It compiles curated research sources into an AI-maintained Markdown wiki while preserving the sources as evidence.

## Language

**Local MVP**:
A single-user ResearchOS deployment that runs its web application, API, and source storage locally through Docker Compose, while using Codex CLI as its AI research worker and files for wiki navigation and operational state.
_Avoid_: SQL database, direct model integration, vector search, fully local AI, cloud deployment

**Cross-paper synthesis**:
An analysis that reconciles claims, concepts, and evidence from at least two source papers. It may appear in research chat, accumulate within a topic page, or become a standalone filed analysis; it is distinct from a summary of one paper.
_Avoid_: Multi-document summarization

**Wiki update**:
A set of AI-maintained changes that integrates a source or synthesis into the research wiki. ResearchOS publishes wiki updates automatically and makes their supporting evidence traceable.
_Avoid_: Approval request, draft update

**Evidence citation**:
A Markdown footnote from a wiki claim to its supporting source paper and pinpoint location, at least a physical PDF page number. The Local MVP displays citations without an in-app document viewer.
_Avoid_: Reference, source link

**Ingested source**:
A paper deliberately added to ResearchOS as evidence. Only ingested sources may support an automatically published wiki update.
_Avoid_: Web source, external reference

**Source identity**:
The stable identity of an ingested source, determined by its exact PDF content rather than its filename or title. Identical PDF bytes represent the same source.
_Avoid_: Filename, paper title

**Source revision**:
An ingested source that represents a corrected or revised form of another source. Each revision remains separate evidence and is linked to the versions it revises.
_Avoid_: Replacement file, duplicate source

**Source metadata**:
Researcher-correctable bibliographic information for an ingested source, including title, authors, year, and DOI when available. Once corrected, it is authoritative for ResearchOS.
_Avoid_: Generated summary, PDF filename

**Withdrawn source**:
An ingested source excluded from future synthesis because it was retracted, judged unreliable, or added by mistake. ResearchOS preserves the source and its historical citations while marking affected wiki knowledge.
_Avoid_: Deleted source, active evidence

**Markdown derivative**:
An immutable, page-addressable Markdown representation generated from an ingested source for efficient Codex reading and search. It is not evidence; the original paper remains authoritative.
_Avoid_: Source of truth, wiki page

**Ingest**:
The Codex workflow that integrates an uploaded paper into the research wiki and its cross-paper knowledge. It is distinct from storing the paper itself.
_Avoid_: Upload, import

**Wiki page**:
An AI-maintained Markdown artifact in the research wiki. The Local MVP creates paper pages and topic pages; an explicitly filed analysis may add a standalone synthesis page.
_Avoid_: Note, document

**Paper page**:
A wiki page that integrates one ingested source's bibliographic metadata, summary, findings, methods, datasets, limitations, relationships, contradictions, open questions, and evidence citations.
_Avoid_: Markdown derivative, source paper

**Topic page**:
A wiki page that synthesizes reusable knowledge about a concept or method central to at least one ingested source. Incidental terminology remains on the paper page.
_Avoid_: Term mention, glossary entry

**Knowledge graph**:
The network formed by wiki pages and their wikilinks. ResearchOS visualizes this network to show connections among papers, concepts, methods, and syntheses.
_Avoid_: Database graph, editable diagram

**Possible duplicate**:
Two wiki pages that may represent the same concept or method but have not been confidently identified as one. ResearchOS keeps them separate and flags the relationship for the researcher.
_Avoid_: Merged page, synonym

**Researcher annotation**:
Human-authored content within a wiki page's designated researcher-annotation section. ResearchOS preserves that section byte-for-byte during automatic updates.
_Avoid_: AI-managed content, generated text

**Page conflict**:
A human edit to an AI-managed section of a wiki page. ResearchOS preserves the edit, flags the page, and pauses automatic changes to it until the researcher resolves the conflict.
_Avoid_: Researcher annotation, overwritten edit

**Activity log**:
An append-only, human-readable record of an ingest or automatic wiki update. Each entry names the source, affected pages, and any contradictions or possible duplicates found.
_Avoid_: Change history, audit record

**Research chat**:
The conversational research interface. It prioritizes ingested sources but may use external search when the ingested evidence is insufficient; external results do not become wiki evidence automatically.
_Avoid_: Wiki update, ingestion

**Research thread**:
A persisted research-chat conversation that can be resumed across application restarts. Its transcript is conversational history, not wiki knowledge.
_Avoid_: Wiki page, filed analysis

**External research source**:
A source discovered through research-chat search rather than the lab's ingested collection. Research chat labels and cites it separately from ingested evidence.
_Avoid_: Ingested source, wiki evidence

**Filed analysis**:
A research-chat result that the researcher explicitly chooses to preserve as a wiki page. Ordinary chat answers are not filed automatically.
_Avoid_: Chat history, automatic wiki update

**Wiki lint**:
A researcher-triggered Codex health check for contradictions, stale claims, orphan pages, missing links, and evidence gaps across the wiki.
_Avoid_: Ingest validation, scheduled maintenance

**Contradiction**:
Incompatible claims from two or more source papers. ResearchOS presents each claim with its evidence citations and does not choose between them for the researcher.
_Avoid_: Resolved conflict, incorrect claim
