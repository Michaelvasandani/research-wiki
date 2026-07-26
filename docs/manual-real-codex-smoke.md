# Real-Codex Local MVP smoke test

This is the repeatable, manual complement to the deterministic test suite. It
uses a normal, already authenticated Codex CLI account; it does not need a
database or a vector-search service. Evaluate the durable structure and
evidence traceability, not the exact wording Codex chooses.

## 1. Prepare a clean checkout

Keep the default Docker Compose flow for deterministic checks. Its checked-in
fake worker is deliberate and needs no account or network access. Run the
real-Codex smoke from the host instead, because the host Codex installation
already has its ordinary login state:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
codex login
codex exec --help
rm -rf data-real-codex
RESEARCHOS_DATA_DIR="$PWD/data-real-codex" \
CODEX_COMMAND="$PWD/scripts/real-codex" \
uvicorn researchos.main:create_app --factory --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. The process is deliberately bound to loopback.
`scripts/real-codex` translates ResearchOS's small JSON-lines worker protocol
to the authenticated `codex exec` CLI and reads the repository-versioned
[`LLM Wiki` skill](../.agents/skills/llm-wiki/SKILL.md) for each operation.
Do not point `CODEX_COMMAND` at bare `codex`: the CLI and ResearchOS use
different process protocols.

The adapter uses Codex's actual `workspace-write` permission for an ingest,
filed-analysis, or lint run, with the staged vault as its working directory;
the application then adds its OS sandbox (macOS `sandbox-exec` or Linux
Bubblewrap), which permits writes only in that stage and disables networking.
Research uses Codex's `read-only` permission against a published snapshot and
enables Codex web search. It cannot write that snapshot. These are the
permission profiles to inspect during the smoke, not advisory environment
variables.

## 2. Use a representative two-paper corpus

Choose two related, text-based PDFs. The first should be ordinary prose and
the second should include at least one extraction-sensitive feature, such as a
two-column page, a table, an equation, or a figure with a meaningful caption.
Record their filenames and SHA-256 digests. Do not use scanned or image-only
papers: the Local MVP should reject those as requiring OCR.

In **Library**, upload the first PDF and wait for `completed`; upload the
second and wait for `completed`. For each source, verify:

- an immutable SHA-256 source identity and a page-addressable derivative exist
  under `data-real-codex/`;
- its paper page has page-level Markdown footnotes, including physical PDF page
  numbers, and the cited claims can be checked against the original PDF;
- `index.md`, `log.md`, topic pages, explicit wikilinks, backlinks, and the
  Graph show the accumulated relationship; and
- `git -C data-real-codex/vault log --oneline` gained exactly one ingest commit
  per completed upload, while both `git -C data-real-codex/vault ls-files` and
  `git -C data-real-codex/vault log --all --name-only --format=` contain no
  PDF, derivative, manifest, job, or transcript artifact. The history command
  matters: a deleted artifact must not be able to hide in an older commit.

The Library displays conversion time, derivative size, and end-to-end ingest
duration for each completed source. Preserve those values with the test notes;
the durable source of the same measurements is
`data-real-codex/runtime/ingest-jobs.json`.

## 3. Exercise research and maintenance

In **Research**, ask a question that requires both papers. Confirm that the
answer names both lab sources and is a synthesis rather than a one-paper
summary. File it explicitly, then verify that a cited analysis page, index/log
entry, graph node, and exactly one new Git commit appear. An ordinary answer
before filing must not change the vault.

Ask one question unsupported by the uploaded corpus. Confirm that chat states
the lab-evidence gap and labels web results under **External sources**. The
external result must not appear in the source manifest, derivative store, wiki,
or Git history. This confirms that live web access is available only to the
read-only chat profile.

Correct one paper's metadata in Library, upload a distinct corrected PDF as a
revision, and withdraw one completed source. Confirm that original citations
remain resolvable, revisions link both directions, and the withdrawn source is
excluded from later research. Trigger **Wiki lint** from Wiki; it must produce
at most one atomic maintenance commit and retain contradictions, possible
duplicates, and annotations rather than silently resolving them.

## 4. Inspect through Obsidian and the web UI

Open `data-real-codex/vault` as a vault in Obsidian. Add text only inside a
page's final `Researcher annotations` markers, save, wait for the debounced
researcher commit, and run a later ingest or lint. The annotation must survive
byte-for-byte. Next edit AI-managed content, save, and confirm ResearchOS shows
a page conflict and pauses writers touching that page.

Visit all four web areas—Library, Research, Wiki, and Graph. Confirm that Wiki
supports browse/search/wikilinks/backlinks but exposes no edit control; Obsidian
is the sole editing path. On the Graph, confirm its edges correspond only to
explicit wikilinks and nodes navigate to read-only pages.

## 5. Record the outcome

Capture the two source IDs, measured timings and derivative sizes, Git commit
count, cited PDF pages, any extraction weakness observed in the structured
paper, the external-search separation, and the Obsidian conflict/annotation
result. A successful smoke run establishes that the Local MVP's constraints and
evidence trail hold with real Codex behavior even when prose differs from the
deterministic fake.
