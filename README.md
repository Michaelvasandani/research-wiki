# ResearchOS Local MVP

Start the localhost-only shell from a clean checkout:

```sh
docker compose up --build
```

Open <http://localhost:8000>. Docker Compose publishes the application only on
`127.0.0.1`; no authentication is required for this single-user Local MVP.
Persistent application state is stored in the bind-mounted `./data` directory,
so it survives `docker compose restart` and container replacement.

The application invokes its AI worker as the configurable `CODEX_COMMAND` CLI
process. Compose defaults that command to the checked-in deterministic
`scripts/fake-codex`, so a clean checkout can exercise the worker boundary
without network access. It can provide progress and success output, or
controlled malformed output and failures with `FAKE_CODEX_MODE=malformed` or
`FAKE_CODEX_MODE=failure`. Set `CODEX_COMMAND` to a real Codex CLI command when
running the worker outside this deterministic test mode.

Run the public-boundary smoke tests locally with:

```sh
python -m pip install -e '.[dev]'
python -m pytest
```

For the complete manual acceptance smoke using an ordinarily authenticated real
Codex CLI and Obsidian, including the actual writer/chat permission profiles,
use [the real-Codex smoke guide](docs/manual-real-codex-smoke.md). The guide
uses the checked-in `scripts/real-codex` protocol adapter; bare `codex` is not
itself a ResearchOS worker command.
