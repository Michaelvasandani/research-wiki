from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


ADAPTER = Path(__file__).parents[1] / "scripts" / "real-codex"


def fake_codex(tmp_path: Path) -> Path:
    executable = tmp_path / "codex"
    executable.write_text(
        "#!/bin/sh\n"
        'printf "%s\\n" "$@" > "$RESEARCHOS_ADAPTER_ARGUMENTS"\n'
        "printf '%s\\n' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"ready\"}}'\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return executable


def run_adapter(tmp_path: Path, *arguments: str) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    argument_log = tmp_path / "arguments.txt"
    environment = os.environ | {
        "RESEARCHOS_CODEX_BIN": str(fake_codex(tmp_path)),
        "RESEARCHOS_ADAPTER_ARGUMENTS": str(argument_log),
    }
    result = subprocess.run(
        [sys.executable, str(ADAPTER), *arguments],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    return result, argument_log.read_text(encoding="utf-8").splitlines()


def test_real_codex_adapter_uses_supported_read_only_and_staged_writer_profiles(
    tmp_path: Path,
) -> None:
    probe, probe_arguments = run_adapter(tmp_path, "probe")

    stage = tmp_path / "stage"
    stage.mkdir()
    request = stage / "request.json"
    request.write_text(json.dumps({"staged_vault": str(stage)}), encoding="utf-8")
    writer, writer_arguments = run_adapter(tmp_path, "ingest", str(request))

    assert probe.returncode == writer.returncode == 0
    assert json.loads(probe.stdout.splitlines()[-1]) == {"type": "result", "output": "ready"}
    assert probe_arguments[:2] == ["exec", "--json"]
    assert "--ephemeral" in probe_arguments
    assert "--ask-for-approval" not in probe_arguments
    assert probe_arguments[probe_arguments.index("--sandbox") + 1] == "read-only"
    assert writer_arguments[writer_arguments.index("--sandbox") + 1] == "workspace-write"
    assert writer_arguments[writer_arguments.index("--cd") + 1] == str(stage.resolve())
