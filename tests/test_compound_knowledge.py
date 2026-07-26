from __future__ import annotations

from pathlib import Path
import re
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


def ingest(client: TestClient, filename: str, text: str) -> str:
    uploaded = client.post(
        "/api/sources",
        files={"file": (filename, text_pdf(text), "application/pdf")},
    )
    assert uploaded.status_code == 201
    published = client.post("/api/ingests/run")
    assert published.status_code == 200
    assert published.json()["job"]["status"] == "completed"
    return uploaded.json()["source_id"]


def git_commit_count(vault: Path) -> int:
    return int(
        subprocess.run(
            ["git", "-C", str(vault), "rev-list", "--count", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
        ).stdout
    )


def test_second_ingest_compounds_cited_knowledge_without_merging_ambiguity(
    tmp_path: Path,
) -> None:
    with make_client(tmp_path) as client:
        first_source = ingest(
            client,
            "initial-method.pdf",
            "The initial evaluation reports that a method has a higher outcome under its stated assumption.",
        )
        first_head = subprocess.run(
            ["git", "-C", str(tmp_path / "vault"), "rev-parse", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
        first_topic = (tmp_path / "vault" / "topics" / "research-methods.md").read_text(
            encoding="utf-8"
        )
        second_source = ingest(
            client,
            "follow-up-method.pdf",
            "The follow-up evaluation reports a lower outcome for a possible duplicate method under another assumption.",
        )
        topic = client.get("/wiki/topics/research-methods")
        variant = client.get("/wiki/topics/research-method-variants")
        first_paper = client.get(f"/wiki/papers/{first_source}")
        graph = client.get("/api/graph")
        activity = client.get("/wiki/activity")
        index = client.get("/wiki/index")

    vault = tmp_path / "vault"
    topic_text = (vault / "topics" / "research-methods.md").read_text(encoding="utf-8")
    log_text = (vault / "log.md").read_text(encoding="utf-8")
    graph_edges = {(edge["source"], edge["target"]) for edge in graph.json()["edges"]}

    assert git_commit_count(vault) == 2
    assert subprocess.run(
        ["git", "-C", str(vault), "merge-base", "--is-ancestor", first_head, "HEAD"],
        check=False,
    ).returncode == 0
    assert topic.status_code == variant.status_code == first_paper.status_code == 200
    assert first_source in topic_text and second_source in topic_text
    assert re.search(rf"source {first_source} — PDF p\. 1", topic_text)
    assert re.search(rf"source {second_source} — PDF p\. 1", topic_text)
    for historical_line in first_topic.splitlines():
        if f"[^source-{first_source[:12]}-p1]" in historical_line:
            assert historical_line in topic_text
    assert "Contradictions" in topic.text
    assert "Possible duplicates" in topic.text
    assert f'href="/wiki/papers/{first_source}"' in topic.text
    assert f'href="/wiki/topics/research-methods"' in first_paper.text
    assert {
        (f"paper-{first_source}", "topic-research-methods"),
        (f"paper-{second_source}", "topic-research-methods"),
        ("topic-research-methods", f"paper-{first_source}"),
        ("topic-research-methods", f"paper-{second_source}"),
        ("topic-research-methods", "topic-research-method-variants"),
        ("topic-research-method-variants", "topic-research-methods"),
    } <= graph_edges
    assert f'href="/wiki/papers/{second_source}"' in index.text
    assert "Contradictions: 1" in log_text
    assert "Possible duplicates: 1" in log_text
    assert first_source in activity.text and second_source in activity.text


def test_incidental_terminology_stays_inline_without_a_topic_page(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        source_id = ingest(
            client,
            "incidental-term.pdf",
            "The paper uses the incidental abbreviation ARX once in its introduction.",
        )
        paper = client.get(f"/wiki/papers/{source_id}")
        topic = client.get("/wiki/topics/research-methods")

    assert paper.status_code == 200
    assert "No related pages yet." in paper.text
    assert topic.status_code == 404
    assert not list((tmp_path / "vault" / "topics").glob("*.md"))


def test_second_ingest_cannot_remove_a_first_source_citation(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        first_source = ingest(
            client,
            "initial-method.pdf",
            "The initial evaluation reports a method with a higher outcome.",
        )

    vault = tmp_path / "vault"
    original_topic = (vault / "topics" / "research-methods.md").read_text(encoding="utf-8")
    original_head = subprocess.run(
        ["git", "-C", str(vault), "rev-parse", "HEAD"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()

    with make_client(tmp_path, fake_mode="drop-history") as client:
        uploaded = client.post(
            "/api/sources",
            files={
                "file": (
                    "follow-up-method.pdf",
                    text_pdf("The follow-up evaluation reports a method with a lower outcome."),
                    "application/pdf",
                )
            },
        )
        assert uploaded.status_code == 201
        second_source = uploaded.json()["source_id"]
        failed = client.post("/api/ingests/run")

    assert failed.status_code == 200
    assert failed.json()["job"]["status"] == "failed"
    assert first_source in original_topic
    assert second_source not in (vault / "index.md").read_text(encoding="utf-8")
    assert (vault / "topics" / "research-methods.md").read_text(encoding="utf-8") == original_topic
    assert subprocess.run(
        ["git", "-C", str(vault), "rev-parse", "HEAD"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip() == original_head
