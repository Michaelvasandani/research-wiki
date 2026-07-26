from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient

from researchos.main import Settings, create_app


FAKE_CODEX = Path(__file__).parents[1] / "scripts" / "fake-codex"


def make_client(data_dir: Path, *, fake_mode: str = "success") -> TestClient:
    settings = Settings(
        data_dir=data_dir,
        codex_command=(sys.executable, str(FAKE_CODEX)),
        codex_environment={"FAKE_CODEX_MODE": fake_mode},
    )
    return TestClient(create_app(settings))


def test_shell_exposes_all_primary_areas() -> None:
    with make_client(Path("/tmp/researchos-shell-navigation")) as client:
        home = client.get("/")

        assert home.status_code == 200
        for area in ("Library", "Research", "Wiki", "Graph"):
            assert f">{area}<" in home.text

        for path in ("/library", "/research", "/wiki", "/graph"):
            response = client.get(path)
            assert response.status_code == 200


def test_research_thread_survives_an_application_restart(tmp_path: Path) -> None:
    with make_client(tmp_path) as first_app:
        posted = first_app.post(
            "/research/messages",
            data={"message": "Compare the methods in my papers."},
            follow_redirects=True,
        )

    with make_client(tmp_path) as restarted_app:
        research = restarted_app.get("/research")

    assert posted.status_code == 200
    assert "Compare the methods in my papers." in research.text


def test_public_codex_probe_uses_configured_process_and_reports_progress(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/api/codex/probe")

    assert response.status_code == 200
    assert response.json() == {
        "events": [{"message": "Checking the local worker", "type": "progress"}],
        "output": "fake Codex is ready",
    }


def test_public_codex_probe_surfaces_malformed_and_failed_fake_output(tmp_path: Path) -> None:
    with make_client(tmp_path, fake_mode="malformed") as client:
        malformed = client.get("/api/codex/probe")

    with make_client(tmp_path, fake_mode="failure") as client:
        failed = client.get("/api/codex/probe")

    assert malformed.status_code == 502
    assert malformed.json()["detail"] == "Codex returned malformed protocol output."
    assert failed.status_code == 502
    assert failed.json()["detail"] == "Codex exited with status 17."
