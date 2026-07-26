from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
from threading import Thread
import time

from fastapi.testclient import TestClient

from researchos.main import NetworkDisabledSession, Settings, create_app


FAKE_CODEX = Path(__file__).parents[1] / "scripts" / "fake-codex"


def make_client(
    data_dir: Path, *, transient_failures: int = 0, max_pdf_bytes: int = 20 * 1024 * 1024
) -> TestClient:
    return TestClient(
        create_app(
            Settings(
                data_dir=data_dir,
                codex_command=(sys.executable, str(FAKE_CODEX)),
                transient_conversion_failures=transient_failures,
                max_pdf_bytes=max_pdf_bytes,
                run_ingest_service=False,
            )
        )
    )


def text_pdf(*pages: str) -> bytes:
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "",  # Filled after the page-object numbers are known.
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    page_numbers: list[int] = []
    for page in pages:
        page_number = len(objects) + 1
        content_number = page_number + 1
        page_numbers.append(page_number)
        objects.append(
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_number} 0 R >>"
        )
        stream = f"BT /F1 12 Tf 72 720 Td ({page}) Tj ET"
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
    objects[1] = f"<< /Type /Pages /Count {len(pages)} /Kids [{' '.join(f'{n} 0 R' for n in page_numbers)}] >>"
    result = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, contents in enumerate(objects, start=1):
        offsets.append(len(result))
        result.extend(f"{number} 0 obj\n{contents}\nendobj\n".encode())
    xref = len(result)
    result.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    result.extend(b"".join(f"{offset:010} 00000 n \n".encode() for offset in offsets[1:]))
    result.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(result)


def upload(client: TestClient, filename: str, content: bytes) -> str:
    response = client.post(
        "/api/sources", files={"file": (filename, content, "application/pdf")}
    )
    assert response.status_code == 201
    return response.json()["source_id"]


def test_fifo_ingest_creates_immutable_page_addressable_derivatives_and_manifest(
    tmp_path: Path,
) -> None:
    first_pdf = text_pdf("First physical page has enough prose.", "Second physical page has enough prose.")
    second_pdf = text_pdf("A later queued source also has enough prose.")

    with make_client(tmp_path) as client:
        first_id = upload(client, "first.pdf", first_pdf)
        second_id = upload(client, "second.pdf", second_pdf)
        first_run = client.post("/api/ingests/run")
        second_run = client.post("/api/ingests/run")

    assert first_run.status_code == second_run.status_code == 200
    assert first_run.json()["job"]["source_id"] == first_id
    assert second_run.json()["job"]["source_id"] == second_id
    derivative = tmp_path / first_run.json()["job"]["derivative"]
    manifest_path = tmp_path / first_run.json()["job"]["manifest"]
    assert derivative.read_text() == (
        "<!-- pdf-page: 1 -->\nFirst physical page has enough prose.\n\n"
        "<!-- pdf-page: 2 -->\nSecond physical page has enough prose.\n"
    )
    manifest = json.loads(manifest_path.read_text())
    assert manifest["source_sha256"] == first_id == sha256(first_pdf).hexdigest()
    assert manifest["output_sha256"] == sha256(derivative.read_bytes()).hexdigest()
    assert manifest["converter"] == "markitdown==0.1.6"
    assert manifest["dependencies"] == {
        "pdfminer.six": "20251230",
        "pdfplumber": "0.11.9",
        "pypdf": "6.14.2",
    }
    assert manifest["configuration"]["network"] == "disabled"
    assert manifest["configuration"]["plugins"] == "disabled"
    metrics = first_run.json()["job"]["metrics"]
    assert metrics["conversion_duration_ms"] >= 0
    assert metrics["derivative_bytes"] == len(derivative.read_bytes())
    assert metrics["end_to_end_ingest_duration_ms"] >= metrics["conversion_duration_ms"]
    assert manifest["configuration"]["untrusted_pdf"] is True


def test_scanned_and_encrypted_pdfs_do_not_create_derivatives(tmp_path: Path) -> None:
    scanned = text_pdf("").replace(b"() Tj", b"[] TJ")
    encrypted = text_pdf("This text will not be processed because encryption is declared.").replace(
        b"/Type /Catalog", b"/Type /Catalog /Encrypt 9 0 R"
    )

    with make_client(tmp_path) as client:
        scanned_id = upload(client, "scan.pdf", scanned)
        encrypted_id = upload(client, "encrypted.pdf", encrypted)
        scan_run = client.post("/api/ingests/run")
        encrypted_run = client.post("/api/ingests/run")

    assert scan_run.json()["job"]["status"] == "unsupported"
    assert "OCR required" in scan_run.json()["job"]["error"]
    assert encrypted_run.json()["job"]["status"] == "failed"
    assert "Encrypted" in encrypted_run.json()["job"]["error"]
    assert not (tmp_path / "derivatives" / scanned_id).exists()
    assert not (tmp_path / "derivatives" / encrypted_id).exists()


def test_conversion_rejects_oversized_and_partially_missing_extraction(tmp_path: Path) -> None:
    oversized = text_pdf("This source is deliberately larger than the configured limit.")
    partially_missing = text_pdf("Useful first-page prose.", "")

    with make_client(tmp_path, max_pdf_bytes=len(oversized) - 1) as client:
        oversized_id = upload(client, "large.pdf", oversized)
        oversized_run = client.post("/api/ingests/run")
    with make_client(tmp_path) as client:
        missing_id = upload(client, "partial.pdf", partially_missing)
        missing_run = client.post("/api/ingests/run")

    assert oversized_run.json()["job"]["source_id"] == oversized_id
    assert oversized_run.json()["job"]["status"] == "failed"
    assert "size limit" in oversized_run.json()["job"]["error"]
    assert missing_run.json()["job"]["source_id"] == missing_id
    assert missing_run.json()["job"]["status"] == "failed"
    assert "missing text" in missing_run.json()["job"]["error"]


def test_converter_transport_is_blocked_and_interrupted_processing_recovers(tmp_path: Path) -> None:
    try:
        NetworkDisabledSession().request("GET", "https://example.invalid")
    except RuntimeError as error:
        assert str(error) == "Network access is disabled during PDF conversion."
    else:
        raise AssertionError("The converter transport unexpectedly allowed a request.")

    content = text_pdf("A restart must recover the durable processing job.")
    with make_client(tmp_path) as first_app:
        source_id = upload(first_app, "restart.pdf", content)
    jobs_path = tmp_path / "runtime" / "ingest-jobs.json"
    jobs = json.loads(jobs_path.read_text())
    jobs["jobs"][source_id]["status"] = "processing"
    jobs_path.write_text(json.dumps(jobs))

    with make_client(tmp_path) as restarted_app:
        recovered = restarted_app.post("/api/ingests/run")

    assert recovered.json()["job"]["source_id"] == source_id
    assert recovered.json()["job"]["status"] == "completed"


def test_upload_starts_the_serial_worker_without_a_manual_operational_call(
    tmp_path: Path,
) -> None:
    settings = Settings(
        data_dir=tmp_path,
        codex_command=(sys.executable, str(FAKE_CODEX)),
        run_ingest_service=True,
    )
    with TestClient(create_app(settings)) as client:
        source_id = upload(client, "automatic.pdf", text_pdf("The worker starts after upload."))
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            library = client.get("/library")
            if source_id in library.text and "completed" in library.text:
                break
            time.sleep(0.02)
        else:
            raise AssertionError("The scheduled ingest worker did not complete the queued source.")


def test_operational_runs_reject_a_second_concurrent_worker(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path,
        codex_command=(sys.executable, str(FAKE_CODEX)),
        conversion_start_delay_seconds=0.2,
        run_ingest_service=False,
    )
    first_response = []
    with TestClient(create_app(settings)) as client:
        upload(client, "first.pdf", text_pdf("The first source holds the serial worker."))
        upload(client, "second.pdf", text_pdf("The second source remains queued."))
        first = Thread(target=lambda: first_response.append(client.post("/api/ingests/run")))
        first.start()
        time.sleep(0.05)
        overlapping = client.post("/api/ingests/run")
        first.join()
        next_run = client.post("/api/ingests/run")

    assert first_response[0].status_code == 200
    assert overlapping.status_code == 409
    assert next_run.status_code == 200


def test_transient_failure_retries_once_then_manual_retry_uses_same_source(tmp_path: Path) -> None:
    content = text_pdf("The immutable original can be retried safely.")

    with make_client(tmp_path, transient_failures=2) as failing_client:
        source_id = upload(failing_client, "retry.pdf", content)
        failed = failing_client.post("/api/ingests/run")

    assert failed.json()["job"] == {
        "source_id": source_id,
        "status": "failed",
        "attempts": 2,
        "error": "Conversion failed after one automatic retry.",
    }
    with make_client(tmp_path) as restarted_client:
        queued = restarted_client.post(f"/api/ingests/{source_id}/retry")
        recovered = restarted_client.post("/api/ingests/run")

    assert queued.status_code == recovered.status_code == 200
    assert recovered.json()["job"]["status"] == "completed"
    assert (tmp_path / "sources" / f"{source_id}.pdf").read_bytes() == content
