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


def head(vault: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(vault), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def wait_for(predicate: object) -> None:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if callable(predicate) and predicate():
            return
        time.sleep(0.02)
    raise AssertionError("The expected watcher outcome did not occur.")


def has_topic_conflict(client: TestClient) -> bool:
    return [
        conflict["path"] for conflict in client.get("/api/wiki/conflicts").json()["conflicts"]
    ] == ["topics/research-methods.md"]


def vault_is_clean(vault: Path) -> bool:
    return not subprocess.run(
        ["git", "-C", str(vault), "status", "--short"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def replace_annotation(page: Path, annotation: bytes) -> None:
    page.write_bytes(
        page.read_bytes().replace(START + b"\n" + END, START + b"\n" + annotation + b"\n" + END)
    )


def annotation_section(page: Path) -> bytes:
    contents = page.read_bytes()
    end = contents.index(END) + len(END)
    while end < len(contents) and contents[end : end + 1] in {b"\r", b"\n"}:
        end += 1
    return contents[contents.index(START) : end]


def test_researcher_can_run_lint_and_see_its_completed_atomic_repair(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        source_id = publish(client, "method.pdf", "A method has a higher outcome.")
        vault = tmp_path / "vault"
        before_head = head(vault)

        queued = client.post("/api/wiki/lint")
        status = client.get("/api/wiki/lint")
        completed = client.post("/api/wiki/lint/run")
        wiki = client.get("/wiki")

    assert queued.status_code == 202
    assert queued.json()["job"]["status"] == "queued"
    assert status.status_code == 200
    assert status.json()["job"]["status"] == "queued"
    assert completed.status_code == 200
    assert completed.json()["job"]["status"] == "completed"
    assert completed.json()["job"]["checks"] == [
        "contradictions",
        "stale claims",
        "orphan pages",
        "missing cross-references",
        "possible duplicates",
        "evidence gaps",
    ]
    assert head(vault) != before_head
    assert "wiki lint" in subprocess.run(
        ["git", "-C", str(vault), "log", "-1", "--format=%s"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    topic = vault / "topics" / "research-methods.md"
    assert "## Lint maintenance" in topic.read_text(encoding="utf-8")
    assert "Wiki lint" in (vault / "index.md").read_text(encoding="utf-8")
    assert "wiki lint" in (vault / "log.md").read_text(encoding="utf-8")
    assert "Wiki lint" in wiki.text and "completed" in wiki.text
    assert source_id in (vault / "papers" / f"{source_id}.md").read_text(encoding="utf-8")


def test_lint_rejects_annotation_changes_and_exposes_no_partial_update(tmp_path: Path) -> None:
    with make_client(tmp_path, fake_mode="lint-annotation") as client:
        publish(client, "method.pdf", "A method has a higher outcome.")
        vault = tmp_path / "vault"
        before_head = head(vault)
        before_files = {
            path.relative_to(vault): path.read_bytes()
            for path in vault.rglob("*")
            if path.is_file() and ".git" not in path.parts
        }

        assert client.post("/api/wiki/lint").status_code == 202
        completed = client.post("/api/wiki/lint/run")

    assert completed.status_code == 200
    assert completed.json()["job"]["status"] == "failed"
    assert "researcher annotations" in completed.json()["job"]["error"]
    assert head(vault) == before_head
    assert {
        path.relative_to(vault): path.read_bytes()
        for path in vault.rglob("*")
        if path.is_file() and ".git" not in path.parts
    } == before_files


def test_lint_reports_and_repairs_a_detected_missing_cross_reference(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        publish(
            client,
            "cross-reference.pdf",
            "A method has a higher outcome. Missing cross reference to a related page.",
        )
        assert client.post("/api/wiki/lint").status_code == 202
        completed = client.post("/api/wiki/lint/run")

    assert completed.json()["job"]["status"] == "completed"
    assert completed.json()["job"]["findings"]["missing cross-references"] == {
        "status": "repaired",
        "affected_pages": ["topics/research-methods"],
    }
    assert "[[index|ResearchOS index]]" in (
        tmp_path / "vault" / "topics" / "research-methods.md"
    ).read_text(encoding="utf-8")


def test_lint_preserves_a_researcher_annotation_during_a_successful_repair(
    tmp_path: Path,
) -> None:
    with make_client(tmp_path) as client:
        source_id = publish(client, "method.pdf", "A method has a higher outcome.")
        vault = tmp_path / "vault"
        paper = vault / "papers" / f"{source_id}.md"
        annotation = b"A researcher note with two spaces  \r\n- and a literal tab\t"
        replace_annotation(paper, annotation)
        wait_for(lambda: vault_is_clean(vault))

        assert client.post("/api/wiki/lint").status_code == 202
        completed = client.post("/api/wiki/lint/run")

    assert completed.json()["job"]["status"] == "completed"
    assert annotation_section(paper) == START + b"\n" + annotation + b"\n" + END + b"\n"


def test_lint_worker_failure_exposes_no_partial_update(tmp_path: Path) -> None:
    with make_client(tmp_path, fake_mode="lint-failure") as client:
        publish(client, "method.pdf", "A method has a higher outcome.")
        vault = tmp_path / "vault"
        before_head = head(vault)
        before_files = {
            path.relative_to(vault): path.read_bytes()
            for path in vault.rglob("*")
            if path.is_file() and ".git" not in path.parts
        }

        assert client.post("/api/wiki/lint").status_code == 202
        completed = client.post("/api/wiki/lint/run")

    assert completed.json()["job"]["status"] == "failed"
    assert "Codex exited" in completed.json()["job"]["error"]
    assert head(vault) == before_head
    assert {
        path.relative_to(vault): path.read_bytes()
        for path in vault.rglob("*")
        if path.is_file() and ".git" not in path.parts
    } == before_files


def test_lint_skips_a_conflicted_page_without_overwriting_it(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        publish(client, "method.pdf", "A method has a higher outcome.")
        vault = tmp_path / "vault"
        topic = vault / "topics" / "research-methods.md"
        original = topic.read_text(encoding="utf-8")
        topic.write_text(
            original.replace(
                "Research methods are a substantive reusable method topic supported by this source.",
                "A researcher changed this managed topic.",
            ),
            encoding="utf-8",
        )
        wait_for(lambda: has_topic_conflict(client))
        wait_for(lambda: vault_is_clean(vault))
        before_head = head(vault)

        assert client.post("/api/wiki/lint").status_code == 202
        completed = client.post("/api/wiki/lint/run")

    assert completed.json()["job"]["status"] == "failed"
    assert "page conflict" in completed.json()["job"]["error"]
    assert "A researcher changed this managed topic." in topic.read_text(encoding="utf-8")
    assert head(vault) == before_head


def test_lint_writer_uses_disabled_networking(tmp_path: Path) -> None:
    with make_client(tmp_path, fake_mode="lint-network") as client:
        publish(client, "method.pdf", "A method has a higher outcome.")
        assert client.post("/api/wiki/lint").status_code == 202
        completed = client.post("/api/wiki/lint/run")

    assert completed.status_code == 200
    assert completed.json()["job"]["status"] == "completed"
