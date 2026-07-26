from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from threading import Thread
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


def upload_and_run(client: TestClient, filename: str, content: bytes) -> str:
    uploaded = client.post(
        "/api/sources", files={"file": (filename, content, "application/pdf")}
    )
    assert uploaded.status_code == 201
    published = client.post("/api/ingests/run")
    assert published.status_code == 200
    assert published.json()["job"]["status"] == "completed"
    return uploaded.json()["source_id"]


def commit_obsidian_annotation(vault: Path, page: Path, annotation: bytes) -> None:
    contents = page.read_bytes()
    replacement = START + b"\n" + annotation + b"\n" + END
    page.write_bytes(contents.replace(START + b"\n" + END, replacement))
    commit_researcher_edit(vault, page, "researcher annotation")


def commit_researcher_edit(vault: Path, page: Path, message: str) -> None:
    subprocess.run(["git", "-C", str(vault), "add", str(page.relative_to(vault))], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(vault),
            "-c",
            "user.name=Researcher",
            "-c",
            "user.email=researcher@local.invalid",
            "commit",
            "-m",
            message,
        ],
        check=True,
    )


def annotation_section(page: Path) -> bytes:
    contents = page.read_bytes()
    end = contents.index(END) + len(END)
    while end < len(contents) and contents[end : end + 1] in {b"\r", b"\n"}:
        end += 1
    return contents[contents.index(START) : end]


def wait_for_stage(data_dir: Path) -> None:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if list((data_dir / "runtime").glob("wiki-stage-*")):
            return
        time.sleep(0.01)
    raise AssertionError("The staged writer did not start.")


def commit_researcher_managed_edit(vault: Path, page: Path) -> None:
    page.write_text(
        page.read_text(encoding="utf-8").replace(
            "Research methods are a substantive reusable method topic supported by this source.",
            "A researcher changed this managed topic while the writer was preparing an update.",
        ),
        encoding="utf-8",
    )
    commit_researcher_edit(vault, page, "researcher managed edit")


def test_obsidian_annotation_is_preserved_byte_for_byte_by_a_later_ingest(
    tmp_path: Path,
) -> None:
    with make_client(tmp_path) as client:
        first_id = upload_and_run(client, "first.pdf", text_pdf("First paper."))
        vault = tmp_path / "vault"
        first_page = vault / "papers" / f"{first_id}.md"
        annotation = b"A researcher note with  two spaces\r\n- and a literal tab\t"
        commit_obsidian_annotation(vault, first_page, annotation)

        second_id = upload_and_run(client, "second.pdf", text_pdf("Second paper."))

    assert second_id in (vault / "index.md").read_text(encoding="utf-8")
    assert annotation_section(first_page) == START + b"\n" + annotation + b"\n" + END + b"\n"


def test_ambiguous_protected_annotation_boundaries_are_rejected(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        upload_and_run(client, "first.pdf", text_pdf("First paper."))

    vault = tmp_path / "vault"
    previous_head = subprocess.run(
        ["git", "-C", str(vault), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    with make_client(tmp_path, fake_mode="annotation-ambiguous") as client:
        uploaded = client.post(
            "/api/sources", files={"file": ("second.pdf", text_pdf("Second paper."), "application/pdf")}
        )
        failed = client.post("/api/ingests/run")

    assert uploaded.status_code == 201
    assert failed.json()["job"]["status"] == "failed"
    assert "ambiguous researcher-annotation" in failed.json()["job"]["error"]
    current_head = subprocess.run(
        ["git", "-C", str(vault), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert current_head == previous_head


def test_annotation_section_final_newline_bytes_are_protected(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        upload_and_run(client, "first.pdf", text_pdf("First paper."))

    vault = tmp_path / "vault"
    previous_head = subprocess.run(
        ["git", "-C", str(vault), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    with make_client(tmp_path, fake_mode="annotation-trailing-newline") as client:
        uploaded = client.post(
            "/api/sources", files={"file": ("second.pdf", text_pdf("Second paper."), "application/pdf")}
        )
        failed = client.post("/api/ingests/run")

    assert uploaded.status_code == 201
    assert failed.json()["job"]["status"] == "failed"
    assert "modified researcher annotations" in failed.json()["job"]["error"]
    assert subprocess.run(
        ["git", "-C", str(vault), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip() == previous_head


def test_writer_rebases_onto_a_concurrent_obsidian_annotation_commit(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        first_id = upload_and_run(client, "first.pdf", text_pdf("First paper."))

    vault = tmp_path / "vault"
    first_page = vault / "papers" / f"{first_id}.md"
    with make_client(tmp_path, fake_mode="wait-for-concurrent-commit") as client:
        uploaded = client.post(
            "/api/sources", files={"file": ("second.pdf", text_pdf("Second paper."), "application/pdf")}
        )
        response: list[object] = []
        runner = Thread(target=lambda: response.append(client.post("/api/ingests/run")))
        runner.start()
        wait_for_stage(tmp_path)
        annotation = b"Committed from Obsidian while the ingest was staged."
        commit_obsidian_annotation(vault, first_page, annotation)
        runner.join(timeout=5)

    assert uploaded.status_code == 201
    assert not runner.is_alive()
    assert response[0].json()["job"]["status"] == "completed"
    assert annotation_section(first_page) == START + b"\n" + annotation + b"\n" + END + b"\n"
    assert subprocess.run(
        ["git", "-C", str(vault), "rev-list", "--count", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip() == "3"
    assert subprocess.run(
        ["git", "-C", str(vault), "log", "-1", "--format=%s", "HEAD^"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip() == "researcher annotation"


def test_unresolvable_concurrent_change_is_recoverable_and_keeps_researcher_head(
    tmp_path: Path,
) -> None:
    with make_client(tmp_path) as client:
        upload_and_run(client, "first.pdf", text_pdf("The first paper describes a method."))

    vault = tmp_path / "vault"
    topic = vault / "topics" / "research-methods.md"
    with make_client(tmp_path, fake_mode="wait-for-concurrent-commit") as client:
        uploaded = client.post(
            "/api/sources",
            files={"file": ("second.pdf", text_pdf("The second paper describes a method."), "application/pdf")},
        )
        response: list[object] = []
        runner = Thread(target=lambda: response.append(client.post("/api/ingests/run")))
        runner.start()
        wait_for_stage(tmp_path)
        commit_researcher_managed_edit(vault, topic)
        researcher_head = subprocess.run(
            ["git", "-C", str(vault), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        runner.join(timeout=5)

    assert uploaded.status_code == 201
    assert not runner.is_alive()
    assert response[0].json()["job"]["status"] == "failed"
    assert "could not be rebased" in response[0].json()["job"]["error"]
    current_head = subprocess.run(
        ["git", "-C", str(vault), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert current_head == researcher_head
    assert "researcher changed this managed topic" in topic.read_text(encoding="utf-8")
