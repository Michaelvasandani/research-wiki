# 01 — Run the Local MVP shell

**What to build:** A localhost-only ResearchOS application that starts with one Docker Compose command, exposes the Library, Research, Wiki, and Graph areas, persists its file-based state, and can exercise the production-shaped Codex process boundary with a deterministic fake.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] One documented Docker Compose command starts the application and its required local services from a clean checkout.
- [ ] The application binds to localhost and requires no authentication for the Local MVP.
- [ ] Library, Research, Wiki, and Graph are reachable through a coherent server-rendered navigation shell.
- [ ] Application state survives a container restart through bind-mounted file storage.
- [ ] The application invokes Codex through a configurable CLI process boundary rather than a direct model API.
- [ ] Automated tests can substitute a deterministic fake Codex executable through the same process boundary.
- [ ] The fake can emit controlled progress, successful output, malformed output, and failure exit states without network access.
- [ ] A public-boundary smoke test verifies startup, navigation, persistence, and fake-Codex availability.
