from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient

from researchos.main import Settings, create_app
from test_atomic_paper_ingest import text_pdf


FAKE_CODEX = Path(__file__).parents[1] / "scripts" / "fake-codex"


def make_client(data_dir: Path) -> TestClient:
    return TestClient(
        create_app(
            Settings(
                data_dir=data_dir,
                codex_command=(sys.executable, str(FAKE_CODEX)),
                run_ingest_service=False,
            )
        )
    )


def publish_paper(client: TestClient) -> str:
    uploaded = client.post(
        "/api/sources",
        files={
            "file": (
                "methods-paper.pdf",
                text_pdf("A local research method has a measurable limitation."),
                "application/pdf",
            )
        },
    )
    assert uploaded.status_code == 201
    completed = client.post("/api/ingests/run")
    assert completed.status_code == 200
    assert completed.json()["job"]["status"] == "completed"
    return uploaded.json()["source_id"]


def test_wiki_browses_only_the_latest_published_snapshot_through_read_only_web_pages(
    tmp_path: Path,
) -> None:
    with make_client(tmp_path) as client:
        source_id = publish_paper(client)

        staged_page = tmp_path / "runtime" / "wiki-stage-unpublished" / "topics" / "hidden.md"
        staged_page.parent.mkdir(parents=True)
        staged_page.write_text(
            "---\ntitle: Unpublished only\n---\nThe unpublished-only-text must stay hidden.\n",
            encoding="utf-8",
        )

        wiki = client.get("/wiki")
        paper = client.get(f"/wiki/papers/{source_id}")
        topic = client.get("/wiki/topics/research-methods")
        search = client.get("/wiki/search", params={"q": "research method"})
        staged_search = client.get("/wiki/search", params={"q": "unpublished-only-text"})
        index = client.get("/wiki/index")
        activity = client.get("/wiki/activity")
        write_attempt = client.post(f"/wiki/papers/{source_id}")

    assert wiki.status_code == 200
    assert f'href="/wiki/papers/{source_id}"' in wiki.text
    assert 'href="/wiki/topics/research-methods"' in wiki.text
    assert "Unpublished only" not in wiki.text

    assert paper.status_code == 200
    assert "Page metadata" in paper.text
    assert "page_type:" not in paper.text
    assert "Evidence citations" in paper.text
    assert "Source identity" in paper.text
    assert "PDF page 1" in paper.text
    assert 'href="/wiki/topics/research-methods"' in paper.text
    assert "<form" not in paper.text
    assert "Edit" not in paper.text

    assert topic.status_code == 200
    assert "Backlinks" in topic.text
    assert f'href="/wiki/papers/{source_id}"' in topic.text

    assert search.status_code == 200
    assert f'href="/wiki/papers/{source_id}"' in search.text
    assert 'href="/wiki/topics/research-methods"' in search.text
    assert staged_search.status_code == 200
    assert "No published pages match" in staged_search.text
    assert "Unpublished only" not in staged_search.text

    assert index.status_code == activity.status_code == 200
    assert "ResearchOS index" in index.text
    assert "ResearchOS activity log" in activity.text
    assert source_id in activity.text
    assert f'href="/wiki/papers/{source_id}"' in activity.text
    assert "ingest" in activity.text and "published" in activity.text
    assert write_attempt.status_code == 405
