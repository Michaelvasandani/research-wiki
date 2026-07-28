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
        'printf "__CALL__\\n" >> "$RESEARCHOS_ADAPTER_ARGUMENTS"\n'
        'printf "%s\\n" "$@" >> "$RESEARCHOS_ADAPTER_ARGUMENTS"\n'
        "printf '%s\\n' "
        "'{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"ready\"}}'\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return executable


def run_adapter(tmp_path: Path, *arguments: str) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    argument_log = tmp_path / "arguments.txt"
    argument_log.unlink(missing_ok=True)
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


def recorded_calls(arguments: list[str]) -> list[list[str]]:
    return [
        call.splitlines()
        for call in "\n".join(arguments).split("__CALL__\n")
        if call
    ]


def test_real_codex_adapter_uses_supported_read_only_and_staged_writer_profiles(
    tmp_path: Path,
) -> None:
    probe, probe_arguments = run_adapter(tmp_path, "probe")

    stage = tmp_path / "stage"
    stage.mkdir()
    request = stage / "request.json"
    request.write_text(json.dumps({"staged_vault": str(stage)}), encoding="utf-8")
    writer, writer_arguments = run_adapter(tmp_path, "ingest", str(request))

    probe_calls = recorded_calls(probe_arguments)
    writer_calls = recorded_calls(writer_arguments)

    assert probe.returncode == writer.returncode == 0
    assert json.loads(probe.stdout.splitlines()[-1]) == {"type": "result", "output": "ready"}
    assert len(probe_calls) == 1
    assert probe_calls[0][:2] == ["exec", "--json"]
    assert "--ephemeral" in probe_calls[0]
    assert "--ask-for-approval" not in probe_calls[0]
    assert probe_calls[0][probe_calls[0].index("--sandbox") + 1] == "read-only"
    assert len(writer_calls) == 2
    for call in writer_calls:
        assert call[call.index("--sandbox") + 1] == "workspace-write"
        assert call[call.index("--cd") + 1] == str(stage.resolve())
    assert "reviewer" in "\n".join(writer_calls[1]).lower()
