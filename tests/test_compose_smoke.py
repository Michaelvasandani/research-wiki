from __future__ import annotations

import os
import json
from pathlib import Path
import socket
import subprocess
import time
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest


ROOT = Path(__file__).parents[1]


def docker_is_available() -> bool:
    return subprocess.run(
        ["docker", "info"], capture_output=True, check=False
    ).returncode == 0


def available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def get(url: str) -> tuple[int, str]:
    with urlopen(url, timeout=2) as response:  # noqa: S310 - localhost test server
        return response.status, response.read().decode()


def post_form(url: str, values: dict[str, str]) -> tuple[int, str]:
    request = Request(
        url,
        data=urlencode(values).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=2) as response:  # noqa: S310 - localhost test server
        return response.status, response.read().decode()


@pytest.mark.compose
def test_compose_shell_persists_state_and_exposes_fake_codex(tmp_path: Path) -> None:
    if not docker_is_available():
        pytest.skip("Docker daemon is unavailable")

    project = f"researchos-smoke-{uuid4().hex[:8]}"
    port = available_port()
    environment = os.environ | {
        "RESEARCHOS_DATA_HOST_DIR": str(tmp_path / "data"),
        "RESEARCHOS_PORT": str(port),
    }
    compose = ["docker", "compose", "-p", project]
    base_url = f"http://127.0.0.1:{port}"

    try:
        subprocess.run(
            [*compose, "up", "--build", "--detach"],
            cwd=ROOT,
            env=environment,
            check=True,
        )
        deadline = time.monotonic() + 30
        while True:
            try:
                status, _ = get(f"{base_url}/api/health")
                if status == 200:
                    break
            except URLError:
                pass
            if time.monotonic() >= deadline:
                raise AssertionError("Compose application did not start within 30 seconds")
            time.sleep(0.25)

        status, home = get(f"{base_url}/")
        assert status == 200
        assert all(area in home for area in ("Library", "Research", "Wiki", "Graph"))
        assert post_form(
            f"{base_url}/research/messages", {"message": "Persist across Compose restart"}
        )[0] == 200
        assert json.loads(get(f"{base_url}/api/codex/probe")[1]) == {
            "events": [{"type": "progress", "message": "Checking the local worker"}],
            "output": "fake Codex is ready",
        }

        subprocess.run([*compose, "restart"], cwd=ROOT, env=environment, check=True)
        deadline = time.monotonic() + 30
        while True:
            try:
                _, research = get(f"{base_url}/research")
                if "Persist across Compose restart" in research:
                    break
            except URLError:
                pass
            if time.monotonic() >= deadline:
                raise AssertionError("Persisted state was unavailable after Compose restart")
            time.sleep(0.25)
    finally:
        subprocess.run(
            [*compose, "down", "--volumes"],
            cwd=ROOT,
            env=environment,
            check=False,
        )
