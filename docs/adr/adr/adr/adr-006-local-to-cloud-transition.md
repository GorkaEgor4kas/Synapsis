# ADR-006: Local-First Architecture with Cloud Transition Path

**Status:** Accepted
**Date:** 2026-07-30
**Project:** Synapsis

---

## Context

Synapsis is a portfolio project built by a solo developer without production
experience. The immediate goal is a local CLI tool that demonstrates architectural
thinking. However, a secondary goal is to showcase DevOps skills by eventually
deploying the system to the cloud.

We needed to design the system so that:
- Local development is simple (one process, no external services)
- Cloud deployment is possible without rewriting core components
- The transition can happen incrementally, not as a big-bang migration

The question: **what abstractions do we put in place now to make cloud deployment
straightforward later, without over-engineering the local version?**

## Decision

We design every shared component behind an interface, and implement the simplest
version first. The interface stays the same; the implementation can be swapped.

### Component Interfaces and Their Implementations

| Component | Interface | Local Implementation | Cloud Implementation |
|-----------|-----------|---------------------|---------------------|
| **Blackboard** | `put()`, `get()`, `list_keys()`, `clear_prefix()` | Python `dict` with `threading.Lock` | Redis (same operations map to `SET`, `GET`, `SCAN`, `DEL`) |
| **Database** | SQL via `sqlite3` module | SQLite file at `~/.synapsis/sessions.db` | PostgreSQL or Cloud SQL (same SQL schema, different connection) |
| **Voice STT** | `transcribe(audio) → text` | Whisper local model | Whisper API |
| **Voice TTS** | `synthesize(text) → audio` | Piper TTS local | ElevenLabs API |
| **LLM** | `chat(messages) → response` | Groq/DeepSeek API | Same (already cloud-native) |
| **Message Transport** | `send(message_envelope) → response` | In-process function call | HTTP or gRPC (message envelope schema is unchanged) |
| **Sandbox** | Subprocess with resource limits | `subprocess.run()` in temp dir | Docker container per execution |
| **User Interface** | `input() → text`, `text → output()` | CLI (Click/Typer) | FastAPI + web frontend |

### Key Principle: Data Flow Doesn't Change

Whether local or cloud, the flow is identical:

User Input → Orchestrator → Agent → Blackboard → Agent → Scribe → User Output


The Orchestrator still delegates tasks. Agents still read and write to the
Blackboard. Messages still use the same envelope schema. The only difference
is *where each component runs* and *which implementation backs each interface*.

### Incremental Transition Path

We do not attempt to build the cloud version now. Instead, we define a path
where each step is independently valuable:

1. **Phase 1: Single-process CLI.** All components in one Python process.
   Dict Blackboard. SQLite. Subprocess sandbox. CLI input. This is the MVP.

2. **Phase 2: Dockerized local.** `docker-compose` with Synapsis + Redis.
   Redis replaces dict Blackboard. Everything else stays the same. Proves
   the Blackboard abstraction works with a real backend.

3. **Phase 3: Web API.** FastAPI wraps the Orchestrator. REST endpoints for
   queries and sessions. Agents still run in the same process. Proves the
   system works behind an API without changing agent logic.

4. **Phase 4: Distributed agents.** Agents run in separate containers.
   Message transport switches from in-process calls to HTTP. Blackboard is
   Redis (already proven in Phase 2). Database is PostgreSQL.

5. **Phase 5: Full cloud deployment.** Deploy to Railway, Render, or fly.io.
   Managed Redis, managed Postgres, cloud STT/TTS APIs. CI/CD pipeline.

## Alternatives Considered

### Option A: Build for the cloud from day one
Docker, Redis, PostgreSQL, separate services for everything from the start.
Rejected: Too much complexity for a solo developer building a portfolio project.
Setting up Redis and Postgres just to test a search agent is overkill. Would
slow down development significantly.

### Option B: Build local-only with no cloud considerations
Dict Blackboard hardcoded everywhere, SQLite-specific queries, no abstraction
layer at all.
Rejected: Would require rewriting core components for cloud deployment. The
goal is to demonstrate DevOps thinking, so a migration path should exist.

### Option C: Interface-first with simple local implementations (chosen)
Define interfaces. Implement the simplest version. Swap later.
The overhead is minimal — an extra `blackboard.py` module with a clean API
instead of using raw dicts everywhere. The benefit is a documented, achievable
cloud path that demonstrates forward thinking to employers.

## Consequences

Easier:
- Local development: one process, no Docker, no Redis, no cloud accounts needed
- Testing: mock the Blackboard interface, test agents in isolation
- Portfolio narrative: "I designed this for local use with a documented path to cloud deployment"

Harder:
- Interface discipline: must not use dict-specific methods (like `.keys()` directly)
  on the Blackboard — always go through the interface
- Voice: local Whisper and Piper require model downloads and CPU time. Cloud APIs
  cost money. The abstraction means supporting both configs.

Risks:
- The interface might not be a perfect abstraction. Redis `SCAN` is not identical
  to `list_keys()`. Mitigation: the Blackboard spec defines exact semantics, and
  Phase 2 validates the Redis implementation early.
- Subprocess sandbox and Docker sandbox have different security properties.
  Mitigation: ADR-004 already documents these differences and their tradeoffs.

## References

- ADR-001: System Architecture (Blackboard pattern)
- ADR-002: Communication Protocol (message envelope)
- ADR-004: Sandbox Security Model
- ADR-005: Voice I/O as External Layer
- `docs/design/blackboard-spec.md`
- `docs/contracts/message-envelope.json`

