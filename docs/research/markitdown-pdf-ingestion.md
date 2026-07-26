# PDF-to-Markdown ingestion for ResearchOS

Research date: 2026-07-25

## Recommendation

Convert uploaded PDFs to a canonical, page-addressable Markdown derivative before Codex performs normal ingestion, while preserving the original PDF as the immutable source of truth.

Use MarkItDown's local built-in PDF converter as an MVP extraction component, not as the complete citation pipeline:

1. Store the original PDF unchanged and record its SHA-256 digest.
2. Run a pinned version of `markitdown[pdf]` locally, with plugins disabled and no network access.
3. Convert one physical PDF page at a time, or wrap the extractor so that the canonical Markdown contains an unambiguous marker such as `<!-- pdf-page: 12 -->` before every page.
4. Store a manifest with the source digest, converter and dependency versions, configuration, timestamp, and output digest. Treat the derivative as immutable; a converter upgrade creates a new derivative rather than silently replacing it.
5. Validate the result. If a page is empty, visibly garbled, or materially depends on a figure, table, or equation that was not represented adequately, have Codex inspect the corresponding original PDF page. Do not publish a wiki claim from degraded extraction alone.
6. For the Local MVP, detect scanned or extraction-poor PDFs and reject them with a clear unsupported/OCR-required status. If scanned-paper support is added later, prefer a pinned OCRmyPDF/Tesseract stage before MarkItDown; do not use MarkItDown's LLM-vision OCR plugin as the canonical deterministic extractor.

This is preferable to sending every full PDF directly to a vision-capable model for routine, text-heavy work. OpenAI's PDF file-input path places both extracted text and page images into model context, which OpenAI warns can increase token usage. A reusable Markdown derivative avoids repeatedly paying for page-image context and is directly searchable with ordinary file tools. However, no primary source found establishes a universal token-count or latency ratio for MarkItDown versus direct PDF input, so the expected savings should be measured on the project's representative papers rather than stated as guaranteed.

Before committing to MarkItDown for all research papers, benchmark it against a more layout-aware converter such as Docling on a small acceptance corpus containing two-column prose, tables, equations, plots, and scanned pages. MarkItDown is attractive for the MVP because it is small and local, but its built-in PDF converter is not a high-fidelity scientific-paper parser.

## What the primary sources establish

### Markdown and model cost

Microsoft describes MarkItDown as a lightweight converter intended for LLM and text-analysis pipelines. Its rationale is that Markdown retains useful structure with little markup and is token-efficient. This is a project claim, not a published benchmark. The project also cautions that the output targets text analysis rather than high-fidelity human document conversion. [MarkItDown README](https://github.com/microsoft/markitdown#markitdown)

OpenAI documents that direct PDF file inputs include both extracted text and page images in context and therefore can increase token usage. Visual detail can be adjusted in the Responses API, but the image portion is still a meaningful cost consideration. [OpenAI file-input usage considerations](https://developers.openai.com/api/docs/guides/file-inputs#usage-considerations)

Therefore:

- It is reasonable to expect a text-only Markdown derivative to be cheaper and often faster for repeated, text-centric analysis than repeatedly supplying the full PDF as a multimodal file.
- It is not established that Markdown uses fewer text tokens than OpenAI's own extracted text, nor that conversion always improves answer quality.
- Direct page-image inspection remains valuable for layout, plots, diagrams, equations, and extraction failures.

### Built-in PDF conversion behavior

The current built-in converter depends on `pdfminer.six` and `pdfplumber`. Those are the only dependencies in the package's `pdf` extra. [MarkItDown package configuration](https://github.com/microsoft/markitdown/blob/main/packages/markitdown/pyproject.toml)

The converter:

- reads the complete input stream into memory;
- iterates pages with pdfplumber;
- applies positional heuristics for form-like/table-like pages;
- otherwise extracts page text;
- falls back to pdfminer for the whole document when no form-style pages are detected or when pdfplumber fails; and
- returns one Markdown string. [Built-in PDF converter source](https://github.com/microsoft/markitdown/blob/main/packages/markitdown/src/markitdown/converters/_pdf_converter.py)

The source explicitly says its borderless-table heuristic is intended for structured tabular data such as invoices, not multi-column text layouts in scientific documents. The fallback path is plain text extraction. [Table extraction source](https://github.com/microsoft/markitdown/blob/main/packages/markitdown/src/markitdown/converters/_pdf_converter.py#L361-L368)

The implementation does not emit page-boundary markers in the built-in conversion result. Although it traverses pages internally, it appends their content and joins the chunks without identifiers; when it uses pdfminer for the entire document, even that per-page loop is bypassed for final output. [Conversion implementation](https://github.com/microsoft/markitdown/blob/main/packages/markitdown/src/markitdown/converters/_pdf_converter.py#L490-L534)

Consequences for ResearchOS:

- A single ordinary `markitdown paper.pdf` output is unsuitable as the sole basis for pinpoint page citations.
- Physical page markers must be injected by a ResearchOS wrapper, preferably by extracting pages independently.
- Citations should use the one-based physical PDF page sequence. Printed page labels may differ and can be stored as optional metadata, but must not replace the stable physical-page locator.

### Structure and information loss

The built-in PDF converter has code for text and heuristic Markdown tables, but no built-in path in that converter for exporting figures, describing images, preserving PDF metadata, or modeling equations. Its return value is only the extracted Markdown string. [Built-in PDF converter source](https://github.com/microsoft/markitdown/blob/main/packages/markitdown/src/markitdown/converters/_pdf_converter.py)

Accordingly:

- **Page numbers:** not preserved as page provenance by the built-in converter.
- **Figures and plots:** not included or described by the built-in converter. Captions may survive if they are ordinary extractable text.
- **Tables:** simple/form-like layouts may become Markdown tables, but scientific tables and multi-column paper layouts are not guaranteed.
- **Equations:** there is no equation-specific representation; symbols and reading order depend on generic PDF text extraction and may degrade.
- **Metadata:** PDF metadata fields are not returned. Visible title and author text may be extracted as body text, but that is not metadata preservation.
- **Headings and reading order:** the built-in path largely produces extracted text, not a reconstructed semantic paper hierarchy. Complex and two-column layouts require validation.

These are implementation-level observations, not claims that every such element will always be lost.

### Determinism

MarkItDown does not document a byte-for-byte determinism guarantee. The local built-in PDF converter contains fixed extraction logic and does not call an LLM, so the same file in a pinned runtime is suitable for a repeatable conversion stage. Reproducibility still requires pinning MarkItDown, pdfminer, pdfplumber, Python, and preferably the container image, because parser and heuristic changes can change output. The package currently identifies itself as beta in its project metadata. [MarkItDown package configuration](https://github.com/microsoft/markitdown/blob/main/packages/markitdown/pyproject.toml)

The canonical property should therefore come from ResearchOS:

- pin the environment;
- record input and output digests;
- retain the generated artifact;
- never regenerate it implicitly; and
- version migrations explicitly.

This yields a deterministic ingestion record even though upstream does not promise that every future MarkItDown version produces identical Markdown.

### Scanned PDFs and OCR

The built-in PDF converter has no OCR stage. MarkItDown now offers an optional OCR plugin that sends embedded or full-page images to an OpenAI-compatible vision model. For pages with no extractable text, it renders the page at 300 DPI and sends the image to the model. If an LLM call fails, conversion continues without that image's text; if no client is configured, OCR is silently skipped. [MarkItDown OCR plugin documentation](https://github.com/microsoft/markitdown/blob/main/packages/markitdown-ocr/README.md)

That plugin conflicts with the requirements for a deterministic canonical derivative and for Codex CLI to remain the sole research worker:

- output depends on an external generative model;
- it requires a separate API client/model path;
- calls can fail partially while conversion continues; and
- the output is not documented as reproducible.

For scanned sources, OCRmyPDF is a materially different fallback: it uses Tesseract to add a searchable text layer to the PDF while attempting to preserve the original visible content. Its documentation also clearly states OCR limitations, including errors, weak reading-order handling, and no paragraph/heading structure. [OCRmyPDF introduction and limitations](https://ocrmypdf.readthedocs.io/en/latest/introduction.html)

A safe future scanned-paper flow is:

```text
original.pdf
  -> pinned OCRmyPDF/Tesseract (only when needed)
  -> OCR derivative PDF
  -> page-aware MarkItDown extraction
  -> canonical Markdown derivative
```

The original PDF remains the source of truth, and OCR-derived claims should retain an extraction-quality warning until visually checked. This flow is intentionally deferred from the Local MVP.

### Security and operations

MarkItDown warns that it performs I/O with the privileges of its process. In hosted environments it requires input validation and restriction, including file paths, URI schemes, network destinations, and access to private, loopback, link-local, or cloud metadata-service addresses. It recommends using the narrowest API, such as `convert_local()` for local files or `convert_stream()` for maximum control, instead of the permissive general `convert()` method. [MarkItDown security considerations](https://github.com/microsoft/markitdown#security-considerations)

For the EC2 service:

- accept uploaded bytes into an isolated object, not an arbitrary user-supplied path or URL;
- invoke `convert_stream()` or an explicitly scoped `convert_local()` path;
- disable plugins by default;
- deny converter network access;
- run conversion as an unprivileged process in a sandbox/container;
- enforce PDF size, page-count, memory, CPU, and wall-clock limits;
- account for the built-in converter reading the entire PDF into memory;
- record failures rather than publishing partial wiki updates; and
- treat extracted paper text as untrusted source data, not as Codex instructions.

### Why consider Docling in the benchmark

Docling's official project materials describe PDF-specific layout and reading-order analysis, table structure, formulas, pictures, OCR, provenance, bounding boxes, and both Markdown and lossless JSON output. These capabilities align more directly with scientific papers and pinpoint evidence mapping than MarkItDown's lightweight built-in PDF path. It is also a heavier pipeline, so a representative benchmark should decide whether the added fidelity is worth the operational cost. [Docling project](https://github.com/docling-project/docling#docling) and [Docling document model](https://docling-project.github.io/docling/concepts/docling_document/)

## MVP acceptance test

Evaluate at least ten representative papers and require:

- every physical PDF page has a corresponding marker in the Markdown derivative;
- section prose remains in correct reading order;
- title and author information is captured or separately recorded;
- tables, figures, and equations are either represented adequately or explicitly flagged for original-page inspection;
- a sampled set of claims round-trips from Markdown citation to the correct PDF page;
- re-running the pinned container produces the same output digest;
- malformed, encrypted, oversized, and scanned PDFs fail safely or enter the declared fallback path; and
- Markdown token count, conversion time, and end-to-end Codex ingestion time are measured against direct PDF ingestion on the same corpus.

## Bottom line

The user's intuition is directionally correct: a persistent Markdown derivative is a better default working format for the LLM Wiki than repeatedly reading full PDFs, especially because direct PDF model input includes page images as well as text. MarkItDown is a sensible lightweight MVP component. It is not, by itself, enough for ResearchOS: page-aware wrapping, immutable provenance, validation, and original-PDF inspection for degraded visual content are required. The Local MVP rejects scanned PDFs; an OCR path and a Docling benchmark can follow before a long-term parser commitment.
