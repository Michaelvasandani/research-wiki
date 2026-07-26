from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys

from fastapi.testclient import TestClient

from researchos.main import Settings, create_app


FAKE_CODEX = Path(__file__).parents[1] / "scripts" / "fake-codex"


def make_client(data_dir: Path) -> TestClient:
    settings = Settings(
        data_dir=data_dir,
        codex_command=(sys.executable, str(FAKE_CODEX)),
    )
    return TestClient(create_app(settings))


def pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"


def test_uploading_a_pdf_preserves_its_bytes_and_queues_an_ingest(tmp_path: Path) -> None:
    content = pdf_bytes()

    with make_client(tmp_path) as client:
        response = client.post(
            "/api/sources",
            files={"file": ("paper.pdf", content, "application/pdf")},
        )

    source_id = sha256(content).hexdigest()
    assert response.status_code == 201
    assert response.json() == {
        "source_id": source_id,
        "filename": "paper.pdf",
        "job": {"source_id": source_id, "status": "queued"},
        "metadata": {
            "extracted": {
                "title": "paper",
                "authors": [],
                "year": None,
                "doi": None,
            },
            "authoritative": None,
        },
    }
    assert (tmp_path / "sources" / f"{source_id}.pdf").read_bytes() == content
    assert json.loads((tmp_path / "sources" / "manifest.json").read_text()) == {
        "sources": {
            source_id: {
                "source_id": source_id,
                "filenames": ["paper.pdf"],
                "metadata": response.json()["metadata"],
            }
        }
    }
    assert json.loads((tmp_path / "runtime" / "ingest-jobs.json").read_text()) == {
        "jobs": {source_id: {"source_id": source_id, "status": "queued"}}
    }


def test_library_shows_a_queued_ingest_after_an_application_restart(tmp_path: Path) -> None:
    content = pdf_bytes()
    source_id = sha256(content).hexdigest()

    with make_client(tmp_path) as first_app:
        first_app.post(
            "/api/sources",
            files={"file": ("paper.pdf", content, "application/pdf")},
        )

    with make_client(tmp_path) as restarted_app:
        library = restarted_app.get("/library")

    assert library.status_code == 200
    assert source_id in library.text
    assert "queued" in library.text


def test_upload_extracts_available_bibliographic_metadata_locally(tmp_path: Path) -> None:
    content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Title (A Practical Method) /Author (Ada Lovelace; Alan Turing) "
        b"/CreationDate (D:20240315000000) >>\nendobj\n"
        b"10.5555/researchos.example\n%%EOF\n"
    )

    with make_client(tmp_path) as client:
        response = client.post(
            "/api/sources",
            files={"file": ("opaque-name.pdf", content, "application/pdf")},
        )

    assert response.status_code == 201
    assert response.json()["metadata"] == {
        "extracted": {
            "title": "A Practical Method",
            "authors": ["Ada Lovelace", "Alan Turing"],
            "year": 2024,
            "doi": "10.5555/researchos.example",
        },
        "authoritative": None,
    }


def test_uploading_identical_bytes_reuses_the_existing_source_identity(tmp_path: Path) -> None:
    content = pdf_bytes()

    with make_client(tmp_path) as client:
        first = client.post(
            "/api/sources",
            files={"file": ("first-name.pdf", content, "application/pdf")},
        )
        duplicate = client.post(
            "/api/sources",
            files={"file": ("second-name.pdf", content, "application/pdf")},
        )

    source_id = sha256(content).hexdigest()
    assert duplicate.status_code == 201
    assert first.json()["source_id"] == duplicate.json()["source_id"] == source_id
    manifest = json.loads((tmp_path / "sources" / "manifest.json").read_text())
    assert list(manifest["sources"]) == [source_id]
    assert manifest["sources"][source_id]["filenames"] == [
        "first-name.pdf",
        "second-name.pdf",
    ]


def test_uploading_different_pdf_bytes_with_the_same_filename_keeps_both_sources(
    tmp_path: Path,
) -> None:
    first_content = pdf_bytes()
    second_content = b"%PDF-1.4\n2 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"

    with make_client(tmp_path) as client:
        first = client.post(
            "/api/sources",
            files={"file": ("paper.pdf", first_content, "application/pdf")},
        )
        second = client.post(
            "/api/sources",
            files={"file": ("paper.pdf", second_content, "application/pdf")},
        )

    assert first.status_code == second.status_code == 201
    assert first.json()["source_id"] != second.json()["source_id"]
    assert len(json.loads((tmp_path / "sources" / "manifest.json").read_text())["sources"]) == 2


def test_library_rejects_non_pdf_and_clearly_invalid_uploads(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        non_pdf = client.post(
            "/api/sources",
            files={"file": ("notes.txt", b"ordinary text", "text/plain")},
        )
        invalid_pdf = client.post(
            "/api/sources",
            files={"file": ("broken.pdf", b"%PDF-1.4\ntruncated", "application/pdf")},
        )

    assert non_pdf.status_code == invalid_pdf.status_code == 422
    assert non_pdf.json() == invalid_pdf.json() == {
        "detail": "Upload a valid PDF file to the Library."
    }
    assert not (tmp_path / "sources" / "manifest.json").exists()
    assert not (tmp_path / "runtime" / "ingest-jobs.json").exists()


def test_library_form_returns_the_researcher_to_the_queued_source(tmp_path: Path) -> None:
    content = pdf_bytes()
    source_id = sha256(content).hexdigest()

    with make_client(tmp_path) as client:
        response = client.post(
            "/library/sources",
            files={"file": ("paper.pdf", content, "application/pdf")},
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert source_id in response.text
    assert "queued" in response.text


def test_library_rejects_pdf_shaped_arbitrary_bytes(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/sources",
            files={
                "file": (
                    "not-really-a-pdf.pdf",
                    b"%PDF-not-a-real-document\n%%EOF\n",
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "Upload a valid PDF file to the Library."}
