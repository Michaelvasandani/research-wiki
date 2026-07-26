from __future__ import annotations

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


def publish(client: TestClient, filename: str, text: str) -> str:
    uploaded = client.post(
        "/api/sources",
        files={"file": (filename, text_pdf(text), "application/pdf")},
    )
    assert uploaded.status_code == 201
    completed = client.post("/api/ingests/run")
    assert completed.status_code == 200
    assert completed.json()["job"]["status"] == "completed"
    return uploaded.json()["source_id"]


def test_researcher_can_file_a_supported_cross_paper_analysis_as_one_published_update(
    tmp_path: Path,
) -> None:
    with make_client(tmp_path) as client:
        first_source = publish(
            client, "initial-method.pdf", "The initial method has a higher outcome."
        )
        second_source = publish(
            client, "follow-up-method.pdf", "The follow-up method has a lower outcome."
        )
        chat = client.post(
            "/api/research/messages",
            json={"message": "Compare the methods in my lab papers."},
        )
        vault = tmp_path / "vault"
        before_count = int(
            subprocess.run(
                ["git", "-C", str(vault), "rev-list", "--count", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )

        filed = client.post(
            "/api/research/analyses",
            json={"title": "Method comparison"},
        )
        wiki = client.get("/wiki")
        analysis = client.get("/wiki/analyses/method-comparison")
        search = client.get("/wiki/search", params={"q": "Method comparison"})
        graph = client.get("/api/graph")

    assert chat.status_code == 200
    assert filed.status_code == 201
    assert filed.json()["path"] == "analyses/method-comparison"
    assert int(
        subprocess.run(
            ["git", "-C", str(vault), "rev-list", "--count", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    ) == before_count + 1
    contents = (vault / "analyses" / "method-comparison.md").read_text(encoding="utf-8")
    assert "page_type: filed-analysis" in contents
    assert first_source in contents and second_source in contents
    assert "PDF p. 1" in contents
    assert "[[papers/" in contents
    assert "## Researcher annotations" in contents
    assert "Method comparison" in (vault / "index.md").read_text(encoding="utf-8")
    assert "filed analysis" in (vault / "log.md").read_text(encoding="utf-8")
    assert wiki.status_code == analysis.status_code == search.status_code == graph.status_code == 200
    assert "Method comparison" in wiki.text and "Method comparison" in analysis.text
    assert "Method comparison" in search.text
    assert any(node["id"] == "analysis-method-comparison" for node in graph.json()["nodes"])


def test_external_research_cannot_be_filed_until_its_evidence_is_ingested(
    tmp_path: Path,
) -> None:
    with make_client(tmp_path, fake_mode="web") as client:
        publish(client, "lab-method.pdf", "The lab method has a higher outcome.")
        chat = client.post(
            "/api/research/messages",
            json={"message": "What later evidence addresses the gap in my lab paper?"},
        )
        vault = tmp_path / "vault"
        before_head = subprocess.run(
            ["git", "-C", str(vault), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        filed = client.post("/api/research/analyses", json={"title": "Later evidence"})

    assert chat.status_code == 200
    assert "External follow-up study" in chat.text
    assert filed.status_code == 409
    assert "must be ingested" in filed.json()["detail"]
    assert not (vault / "analyses" / "later-evidence.md").exists()
    assert subprocess.run(
        ["git", "-C", str(vault), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip() == before_head


def test_invalid_or_annotation_changing_filed_writer_output_publishes_nothing(
    tmp_path: Path,
) -> None:
    for fake_mode in ("file-invalid", "file-annotation"):
        data_dir = tmp_path / fake_mode
        with make_client(data_dir, fake_mode=fake_mode) as client:
            publish(client, "first.pdf", "The initial method has a higher outcome.")
            publish(client, "second.pdf", "The follow-up method has a lower outcome.")
            client.post(
                "/api/research/messages",
                json={"message": "Compare the methods in my lab papers."},
            )
            vault = data_dir / "vault"
            before_head = subprocess.run(
                ["git", "-C", str(vault), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            before_files = {
                path.relative_to(vault): path.read_bytes()
                for path in vault.rglob("*")
                if path.is_file() and ".git" not in path.parts
            }

            filed = client.post(
                "/api/research/analyses", json={"title": "Rejected comparison"}
            )

        assert filed.status_code == 409
        assert subprocess.run(
            ["git", "-C", str(vault), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip() == before_head
        assert {
            path.relative_to(vault): path.read_bytes()
            for path in vault.rglob("*")
            if path.is_file() and ".git" not in path.parts
        } == before_files


def test_filed_writer_cannot_publish_an_invalid_change_to_an_existing_page(
    tmp_path: Path,
) -> None:
    with make_client(tmp_path, fake_mode="file-corrupt-existing") as client:
        publish(client, "first.pdf", "The initial method has a higher outcome.")
        publish(client, "second.pdf", "The follow-up method has a lower outcome.")
        client.post(
            "/api/research/messages",
            json={"message": "Compare the methods in my lab papers."},
        )
        vault = tmp_path / "vault"
        before_head = subprocess.run(
            ["git", "-C", str(vault), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        filed = client.post(
            "/api/research/analyses", json={"title": "Corrupt existing page"}
        )

    assert filed.status_code == 409
    assert subprocess.run(
        ["git", "-C", str(vault), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip() == before_head


def test_ordinary_research_chat_does_not_create_a_wiki_analysis(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        first_source = publish(
            client, "first.pdf", "The initial method has a higher outcome."
        )
        second_source = publish(
            client, "second.pdf", "The follow-up method has a lower outcome."
        )
        vault = tmp_path / "vault"
        before_head = subprocess.run(
            ["git", "-C", str(vault), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        chat = client.post(
            "/api/research/messages",
            json={"message": "Compare the methods in my lab papers."},
        )
        wiki = client.get("/wiki")

    assert chat.status_code == 200
    assert first_source in chat.text and second_source in chat.text
    assert not (vault / "analyses").exists()
    assert "filed-analysis" not in wiki.text
    assert subprocess.run(
        ["git", "-C", str(vault), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip() == before_head


def test_single_source_research_cannot_be_filed_as_a_cross_paper_analysis(
    tmp_path: Path,
) -> None:
    with make_client(tmp_path) as client:
        publish(client, "only-paper.pdf", "The only method has a higher outcome.")
        chat = client.post(
            "/api/research/messages",
            json={"message": "What does my lab paper show?"},
        )
        filed = client.post("/api/research/analyses", json={"title": "One paper only"})

    assert chat.status_code == 200
    assert filed.status_code == 409
    assert "two distinct ingested sources" in filed.json()["detail"]
