from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse


@dataclass(frozen=True)
class Settings:
    """Runtime dependencies configured at the application boundary."""

    data_dir: Path
    codex_command: tuple[str, ...]
    codex_environment: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_environment(cls) -> "Settings":
        command = tuple(shlex.split(os.environ.get("CODEX_COMMAND", "codex")))
        if not command:
            raise ValueError("CODEX_COMMAND must name a Codex executable.")
        return cls(
            data_dir=Path(os.environ.get("RESEARCHOS_DATA_DIR", "data")),
            codex_command=command,
        )


class FileState:
    """Small, durable state store for the single Local MVP research thread."""

    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "runtime" / "research-thread.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def messages(self) -> list[str]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        messages = data.get("messages", [])
        if not isinstance(messages, list) or not all(
            isinstance(message, str) for message in messages
        ):
            raise ValueError("The persisted research thread is invalid.")
        return messages

    def append_message(self, message: str) -> None:
        messages = self.messages()
        messages.append(message)
        self._write({"messages": messages})

    def _write(self, content: dict[str, Any]) -> None:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.path.parent, delete=False
        ) as temporary_file:
            json.dump(content, temporary_file)
            temporary_file.write("\n")
            temporary_path = Path(temporary_file.name)
        temporary_path.replace(self.path)


class SourceCatalog:
    """Filesystem-backed source storage and durable ingest queue state."""

    def __init__(self, data_dir: Path) -> None:
        self.source_dir = data_dir / "sources"
        self.manifest_path = self.source_dir / "manifest.json"
        self.job_path = data_dir / "runtime" / "ingest-jobs.json"
        self.source_dir.mkdir(parents=True, exist_ok=True)
        self.job_path.parent.mkdir(parents=True, exist_ok=True)

    def upload(self, filename: str, content: bytes) -> dict[str, Any]:
        source_id = sha256(content).hexdigest()
        sources = self._read_manifest(self.manifest_path, "sources")
        jobs = self._read_manifest(self.job_path, "jobs")
        source = sources.get(source_id)
        if source is None:
            source = {
                "source_id": source_id,
                "filenames": [filename],
                "metadata": self._extract_metadata(filename, content),
            }
            sources[source_id] = source
            (self.source_dir / f"{source_id}.pdf").write_bytes(content)
            self._write_manifest(self.manifest_path, "sources", sources)
        elif filename not in source["filenames"]:
            source["filenames"].append(filename)
            self._write_manifest(self.manifest_path, "sources", sources)

        jobs.setdefault(source_id, {"source_id": source_id, "status": "queued"})
        self._write_manifest(self.job_path, "jobs", jobs)
        return {
            "source_id": source_id,
            "filename": filename,
            "job": jobs[source_id],
            "metadata": source["metadata"],
        }

    def sources(self) -> list[dict[str, Any]]:
        sources = self._read_manifest(self.manifest_path, "sources")
        jobs = self._read_manifest(self.job_path, "jobs")
        return [
            {**source, "job": jobs[source_id]}
            for source_id, source in sorted(sources.items())
            if source_id in jobs
        ]

    @staticmethod
    def _read_manifest(path: Path, key: str) -> dict[str, dict[str, Any]]:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        entries = data.get(key)
        if not isinstance(entries, dict):
            raise ValueError(f"The persisted {key} manifest is invalid.")
        return entries

    @staticmethod
    def _extract_metadata(filename: str, content: bytes) -> dict[str, Any]:
        text = content.decode("latin-1", errors="ignore")

        def pdf_value(name: str) -> str | None:
            match = re.search(rf"/{name}\s*\(([^)]*)\)", text)
            return match.group(1).strip() if match else None

        title = pdf_value("Title") or Path(filename).stem
        author_text = pdf_value("Author")
        authors = (
            [author.strip() for author in author_text.split(";") if author.strip()]
            if author_text
            else []
        )
        date = pdf_value("CreationDate")
        year_match = re.search(r"(?:D:)?([12]\d{3})", date or "")
        doi_match = re.search(
            r"\b10\.\d{4,9}/[-._;()/:a-z0-9]+", text, flags=re.IGNORECASE
        )
        return {
            "extracted": {
                "title": title,
                "authors": authors,
                "year": int(year_match.group(1)) if year_match else None,
                "doi": doi_match.group(0) if doi_match else None,
            },
            "authoritative": None,
        }

    @staticmethod
    def _write_manifest(
        path: Path, key: str, entries: dict[str, dict[str, Any]]
    ) -> None:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as temporary_file:
            json.dump({key: entries}, temporary_file, sort_keys=True)
            temporary_file.write("\n")
            temporary_path = Path(temporary_file.name)
        temporary_path.replace(path)


class CodexProtocolError(Exception):
    pass


class CodexWorker:
    """Production-shaped subprocess boundary for the Codex CLI worker."""

    def __init__(self, settings: Settings) -> None:
        self.command = settings.codex_command
        self.environment = settings.codex_environment

    def probe(self) -> dict[str, Any]:
        environment = os.environ.copy()
        environment.update(self.environment)
        try:
            result = subprocess.run(
                [*self.command, "probe"],
                capture_output=True,
                check=False,
                env=environment,
                text=True,
                timeout=15,
            )
        except FileNotFoundError as error:
            raise CodexProtocolError("Codex executable was not found.") from error
        except subprocess.TimeoutExpired as error:
            raise CodexProtocolError("Codex did not respond before the timeout.") from error

        if result.returncode:
            raise CodexProtocolError(f"Codex exited with status {result.returncode}.")

        events: list[dict[str, str]] = []
        output: str | None = None
        for line in result.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise CodexProtocolError("Codex returned malformed protocol output.") from error
            if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                raise CodexProtocolError("Codex returned malformed protocol output.")
            if event["type"] == "progress" and isinstance(event.get("message"), str):
                events.append({"type": "progress", "message": event["message"]})
            elif event["type"] == "result" and isinstance(event.get("output"), str):
                output = event["output"]
            else:
                raise CodexProtocolError("Codex returned malformed protocol output.")
        if output is None:
            raise CodexProtocolError("Codex returned malformed protocol output.")
        return {"events": events, "output": output}


NAVIGATION = (
    ("Library", "/library"),
    ("Research", "/research"),
    ("Wiki", "/wiki"),
    ("Graph", "/graph"),
)


def validate_pdf_upload(filename: str, content: bytes) -> None:
    if (
        not filename.lower().endswith(".pdf")
        or not re.match(br"%PDF-\d\.\d(?:\s|$)", content)
        or not re.search(br"\b\d+\s+\d+\s+obj\b", content)
        or b"endobj" not in content
        or not content.rstrip().endswith(b"%%EOF")
    ):
        raise HTTPException(
            status_code=422, detail="Upload a valid PDF file to the Library."
        )


def page(title: str, content: str) -> HTMLResponse:
    navigation = "".join(
        f'<a href="{href}">{label}</a>' for label, href in NAVIGATION
    )
    return HTMLResponse(
        f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{escape(title)} · ResearchOS</title>
<style>body{{font-family:system-ui,sans-serif;margin:0;color:#17212b;background:#f7f8fa}}header{{background:#132b3a;color:#fff;padding:1rem 2rem}}nav a{{color:#dff4f0;margin-right:1rem}}main{{max-width:56rem;margin:2rem auto;background:#fff;padding:2rem;border-radius:.5rem;box-shadow:0 1px 4px #ccd}}</style>
</head><body><header><strong>ResearchOS</strong><nav aria-label="Primary">{navigation}</nav></header><main><h1>{escape(title)}</h1>{content}</main></body></html>"""
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_environment()
    state = FileState(settings.data_dir)
    sources = SourceCatalog(settings.data_dir)
    worker = CodexWorker(settings)
    app = FastAPI(title="ResearchOS Local MVP")

    @app.get("/", response_class=HTMLResponse)
    def home() -> HTMLResponse:
        return page(
            "Local research workspace",
            "<p>ResearchOS is running locally. Choose an area to begin.</p>",
        )

    @app.get("/library", response_class=HTMLResponse)
    def library() -> HTMLResponse:
        entries = "".join(
            f"<li><code>{escape(source['source_id'])}</code> — "
            f"{escape(source['metadata']['extracted']['title'])} "
            f"(<strong>{escape(source['job']['status'])}</strong>)</li>"
            for source in sources.sources()
        )
        library_entries = f"<ul>{entries}</ul>" if entries else "<p>No uploaded sources.</p>"
        return page(
            "Library",
            f"""{library_entries}<form action="/library/sources" method="post" enctype="multipart/form-data">
<label>PDF <input name="file" type="file" accept="application/pdf,.pdf" required></label>
<button>Upload PDF</button></form>""",
        )

    @app.post("/library/sources")
    async def upload_from_library(file: UploadFile = File()) -> RedirectResponse:
        filename = file.filename or "uploaded.pdf"
        content = await file.read()
        validate_pdf_upload(filename, content)
        sources.upload(filename, content)
        return RedirectResponse("/library", status_code=303)

    @app.post("/api/sources", status_code=status.HTTP_201_CREATED)
    async def upload_source(file: UploadFile = File()) -> dict[str, Any]:
        filename = file.filename or "uploaded.pdf"
        content = await file.read()
        validate_pdf_upload(filename, content)
        return sources.upload(filename, content)

    @app.get("/research", response_class=HTMLResponse)
    def research() -> HTMLResponse:
        messages = "".join(f"<li>{escape(message)}</li>" for message in state.messages())
        transcript = f"<ul>{messages}</ul>" if messages else "<p>No saved research messages.</p>"
        return page(
            "Research",
            f"""<p>The single persisted research thread is ready.</p>{transcript}
<form action="/research/messages" method="post"><label>Message <input name="message" required></label><button>Save message</button></form>""",
        )

    @app.post("/research/messages")
    def save_research_message(message: str = Form()) -> RedirectResponse:
        clean_message = message.strip()
        if not clean_message:
            raise HTTPException(status_code=422, detail="A research message is required.")
        state.append_message(clean_message)
        return RedirectResponse("/research", status_code=303)

    @app.get("/wiki", response_class=HTMLResponse)
    def wiki() -> HTMLResponse:
        return page("Wiki", "<p>The read-only research wiki will appear here.</p>")

    @app.get("/graph", response_class=HTMLResponse)
    def graph() -> HTMLResponse:
        return page("Graph", "<p>The explicit knowledge graph will appear here.</p>")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "storage": "file"}

    @app.get("/api/codex/probe")
    def codex_probe() -> dict[str, Any]:
        try:
            return worker.probe()
        except CodexProtocolError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error

    return app


app = create_app()
