"""Durable Obsidian-save tracking for the published Markdown vault."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
from threading import Event, Lock, Thread
import time


PAGE_DIRECTORIES = ("papers", "topics", "analyses")
_ANNOTATION_START = re.compile(
    rb"## Researcher annotations\r?\n<!-- researcher-annotations:start -->"
)
_ANNOTATION_END = re.compile(rb"<!-- researcher-annotations:end -->")


def managed_page_bytes(contents: bytes) -> bytes | None:
    """Return the AI-managed portion, or ``None`` for an invalid page boundary."""

    starts = list(_ANNOTATION_START.finditer(contents))
    ends = list(_ANNOTATION_END.finditer(contents))
    if len(starts) != 1 or len(ends) != 1 or ends[0].start() < starts[0].end():
        return None
    trailing = contents[ends[0].end() :]
    if trailing.strip(b"\r\n"):
        return None
    return contents[: starts[0].start()]


@dataclass(frozen=True)
class PageConflict:
    path: str
    detected_at: str


class PageConflictStore:
    """A small durable record of pages that automatic writers must not touch."""

    def __init__(self, runtime_dir: Path) -> None:
        self.path = runtime_dir / "page-conflicts.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def conflicts(self) -> list[PageConflict]:
        with self._lock:
            return self._read()

    def add(self, paths: list[str]) -> None:
        with self._lock:
            recorded = {conflict.path: conflict for conflict in self._read()}
            detected_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            for path in paths:
                recorded.setdefault(path, PageConflict(path, detected_at))
            self._write(list(recorded.values()))

    def resolve(self, path: str) -> bool:
        """Resume writers only after the researcher explicitly resolves a conflict."""

        with self._lock:
            recorded = self._read()
            remaining = [conflict for conflict in recorded if conflict.path != path]
            if len(remaining) == len(recorded):
                return False
            self._write(remaining)
            return True

    def conflicted_paths(self, paths: list[str]) -> list[str]:
        conflicted = {conflict.path for conflict in self.conflicts()}
        return sorted(path for path in paths if path in conflicted)

    def _read(self) -> list[PageConflict]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        conflicts = data.get("conflicts") if isinstance(data, dict) else None
        if not isinstance(conflicts, list):
            return []
        result: list[PageConflict] = []
        for conflict in conflicts:
            if (
                isinstance(conflict, dict)
                and isinstance(conflict.get("path"), str)
                and isinstance(conflict.get("detected_at"), str)
            ):
                result.append(PageConflict(conflict["path"], conflict["detected_at"]))
        return sorted(result, key=lambda conflict: conflict.path)

    def _write(self, conflicts: list[PageConflict]) -> None:
        temporary = self.path.with_suffix(".pending")
        temporary.write_text(
            json.dumps(
                {
                    "conflicts": [
                        {"path": conflict.path, "detected_at": conflict.detected_at}
                        for conflict in sorted(conflicts, key=lambda conflict: conflict.path)
                    ]
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)


class ObsidianWatcher:
    """Poll a local vault and turn completed page saves into researcher commits."""

    def __init__(
        self,
        vault: Path,
        conflicts: PageConflictStore,
        *,
        debounce_seconds: float = 0.15,
        poll_seconds: float = 0.03,
    ) -> None:
        self.vault = vault
        self.conflicts = conflicts
        self.debounce_seconds = debounce_seconds
        self.poll_seconds = poll_seconds
        self._stop = Event()
        self._thread: Thread | None = None
        self._pending_since: float | None = None
        self._pending_fingerprint: tuple[tuple[str, int, int], ...] | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = Thread(target=self._run, name="obsidian-watcher", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None

    def _run(self) -> None:
        while not self._stop.wait(self.poll_seconds):
            try:
                paths = self._changed_page_paths()
                fingerprint = self._fingerprint(paths)
                if not paths:
                    self._pending_since = None
                    self._pending_fingerprint = None
                    continue
                if fingerprint != self._pending_fingerprint:
                    self._pending_fingerprint = fingerprint
                    self._pending_since = time.monotonic()
                    continue
                if (
                    self._pending_since is not None
                    and time.monotonic() - self._pending_since >= self.debounce_seconds
                ):
                    self._commit_researcher_save(paths)
                    self._pending_since = None
                    self._pending_fingerprint = None
            except OSError:
                # The vault pointer can be atomically replaced while a writer publishes.
                self._pending_since = None
                self._pending_fingerprint = None

    def _changed_page_paths(self) -> list[str]:
        if not self.vault.exists() or self._head() is None:
            return []
        changed = self._git("diff", "--name-only", "HEAD", "--")
        return sorted(
            path
            for path in changed.splitlines()
            if self._is_tracked_page(path)
        )

    def _is_tracked_page(self, path: str) -> bool:
        candidate = Path(path)
        return (
            candidate.suffix == ".md"
            and len(candidate.parts) == 2
            and candidate.parts[0] in PAGE_DIRECTORIES
            and self._git_result("ls-files", "--error-unmatch", "--", path).returncode == 0
        )

    def _fingerprint(self, paths: list[str]) -> tuple[tuple[str, int, int], ...]:
        return tuple(
            (
                path,
                (self.vault / path).stat().st_mtime_ns if (self.vault / path).exists() else 0,
                (self.vault / path).stat().st_size if (self.vault / path).exists() else 0,
            )
            for path in paths
        )

    def _commit_researcher_save(self, paths: list[str]) -> None:
        managed_edits = [path for path in paths if self._is_managed_edit(path)]
        if managed_edits:
            self.conflicts.add(managed_edits)
        message = (
            "researcher edit: managed content conflict"
            if managed_edits
            else "researcher edit: annotations"
        )
        self._git("add", "--", *paths)
        result = self._git_result(
            "-c",
            "user.name=Researcher",
            "-c",
            "user.email=researcher@local.invalid",
            "commit",
            "--only",
            "-m",
            message,
            "--",
            *paths,
        )
        if result.returncode and "nothing to commit" not in result.stderr:
            raise OSError(result.stderr.strip())

    def _is_managed_edit(self, path: str) -> bool:
        baseline = subprocess.run(
            ["git", "-C", str(self.vault), "show", f"HEAD:{path}"],
            check=False,
            capture_output=True,
        )
        if baseline.returncode:
            return True
        page = self.vault / path
        if not page.exists():
            return True
        current = page.read_bytes()
        previous_managed = managed_page_bytes(baseline.stdout)
        current_managed = managed_page_bytes(current)
        return (
            previous_managed is None
            or current_managed is None
            or previous_managed != current_managed
        )

    def _head(self) -> str | None:
        result = self._git_result("rev-parse", "--verify", "HEAD")
        return result.stdout.strip() if result.returncode == 0 else None

    def _git(self, *arguments: str) -> str:
        result = self._git_result(*arguments)
        if result.returncode:
            raise OSError(result.stderr.strip())
        return result.stdout

    def _git_result(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.vault), *arguments],
            check=False,
            capture_output=True,
            text=True,
        )
