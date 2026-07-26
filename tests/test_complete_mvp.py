from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time

from fastapi.testclient import TestClient

from researchos.main import Settings, create_app
from test_atomic_paper_ingest import text_pdf


FAKE_CODEX = Path(__file__).parents[1] / "scripts" / "fake-codex"


def structured_pdf() -> bytes:
    """A one-page PDF with two columns, table lines, an equation, and a figure box."""

    stream = """
BT /F1 12 Tf 1 0 0 1 72 720 Tm (Left column: the initial method has a higher outcome.) Tj ET
BT /F1 12 Tf 1 0 0 1 320 720 Tm (Right column: the follow-up reports a lower outcome.) Tj ET
72 650 m 540 650 l S 72 620 m 540 620 l S 72 590 m 540 590 l S
72 590 m 72 650 l S 300 590 m 300 650 l S 540 590 m 540 650 l S
BT /F1 11 Tf 1 0 0 1 82 632 Tm (Table 1: compared runs) Tj ET
BT /F1 11 Tf 1 0 0 1 82 605 Tm (Equation: E = m c squared) Tj ET
72 450 180 90 re S
BT /F1 11 Tf 1 0 0 1 82 430 Tm (Figure 1: measured method outcome) Tj ET
""".strip()
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Count 1 /Kids [4 0 R] >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 3 0 R >> >> /Contents 5 0 R >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
    ]
    result = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, contents in enumerate(objects, start=1):
        offsets.append(len(result))
        result.extend(f"{number} 0 obj\n{contents}\nendobj\n".encode())
    xref = len(result)
    result.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    result.extend(b"".join(f"{offset:010} 00000 n \n".encode() for offset in offsets[1:]))
    result.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(result)


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


def upload_and_ingest(client: TestClient, filename: str, contents: str | bytes) -> str:
    document = text_pdf(contents) if isinstance(contents, str) else contents
    uploaded = client.post(
        "/api/sources",
        files={"file": (filename, document, "application/pdf")},
    )
    assert uploaded.status_code == 201
    completed = client.post("/api/ingests/run")
    assert completed.status_code == 200
    assert completed.json()["job"]["status"] == "completed"
    return uploaded.json()["source_id"]


def git_count(vault: Path) -> int:
    return int(
        subprocess.run(
            ["git", "-C", str(vault), "rev-list", "--count", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )


def wait_for(predicate: object) -> None:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if callable(predicate) and predicate():
            return
        time.sleep(0.02)
    raise AssertionError("Timed out waiting for the public vault state to settle.")


def test_complete_local_mvp_acceptance_flow_captures_evidence_metrics_and_ui(
    tmp_path: Path,
) -> None:
    """Exercise the complete deterministic proof at the public application seam."""

    with make_client(tmp_path) as client:
        first_source = upload_and_ingest(
            client,
            "ordinary-prose.pdf",
            "The initial evaluation reports a research method with a higher outcome.",
        )
        second_source = upload_and_ingest(
            client,
            "structured-follow-up.pdf",
            structured_pdf(),
        )
        library = client.get("/library")
        research = client.post(
            "/api/research/messages",
            json={"message": "How do the two research methods compare?"},
        )
        filed = client.post("/api/research/analyses", json={"title": "Method comparison"})
        corrected = client.put(
            f"/api/sources/{second_source}/metadata",
            json={
                "title": "Corrected structured follow-up",
                "authors": ["Ada Lovelace"],
                "year": 2026,
                "doi": "10.5555/researchos.smoke",
            },
        )
        lint_started = client.post("/api/wiki/lint")
        lint = client.post("/api/wiki/lint/run")
        wiki = client.get("/wiki")
        graph = client.get("/api/graph")

        vault = tmp_path / "vault"
        source_page = vault / "papers" / f"{first_source}.md"
        annotated = source_page.read_bytes().replace(
            b"<!-- researcher-annotations:start -->\n<!-- researcher-annotations:end -->",
            b"<!-- researcher-annotations:start -->\nVerified in Obsidian.\n<!-- researcher-annotations:end -->",
        )
        source_page.write_bytes(annotated)
        wait_for(
            lambda: subprocess.run(
                ["git", "-C", str(vault), "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout == ""
        )
        revision = client.post(
            "/api/sources",
            data={"revision_of": first_source},
            files={
                "file": (
                    "ordinary-prose-revision.pdf",
                    text_pdf("The corrected method reports a lower outcome after review."),
                    "application/pdf",
                )
            },
        )
        assert revision.status_code == 201
        revised = client.post("/api/ingests/run")
        withdrawn = client.post(f"/api/sources/{first_source}/withdraw")

    first_job = json.loads((tmp_path / "runtime" / "ingest-jobs.json").read_text())["jobs"][
        first_source
    ]
    derivative = tmp_path / first_job["derivative"]
    metrics = first_job["metrics"]
    tracked = subprocess.run(
        ["git", "-C", str(tmp_path / "vault"), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    history_paths = subprocess.run(
        ["git", "-C", str(tmp_path / "vault"), "log", "--all", "--name-only", "--format="],
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert all(value >= 0 for value in metrics.values())
    assert metrics["derivative_bytes"] == len(derivative.read_bytes())
    assert "Ingest metrics:" in library.text
    assert "pdf-page: 1" in derivative.read_text(encoding="utf-8")
    second_derivative = tmp_path / json.loads(
        (tmp_path / "runtime" / "ingest-jobs.json").read_text()
    )["jobs"][second_source]["derivative"]
    assert "Table 1" in second_derivative.read_text(encoding="utf-8")
    assert "Figure 1" in second_derivative.read_text(encoding="utf-8")
    assert first_source in research.text and second_source in research.text
    assert "Lab sources" in research.text
    assert filed.status_code == 201
    assert corrected.status_code == 200
    assert lint_started.status_code == 202
    assert lint.json()["job"]["status"] == "completed"
    assert wiki.status_code == graph.status_code == 200
    assert all(area in client.get("/").text for area in ("Library", "Research", "Wiki", "Graph"))
    assert "textarea" not in client.get(f"/wiki/papers/{second_source}").text
    assert graph.json()["edges"]
    assert b"Verified in Obsidian." in source_page.read_bytes()
    assert revised.json()["job"]["status"] == "completed"
    assert withdrawn.status_code == 200
    assert git_count(tmp_path / "vault") >= 7
    assert first_source in (tmp_path / "vault" / "log.md").read_text(encoding="utf-8")
    assert ".pdf" not in tracked and "derivative" not in tracked
    assert all(
        artifact not in history_paths.casefold()
        for artifact in (".pdf", "derivative", "manifest", "ingest-job", "research-thread")
    )

    with make_client(tmp_path) as restarted:
        assert first_source in restarted.get("/library").text
        assert restarted.get("/api/research/thread").json()["messages"]
