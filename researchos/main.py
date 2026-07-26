from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from hashlib import sha256
from html import escape
import json
from multiprocessing import get_context
import os
from pathlib import Path
from queue import Empty
import re
import shlex
import subprocess
import tempfile
from threading import Event, Lock, Thread
import time
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from markitdown import MarkItDown
from pypdf import PdfReader, PdfWriter


@dataclass(frozen=True)
class Settings:
    """Runtime dependencies configured at the application boundary."""

    data_dir: Path
    codex_command: tuple[str, ...]
    codex_environment: dict[str, str] = field(default_factory=dict)
    max_pdf_bytes: int = 20 * 1024 * 1024
    max_pdf_pages: int = 500
    max_derivative_characters: int = 5 * 1024 * 1024
    conversion_timeout_seconds: int = 30
    conversion_memory_bytes: int = 512 * 1024 * 1024
    conversion_start_delay_seconds: float = 0
    transient_conversion_failures: int = 0
    run_ingest_service: bool = True

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
        self.queue_path = data_dir / "runtime" / "ingest-queue.json"
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

        if source_id not in jobs:
            jobs[source_id] = {"source_id": source_id, "status": "queued"}
            self.enqueue(source_id)
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

    def source(self, source_id: str) -> dict[str, Any] | None:
        return self._read_manifest(self.manifest_path, "sources").get(source_id)

    def job(self, source_id: str) -> dict[str, Any] | None:
        return self._read_manifest(self.job_path, "jobs").get(source_id)

    def jobs(self) -> dict[str, dict[str, Any]]:
        return self._read_manifest(self.job_path, "jobs")

    def save_jobs(self, jobs: dict[str, dict[str, Any]]) -> None:
        self._write_manifest(self.job_path, "jobs", jobs)

    def enqueue(self, source_id: str) -> None:
        queue = self._read_queue()
        if source_id not in queue:
            queue.append(source_id)
            self._write_queue(queue)

    def queued_source_ids(self) -> list[str]:
        return self._read_queue()

    def dequeue(self, source_id: str) -> None:
        self._write_queue([item for item in self._read_queue() if item != source_id])

    def source_path(self, source_id: str) -> Path:
        return self.source_dir / f"{source_id}.pdf"

    def _read_queue(self) -> list[str]:
        if not self.queue_path.exists():
            return []
        data = json.loads(self.queue_path.read_text(encoding="utf-8"))
        source_ids = data.get("source_ids")
        if not isinstance(source_ids, list) or not all(
            isinstance(source_id, str) for source_id in source_ids
        ):
            raise ValueError("The persisted ingest queue is invalid.")
        return source_ids

    def _write_queue(self, source_ids: list[str]) -> None:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.queue_path.parent, delete=False
        ) as temporary_file:
            json.dump({"source_ids": source_ids}, temporary_file)
            temporary_file.write("\n")
            temporary_path = Path(temporary_file.name)
        temporary_path.replace(self.queue_path)

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


class ConversionRejected(Exception):
    """A source cannot safely produce a ResearchOS Markdown derivative."""

    def __init__(self, message: str, *, unsupported: bool = False) -> None:
        super().__init__(message)
        self.unsupported = unsupported


class TransientConversionError(Exception):
    """A local converter failure that is safe to retry once."""


class NetworkDisabledSession:
    """The converter receives no usable HTTP transport for untrusted PDFs."""

    def __init__(self) -> None:
        self.headers: dict[str, str] = {}

    def request(self, *_: Any, **__: Any) -> None:
        raise RuntimeError("Network access is disabled during PDF conversion.")


class PageAddressableConverter:
    """Local, pinned PDF conversion with physical-page provenance."""

    converter_version = "markitdown==0.1.6"
    dependency_versions = {
        "pdfminer.six": "20251230",
        "pdfplumber": "0.11.9",
        "pypdf": "6.14.2",
    }

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def convert(self, source_id: str, content: bytes) -> tuple[str, dict[str, Any]]:
        if len(content) > self.settings.max_pdf_bytes:
            raise ConversionRejected("PDF exceeds the conversion size limit.")
        if b"/Encrypt" in content:
            raise ConversionRejected("Encrypted PDFs cannot be converted safely.")

        try:
            reader = PdfReader(BytesIO(content), strict=True)
            if reader.is_encrypted:
                raise ConversionRejected("Encrypted PDFs cannot be converted safely.")
            if not reader.pages:
                raise ConversionRejected("PDF has no physical pages.")
            if len(reader.pages) > self.settings.max_pdf_pages:
                raise ConversionRejected("PDF exceeds the conversion page limit.")
            converter = MarkItDown(
                enable_plugins=False, requests_session=NetworkDisabledSession()
            )
            page_text = []
            for page in reader.pages:
                page_pdf = BytesIO()
                page_writer = PdfWriter()
                page_writer.add_page(page)
                page_writer.write(page_pdf)
                # Each MarkItDown invocation receives exactly one physical page.  This
                # preserves its Markdown output while giving ResearchOS a reliable
                # place to inject the page marker its built-in PDF converter lacks.
                converted = converter.convert_stream(
                    BytesIO(page_pdf.getvalue()), file_extension=".pdf"
                )
                page_text.append(converted.text_content or "")
        except ConversionRejected:
            raise
        except (OSError, TimeoutError) as error:
            raise TransientConversionError("Local PDF converter was temporarily unavailable.") from error
        except Exception as error:
            raise ConversionRejected("Malformed PDF could not be converted safely.") from error

        nonempty_pages = [text for text in page_text if text.strip()]
        if not nonempty_pages:
            raise ConversionRejected(
                "OCR required: the PDF has no extractable text.", unsupported=True
            )
        if len(nonempty_pages) != len(page_text):
            raise ConversionRejected("PDF extraction is missing text from one or more pages.")
        derivative = "\n\n".join(
            f"<!-- pdf-page: {number} -->\n{text.strip()}"
            for number, text in enumerate(page_text, start=1)
        ) + "\n"
        if len(derivative) > self.settings.max_derivative_characters:
            raise ConversionRejected("PDF extraction exceeds the derivative size limit.")
        # Control characters are a strong, format-independent signal that the parser
        # did not produce usable prose.  The paper itself is never executed or treated
        # as workflow instructions.
        controls = sum(ord(character) < 32 and character not in "\n\t\r" for character in derivative)
        if controls or len("".join(nonempty_pages).strip()) < 8:
            raise ConversionRejected("PDF extraction is too poor to publish safely.")
        configuration = {
            "input": "in-memory local PDF bytes",
            "plugins": "disabled",
            "network": "disabled",
            "resource_limits": {
                "max_pdf_bytes": self.settings.max_pdf_bytes,
                "max_pdf_pages": self.settings.max_pdf_pages,
                "max_derivative_characters": self.settings.max_derivative_characters,
                "timeout_seconds": self.settings.conversion_timeout_seconds,
                "memory_bytes": self.settings.conversion_memory_bytes,
            },
            "page_marker": "<!-- pdf-page: N -->",
            "untrusted_pdf": True,
        }
        return derivative, {
            "source_id": source_id,
            "source_sha256": sha256(content).hexdigest(),
            "converter": self.converter_version,
            "dependencies": self.dependency_versions,
            "configuration": configuration,
        }


def convert_with_resource_limits(
    settings: Settings, source_id: str, content: bytes, result_queue: Any
) -> None:
    """Run untrusted parser code in a disposable, resource-capped process."""

    try:
        import resource

        resource.setrlimit(
            resource.RLIMIT_CPU,
            (settings.conversion_timeout_seconds, settings.conversion_timeout_seconds + 1),
        )
        resource.setrlimit(
            resource.RLIMIT_AS,
            (settings.conversion_memory_bytes, settings.conversion_memory_bytes),
        )
    except (ImportError, ValueError, OSError):
        # The Local MVP Docker target is POSIX.  The wall-clock limit in the parent
        # below remains enforced when an OS cannot expose these extra limits.
        pass
    try:
        if settings.conversion_start_delay_seconds:
            time.sleep(settings.conversion_start_delay_seconds)
        result_queue.put(("completed", PageAddressableConverter(settings).convert(source_id, content)))
    except TransientConversionError as error:
        result_queue.put(("transient", str(error)))
    except ConversionRejected as error:
        result_queue.put(("rejected", (str(error), error.unsupported)))
    except Exception:
        result_queue.put(("transient", "Local PDF converter terminated unexpectedly."))


class IngestWorker:
    """Durable FIFO worker for the conversion stage of an ingest."""

    derivative_version = (
        "markitdown-0.1.6-pdfminer-20251230-pdfplumber-0.11.9-pypdf-6.14.2"
    )

    def __init__(self, sources: SourceCatalog, settings: Settings) -> None:
        self.sources = sources
        self.settings = settings
        self.lock = Lock()

    def run_next(self) -> dict[str, Any] | None:
        if not self.lock.acquire(blocking=False):
            raise RuntimeError("An ingest is already processing.")
        try:
            jobs = self.sources.jobs()
            recovered = False
            for source_id in self.sources.queued_source_ids():
                job = jobs.get(source_id)
                if job and job.get("status") == "processing":
                    job["status"] = "queued"
                    recovered = True
            if recovered:
                self.sources.save_jobs(jobs)
            next_source_id = next(
                (
                    source_id
                    for source_id in self.sources.queued_source_ids()
                    if jobs.get(source_id, {}).get("status") == "queued"
                ),
                None,
            )
            if next_source_id is None:
                return None
            return self._process(next_source_id, jobs)
        finally:
            self.lock.release()

    def retry(self, source_id: str) -> dict[str, Any]:
        jobs = self.sources.jobs()
        job = jobs.get(source_id)
        if job is None:
            raise KeyError(source_id)
        if job["status"] not in {"failed", "unsupported"}:
            raise ValueError("Only failed or unsupported ingests can be retried.")
        job.update({"source_id": source_id, "status": "queued", "attempts": 0})
        job.pop("error", None)
        self.sources.save_jobs(jobs)
        self.sources.enqueue(source_id)
        return job

    def _process(self, source_id: str, jobs: dict[str, dict[str, Any]]) -> dict[str, Any]:
        job = jobs[source_id]
        job["status"] = "processing"
        self.sources.save_jobs(jobs)
        attempts = int(job.get("attempts", 0))
        while True:
            attempts += 1
            job["attempts"] = attempts
            try:
                if attempts <= self.settings.transient_conversion_failures:
                    raise OSError("Transient local converter failure.")
                derivative, manifest = self._convert_with_limits(
                    source_id, self.sources.source_path(source_id).read_bytes()
                )
                manifest["output_sha256"] = sha256(derivative.encode()).hexdigest()
                manifest["converted_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                manifest["derivative_version"] = self.derivative_version
                markdown_path, manifest_path = self._store_derivative_pair(
                    source_id, derivative, manifest
                )
                job.update({
                    "source_id": source_id,
                    "status": "completed",
                    "attempts": attempts,
                    "derivative": str(markdown_path.relative_to(self.sources.source_dir.parent)),
                    "manifest": str(manifest_path.relative_to(self.sources.source_dir.parent)),
                })
                job.pop("error", None)
                self.sources.save_jobs(jobs)
                self.sources.dequeue(source_id)
                return job
            except ConversionRejected as error:
                job.update({
                    "source_id": source_id,
                    "status": "unsupported" if error.unsupported else "failed",
                    "attempts": attempts,
                    "error": str(error),
                })
                self.sources.save_jobs(jobs)
                self.sources.dequeue(source_id)
                return job
            except TransientConversionError:
                if attempts < 2:
                    continue
                job.update({
                    "source_id": source_id,
                    "status": "failed",
                    "attempts": attempts,
                    "error": "Conversion failed after one automatic retry.",
                })
                self.sources.save_jobs(jobs)
                self.sources.dequeue(source_id)
                return job
            except Exception as error:
                if attempts < 2:
                    continue
                job.update({
                    "source_id": source_id,
                    "status": "failed",
                    "attempts": attempts,
                    "error": "Conversion failed after one automatic retry.",
                })
                self.sources.save_jobs(jobs)
                self.sources.dequeue(source_id)
                return job

    def _store_derivative_pair(
        self, source_id: str, derivative: str, manifest: dict[str, Any]
    ) -> tuple[Path, Path]:
        source_dir = self.sources.source_dir.parent / "derivatives" / source_id
        source_dir.mkdir(parents=True, exist_ok=True)
        version_dir = source_dir / self.derivative_version
        markdown_path = version_dir / "derivative.md"
        manifest_path = version_dir / "manifest.json"
        if version_dir.exists():
            if markdown_path.exists() and manifest_path.exists():
                return markdown_path, manifest_path
            raise ConversionRejected("Existing derivative version is incomplete; manual recovery is required.")
        temporary_dir = Path(tempfile.mkdtemp(prefix=".pending-", dir=source_dir))
        try:
            (temporary_dir / "derivative.md").write_text(derivative, encoding="utf-8")
            (temporary_dir / "manifest.json").write_text(
                json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8"
            )
            temporary_dir.replace(version_dir)
        except Exception:
            if temporary_dir.exists():
                for artifact in temporary_dir.iterdir():
                    artifact.unlink()
                temporary_dir.rmdir()
            raise
        return markdown_path, manifest_path

    def _convert_with_limits(
        self, source_id: str, content: bytes
    ) -> tuple[str, dict[str, Any]]:
        context = get_context("fork")
        result_queue = context.Queue(maxsize=1)
        process = context.Process(
            target=convert_with_resource_limits,
            args=(self.settings, source_id, content, result_queue),
        )
        process.start()
        try:
            outcome, payload = result_queue.get(
                timeout=self.settings.conversion_timeout_seconds
            )
        except Empty as error:
            raise TransientConversionError("PDF conversion exceeded the time limit.") from error
        finally:
            if process.is_alive():
                process.terminate()
            process.join()
            result_queue.close()
        if outcome == "completed":
            derivative, manifest = payload
            return derivative, manifest
        if outcome == "rejected":
            message, unsupported = payload
            raise ConversionRejected(message, unsupported=unsupported)
        raise TransientConversionError(str(payload))


class IngestWorkerService:
    """Keeps the single durable worker moving queued ingests after upload."""

    def __init__(self, worker: IngestWorker) -> None:
        self.worker = worker
        self.wake = Event()
        self.stopping = Event()
        self.thread = Thread(target=self._run, daemon=True, name="researchos-ingest")

    def start(self) -> None:
        self.thread.start()
        self.wake.set()  # Recover queued work left by an application restart.

    def stop(self) -> None:
        self.stopping.set()
        self.wake.set()
        self.thread.join(timeout=1)

    def schedule(self) -> None:
        self.wake.set()

    def _run(self) -> None:
        while not self.stopping.is_set():
            self.wake.wait()
            self.wake.clear()
            # A tiny debounce lets the upload response expose its queued job before
            # the asynchronous worker claims it, while batching back-to-back uploads.
            if self.stopping.wait(0.05):
                return
            while not self.stopping.is_set():
                try:
                    job = self.worker.run_next()
                except RuntimeError:
                    break
                if job is None:
                    break


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
    ingest_worker = IngestWorker(sources, settings)
    ingest_service = IngestWorkerService(ingest_worker)
    app = FastAPI(title="ResearchOS Local MVP")

    @app.on_event("startup")
    def start_ingest_service() -> None:
        if settings.run_ingest_service:
            ingest_service.start()

    @app.on_event("shutdown")
    def stop_ingest_service() -> None:
        if settings.run_ingest_service:
            ingest_service.stop()

    @app.get("/", response_class=HTMLResponse)
    def home() -> HTMLResponse:
        return page(
            "Local research workspace",
            "<p>ResearchOS is running locally. Choose an area to begin.</p>",
        )

    @app.get("/library", response_class=HTMLResponse)
    def library() -> HTMLResponse:
        def render_source(source: dict[str, Any]) -> str:
            job = source["job"]
            error = f" — {escape(job['error'])}" if job.get("error") else ""
            retry = ""
            if job["status"] in {"failed", "unsupported"}:
                retry = (
                    f'<form action="/library/ingests/{escape(source["source_id"])}/retry" '
                    'method="post"><button>Retry ingest</button></form>'
                )
            return (
                f"<li><code>{escape(source['source_id'])}</code> — "
                f"{escape(source['metadata']['extracted']['title'])} "
                f"(<strong>{escape(job['status'])}</strong>){error}{retry}</li>"
            )

        entries = "".join(render_source(source) for source in sources.sources())
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
        if settings.run_ingest_service:
            ingest_service.schedule()
        return RedirectResponse("/library", status_code=303)

    @app.post("/api/sources", status_code=status.HTTP_201_CREATED)
    async def upload_source(file: UploadFile = File()) -> dict[str, Any]:
        filename = file.filename or "uploaded.pdf"
        content = await file.read()
        validate_pdf_upload(filename, content)
        result = sources.upload(filename, content)
        if settings.run_ingest_service:
            ingest_service.schedule()
        return result

    @app.post("/api/ingests/run")
    def run_next_ingest() -> dict[str, Any]:
        try:
            job = ingest_worker.run_next()
        except RuntimeError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return {"job": job}

    @app.post("/api/ingests/{source_id}/retry")
    def retry_ingest(source_id: str) -> dict[str, Any]:
        try:
            job = ingest_worker.retry(source_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Unknown source.") from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if settings.run_ingest_service:
            ingest_service.schedule()
        return {"job": job}

    @app.post("/library/ingests/{source_id}/retry")
    def retry_ingest_from_library(source_id: str) -> RedirectResponse:
        try:
            ingest_worker.retry(source_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Unknown source.") from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if settings.run_ingest_service:
            ingest_service.schedule()
        return RedirectResponse("/library", status_code=303)

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
