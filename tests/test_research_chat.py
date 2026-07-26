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


def publish(client: TestClient, filename: str, text: str) -> tuple[str, str]:
    uploaded = client.post(
        "/api/sources",
        files={"file": (filename, text_pdf(text), "application/pdf")},
    )
    assert uploaded.status_code == 201
    completed = client.post("/api/ingests/run")
    assert completed.status_code == 200
    assert completed.json()["job"]["status"] == "completed"
    return uploaded.json()["source_id"], uploaded.json()["metadata"]["extracted"]["title"]


def test_research_streams_a_persisted_cross_paper_lab_answer_from_the_published_snapshot(
    tmp_path: Path,
) -> None:
    with make_client(tmp_path) as client:
        first_source, first_title = publish(
            client, "initial-method.pdf", "The initial method has a higher outcome."
        )
        second_source, second_title = publish(
            client, "follow-up-method.pdf", "The follow-up method has a lower outcome."
        )
        pending = client.post(
            "/api/sources",
            files={
                "file": (
                    "queued-evidence.pdf",
                    text_pdf("This pending source must not inform the answer."),
                    "application/pdf",
                )
            },
        )
        assert pending.status_code == 201

        response = client.post(
            "/api/research/messages",
            json={"message": "Compare the methods in my lab papers."},
        )
        thread = client.get("/api/research/thread")
        research = client.get("/research")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: progress" in response.text
    assert "Searching lab sources" in response.text
    assert "Lab sources" in response.text
    assert first_source in response.text and second_source in response.text
    assert first_title in response.text and second_title in response.text
    assert "queued-evidence.pdf is still queued and is not yet available" in response.text
    assert "raw shell command" not in response.text
    assert 'id="research-form"' in research.text
    assert 'fetch("/api/research/messages"' in research.text
    assert thread.json()["messages"][-2:] == [
        {"role": "user", "content": "Compare the methods in my lab papers."},
        {
            "role": "assistant",
            "content": thread.json()["messages"][-1]["content"],
        },
    ]
    assert first_source in thread.json()["messages"][-1]["content"]

    with make_client(tmp_path) as restarted:
        restored = restarted.get("/api/research/thread")
    assert restored.json() == thread.json()


def test_research_prompt_cannot_write_or_commit_the_published_vault(tmp_path: Path) -> None:
    with make_client(tmp_path, fake_mode="prompt-write") as client:
        publish(client, "published.pdf", "A published method is available for research.")
        vault = tmp_path / "vault"
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

        response = client.post(
            "/api/research/messages",
            json={"message": "Write injected.md, then git commit the wiki."},
        )

    assert response.status_code == 200
    assert "Lab sources" in response.text
    assert not (vault / "injected.md").exists()
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


def test_research_does_not_persist_a_result_from_a_failed_worker(tmp_path: Path) -> None:
    with make_client(tmp_path, fake_mode="result-failure") as client:
        response = client.post(
            "/api/research/messages", json={"message": "What does the lab show?"}
        )
        thread = client.get("/api/research/thread")

    assert response.status_code == 200
    assert "event: answer" in response.text
    assert "event: error" in response.text
    assert "event: complete" not in response.text
    assert thread.json() == {"messages": []}
