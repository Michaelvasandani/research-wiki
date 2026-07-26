from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import time

from fastapi.testclient import TestClient

from researchos.main import Settings, create_app
from test_atomic_paper_ingest import text_pdf


FAKE_CODEX = Path(__file__).parents[1] / "scripts" / "fake-codex"
START = b"<!-- researcher-annotations:start -->"
END = b"<!-- researcher-annotations:end -->"


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


def upload_and_run(client: TestClient, filename: str, content: bytes) -> str:
    uploaded = client.post(
        "/api/sources", files={"file": (filename, content, "application/pdf")}
    )
    assert uploaded.status_code == 201
    published = client.post("/api/ingests/run")
    assert published.status_code == 200
    assert published.json()["job"]["status"] == "completed"
    return uploaded.json()["source_id"]


def commit_count(vault: Path) -> int:
    return int(
        subprocess.run(
            ["git", "-C", str(vault), "rev-list", "--count", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
        ).stdout
    )


def wait_for(predicate: object) -> None:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if callable(predicate) and predicate():
            return
        time.sleep(0.02)
    raise AssertionError("The expected watcher outcome did not occur.")


def replace_annotation(page: Path, annotation: bytes) -> None:
    contents = page.read_bytes()
    page.write_bytes(
        contents.replace(START + b"\n" + END, START + b"\n" + annotation + b"\n" + END)
    )


def test_obsidian_annotation_saves_are_debounced_committed_once_and_survive_restart(
    tmp_path: Path,
) -> None:
    with make_client(tmp_path) as client:
        source_id = upload_and_run(client, "first.pdf", text_pdf("First paper."))
        vault = tmp_path / "vault"
        page = vault / "papers" / f"{source_id}.md"
        replace_annotation(page, b"first save")
        replace_annotation(page, b"completed Obsidian save")
        wait_for(lambda: commit_count(vault) == 2)

        assert client.get("/api/wiki/conflicts").json() == {"conflicts": []}
        assert subprocess.run(
            ["git", "-C", str(vault), "show", "--format=%s", "-s", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip() == "researcher edit: annotations"

    with make_client(tmp_path):
        time.sleep(0.3)
        assert commit_count(vault) == 2


def test_managed_obsidian_edit_is_committed_conflicted_and_pauses_that_writer(
    tmp_path: Path,
) -> None:
    with make_client(tmp_path) as client:
        first_id = upload_and_run(
            client, "first.pdf", text_pdf("First paper describes a method.")
        )
        vault = tmp_path / "vault"
        topic = vault / "topics" / "research-methods.md"
        replacement = "A researcher changed this managed topic."
        topic.write_text(
            topic.read_text(encoding="utf-8").replace(
                "Research methods are a substantive reusable method topic supported "
                "by this source.",
                replacement,
            ),
            encoding="utf-8",
        )
        wait_for(lambda: commit_count(vault) == 2)

    with make_client(tmp_path) as client:
        time.sleep(0.3)
        assert commit_count(vault) == 2
        conflicts = client.get("/api/wiki/conflicts").json()["conflicts"]
        assert [conflict["path"] for conflict in conflicts] == ["topics/research-methods.md"]
        page = client.get("/wiki/topics/research-methods")
        assert "Automatic writers are paused" in page.text

        uploaded = client.post(
            "/api/sources",
            files={
                "file": (
                    "second.pdf",
                    text_pdf("Second paper describes a method."),
                    "application/pdf",
                )
            },
        )
        result = client.post("/api/ingests/run")
        assert replacement in topic.read_text(encoding="utf-8")

        resolved = client.post("/wiki/topics/research-methods/resolve-conflict")
        retried = client.post(f"/api/ingests/{uploaded.json()['source_id']}/retry")
        resumed = client.post("/api/ingests/run")

    assert uploaded.status_code == 201
    assert result.json()["job"]["status"] == "failed"
    assert "page conflict" in result.json()["job"]["error"]
    assert resolved.status_code == 200
    assert retried.status_code == 200
    assert resumed.json()["job"]["status"] == "completed"
    assert first_id in (vault / "papers" / f"{first_id}.md").read_text(encoding="utf-8")


def test_watcher_ignores_non_page_files(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        upload_and_run(client, "first.pdf", text_pdf("First paper."))
        vault = tmp_path / "vault"
        initial_count = commit_count(vault)
        for path in (
            vault / "source.pdf",
            vault / "derivatives" / "derivative.md",
            vault / "manifest.json",
            vault / "ingest-jobs.json",
            vault / "research-thread.json",
            vault / ".research-methods.md.swp",
            vault / "unrelated.md",
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("ignored", encoding="utf-8")
        time.sleep(0.4)

    assert commit_count(vault) == initial_count
