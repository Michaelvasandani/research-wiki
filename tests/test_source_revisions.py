from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient

from researchos.main import Settings, create_app
from test_atomic_paper_ingest import text_pdf


FAKE_CODEX = Path(__file__).parents[1] / "scripts" / "fake-codex"


def make_client(data_dir: Path, *, fake_mode: str = "success") -> TestClient:
    return TestClient(
        create_app(
            Settings(
                data_dir=data_dir,
                codex_command=(sys.executable, str(FAKE_CODEX)),
                codex_environment={"FAKE_CODEX_MODE": fake_mode},
                run_ingest_service=False,
            )
        )
    )


def upload_and_publish(client: TestClient, filename: str, content: bytes) -> str:
    uploaded = client.post(
        "/api/sources", files={"file": (filename, content, "application/pdf")}
    )
    assert uploaded.status_code == 201
    published = client.post("/api/ingests/run")
    assert published.status_code == 200
    assert published.json()["job"]["status"] == "completed"
    return uploaded.json()["source_id"]


def git_head(vault: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(vault), "rev-parse", "HEAD"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()


def test_library_corrects_authoritative_metadata_without_losing_local_extraction(
    tmp_path: Path,
) -> None:
    content = text_pdf("The source documents a research method.")

    with make_client(tmp_path) as client:
        source_id = upload_and_publish(client, "uncertain-filename.pdf", content)
        corrected = client.put(
            f"/api/sources/{source_id}/metadata",
            json={
                "title": "Corrected Research Method",
                "authors": ["Ada Lovelace", "Alan Turing"],
                "year": 2024,
                "doi": "10.5555/corrected.method",
            },
        )
        paper = client.get(f"/wiki/papers/{source_id}")
        library = client.get("/library")
        index = client.get("/wiki/index")
        activity = client.get("/wiki/activity")

    assert corrected.status_code == 200
    assert corrected.json()["metadata"] == {
        "extracted": {
            "title": "uncertain-filename",
            "authors": [],
            "year": None,
            "doi": None,
        },
        "authoritative": {
            "title": "Corrected Research Method",
            "authors": ["Ada Lovelace", "Alan Turing"],
            "year": 2024,
            "doi": "10.5555/corrected.method",
        },
    }
    assert "Corrected Research Method" in paper.text
    assert "Ada Lovelace; Alan Turing" in paper.text
    assert "10.5555/corrected.method" in paper.text
    assert "authoritative metadata" in library.text
    assert "Corrected Research Method" in index.text
    assert "metadata correction" in activity.text


def test_uploading_a_distinct_revision_preserves_the_original_evidence_and_citations(
    tmp_path: Path,
) -> None:
    original = text_pdf("The original method reports a higher outcome.")
    revised = text_pdf("The revised method reports a corrected lower outcome.")

    with make_client(tmp_path) as client:
        original_id = upload_and_publish(client, "paper.pdf", original)
        original_page = (tmp_path / "vault" / "papers" / f"{original_id}.md").read_text()
        original_citation = f"source {original_id} — PDF p. 1"
        uploaded = client.post(
            "/api/sources",
            data={"revision_of": original_id},
            files={"file": ("paper-revised.pdf", revised, "application/pdf")},
        )
        assert uploaded.status_code == 201
        revision_id = uploaded.json()["source_id"]
        assert uploaded.json()["revision_of"] == original_id
        run = client.post("/api/ingests/run")
        original_paper = client.get(f"/wiki/papers/{original_id}")
        revision_paper = client.get(f"/wiki/papers/{revision_id}")
        library = client.get("/library")

    assert revision_id == sha256(revised).hexdigest()
    assert revision_id != original_id
    assert run.json()["job"]["status"] == "completed"
    assert original_citation in (tmp_path / "vault" / "papers" / f"{original_id}.md").read_text()
    assert original_citation in original_page
    assert f'href="/wiki/papers/{revision_id}"' in original_paper.text
    assert f'href="/wiki/papers/{original_id}"' in revision_paper.text
    assert "Revision of" in revision_paper.text
    assert "Revised by" in original_paper.text
    assert original_id in library.text and revision_id in library.text


def test_metadata_or_revision_publication_failure_leaves_the_published_wiki_unchanged(
    tmp_path: Path,
) -> None:
    original = text_pdf("The original source documents a method.")
    revised = text_pdf("The revision documents a different method result.")

    with make_client(tmp_path) as client:
        original_id = upload_and_publish(client, "paper.pdf", original)
    vault = tmp_path / "vault"
    previous_head = git_head(vault)
    previous_contents = {
        path.relative_to(vault): path.read_bytes()
        for path in vault.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }

    with make_client(tmp_path, fake_mode="failure") as client:
        correction = client.put(
            f"/api/sources/{original_id}/metadata",
            json={"title": "", "authors": [], "year": None, "doi": None},
        )
        uploaded = client.post(
            "/api/sources",
            data={"revision_of": original_id},
            files={"file": ("paper-revised.pdf", revised, "application/pdf")},
        )
        assert uploaded.status_code == 201
        failed = client.post("/api/ingests/run")

    assert correction.status_code == 409
    assert failed.json()["job"]["status"] == "failed"
    assert git_head(vault) == previous_head
    assert {
        path.relative_to(vault): path.read_bytes()
        for path in vault.rglob("*")
        if path.is_file() and ".git" not in path.parts
    } == previous_contents


def test_revision_without_bidirectional_paper_links_is_not_published(tmp_path: Path) -> None:
    original = text_pdf("The original source documents a method.")
    revised = text_pdf("The revised source documents a corrected method.")

    with make_client(tmp_path) as client:
        original_id = upload_and_publish(client, "paper.pdf", original)
    vault = tmp_path / "vault"
    previous_head = git_head(vault)
    previous_contents = {
        path.relative_to(vault): path.read_bytes()
        for path in vault.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }

    with make_client(tmp_path, fake_mode="missing-revision-link") as client:
        uploaded = client.post(
            "/api/sources",
            data={"revision_of": original_id},
            files={"file": ("paper-revised.pdf", revised, "application/pdf")},
        )
        assert uploaded.status_code == 201
        failed = client.post("/api/ingests/run")

    assert failed.json()["job"]["status"] == "failed"
    assert git_head(vault) == previous_head
    assert {
        path.relative_to(vault): path.read_bytes()
        for path in vault.rglob("*")
        if path.is_file() and ".git" not in path.parts
    } == previous_contents
