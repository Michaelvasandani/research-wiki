from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient

from researchos.main import (
    AtomicWikiPublisher,
    PublicationRejected,
    Settings,
    SourceCatalog,
    create_app,
)
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


def publish(client: TestClient, filename: str, text: str) -> str:
    uploaded = client.post(
        "/api/sources", files={"file": (filename, text_pdf(text), "application/pdf")}
    )
    assert uploaded.status_code == 201
    completed = client.post("/api/ingests/run")
    assert completed.status_code == 200
    assert completed.json()["job"]["status"] == "completed"
    return uploaded.json()["source_id"]


def vault_files(vault: Path) -> dict[Path, bytes]:
    return {
        path.relative_to(vault): path.read_bytes()
        for path in vault.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }


def test_withdrawing_a_completed_source_preserves_evidence_and_marks_affected_wiki(
    tmp_path: Path,
) -> None:
    with make_client(tmp_path) as client:
        source_id = publish(client, "method.pdf", "The method has a higher outcome.")
        before = client.get(f"/wiki/papers/{source_id}")
        withdrawn = client.post(f"/api/sources/{source_id}/withdraw")
        library = client.get("/library")
        paper = client.get(f"/wiki/papers/{source_id}")
        topic = client.get("/wiki/topics/research-methods")
        index = client.get("/wiki/index")
        activity = client.get("/wiki/activity")

    assert withdrawn.status_code == 200
    assert withdrawn.json()["withdrawal"] == {"status": "withdrawn"}
    assert (tmp_path / "sources" / f"{source_id}.pdf").exists()
    assert list((tmp_path / "derivatives" / source_id).rglob("derivative.md"))
    assert list((tmp_path / "derivatives" / source_id).rglob("manifest.json"))
    assert "withdrawn" in library.text
    assert "Withdrawn evidence" in paper.text and "Withdrawn evidence" in topic.text
    assert source_id in before.text and f"Source identity <code>{source_id}</code>" in paper.text
    assert "PDF page 1" in paper.text
    assert "withdrawn" in index.text and "withdrawal" in activity.text

    with make_client(tmp_path) as restarted:
        persisted = restarted.get("/library")
    assert "withdrawn" in persisted.text


def test_withdrawn_evidence_is_excluded_from_future_research_with_a_notice(
    tmp_path: Path,
) -> None:
    with make_client(tmp_path) as client:
        withdrawn_source = publish(client, "withdrawn.pdf", "The method has a higher outcome.")
        active_source = publish(client, "active.pdf", "The method has a lower outcome.")
        assert client.post(f"/api/sources/{withdrawn_source}/withdraw").status_code == 200
        response = client.post(
            "/api/research/messages", json={"message": "Compare the lab methods."}
        )

    assert response.status_code == 200
    assert active_source in response.text
    assert "Withdrawn material exists" in response.text
    assert withdrawn_source in response.text
    assert f"source {withdrawn_source} — /wiki/papers/{withdrawn_source}" not in response.text


def test_research_worker_receives_no_withdrawn_page_content(tmp_path: Path) -> None:
    with make_client(tmp_path, fake_mode="withdrawn-hidden") as client:
        source_id = publish(client, "withdrawn.pdf", "The method has a higher outcome.")
        assert client.post(f"/api/sources/{source_id}/withdraw").status_code == 200
        response = client.post(
            "/api/research/messages", json={"message": "What does the lab show?"}
        )

    assert response.status_code == 200
    assert "No published lab evidence is available yet." in response.text


def test_research_worker_receives_no_prior_chat_answer_using_withdrawn_evidence(
    tmp_path: Path,
) -> None:
    with make_client(tmp_path, fake_mode="withdrawn-hidden") as client:
        source_id = publish(client, "withdrawn.pdf", "The method has a higher outcome.")
        before_withdrawal = client.post(
            "/api/research/messages", json={"message": "What does the lab show?"}
        )
        assert source_id in before_withdrawal.text
        assert client.post(f"/api/sources/{source_id}/withdraw").status_code == 200
        response = client.post(
            "/api/research/messages", json={"message": "What does the lab show now?"}
        )

    assert response.status_code == 200
    assert "No published lab evidence is available yet." in response.text


def test_restart_recovers_a_published_withdrawal_left_pending_by_state_write_failure(
    tmp_path: Path,
) -> None:
    with make_client(tmp_path) as client, patch.object(
        SourceCatalog,
        "complete_withdrawal",
        side_effect=OSError("controlled state write failure"),
    ):
        source_id = publish(client, "method.pdf", "The method has a higher outcome.")
        failed = client.post(f"/api/sources/{source_id}/withdraw")
        pending_response = client.post(
            "/api/research/messages", json={"message": "What does the lab show?"}
        )

    assert failed.status_code == 409
    assert "No published lab evidence is available yet." in pending_response.text
    assert "Withdrawn evidence" in (tmp_path / "vault" / "papers" / f"{source_id}.md").read_text()
    with make_client(tmp_path) as restarted:
        library = restarted.get("/library")
        response = restarted.post(
            "/api/research/messages", json={"message": "What does the lab show?"}
        )
    assert "withdrawn" in library.text
    assert "No published lab evidence is available yet." in response.text


def test_withdrawal_publication_failure_keeps_the_live_wiki_and_source_active(
    tmp_path: Path,
) -> None:
    with make_client(tmp_path) as client:
        source_id = publish(client, "method.pdf", "The method has a higher outcome.")
    vault = tmp_path / "vault"
    before_head = subprocess.run(
        ["git", "-C", str(vault), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    before_files = vault_files(vault)

    with make_client(tmp_path) as client, patch.object(
        AtomicWikiPublisher,
        "_commit",
        side_effect=PublicationRejected("controlled failure"),
    ):
        failed = client.post(f"/api/sources/{source_id}/withdraw")
        library = client.get("/library")

    assert failed.status_code == 409
    assert subprocess.run(
        ["git", "-C", str(vault), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip() == before_head
    assert vault_files(vault) == before_files
    assert "withdrawn" not in library.text


def test_only_a_pre_ingest_upload_can_be_removed(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        uploaded = client.post(
            "/api/sources",
            files={"file": ("queued.pdf", text_pdf("Queued source."), "application/pdf")},
        )
        source_id = uploaded.json()["source_id"]
        removed = client.delete(f"/api/sources/{source_id}")
        missing = client.get("/library")

        completed_source = publish(client, "completed.pdf", "The method has a higher outcome.")
        rejected = client.delete(f"/api/sources/{completed_source}")

    assert removed.status_code == 204
    assert not (tmp_path / "sources" / f"{source_id}.pdf").exists()
    assert source_id not in missing.text
    assert rejected.status_code == 409
    assert (tmp_path / "sources" / f"{completed_source}.pdf").exists()
