# Synapsis Architecture

**Version:** 1.0
**Date:** 2026-07-30
**Project:** Synapsis

---

## What is Synapsis?

Synapsis is a multi-agent system that searches an Obsidian vault, generates and
reviews code in a sandbox, and supports voice input/output. It builds on two
existing projects: **Memex** (hybrid RAG search for Obsidian) and **Mnemosys**
(a single-agent system with tool use and memory).

Synapsis moves from one agent to several, giving each agent a specific role and
letting them collaborate through a shared Blackboard.

---
## Design Principles

1. **Agents decide, infrastructure executes.** Agents have decision loops (OODA/ReAct). Infrastructure services are pure functions: input in, output out.

2. **Orchestrator coordinates, doesn't carry.** The Orchestrator tells agents what to do but never passes data between them. Data flows through the Blackboard.

3. **Messages carry references, not payloads.** Task assignments and results reference Blackboard keys. Large data (search results, code, reviews) lives on the Blackboard.

4. **Voice is an adapter, not an agent.** The system operates on text. Voice I/O is a modality converter — swap it out without touching agent logic.

5. **Contracts before code.** Every agent has a JSON Schema contract defining its inputs, outputs, tools, timeouts, and retry policies.

---

## Component Catalog

### Orchestrator (Agent)

The central coordinator. Only component that communicates with all others.

**Responsibilities:**
- Decompose user queries into tasks (uses Planner)
- Route tasks to the right agent
- Monitor timeouts and retries
- Spawn and supervise Coder↔Critic debate loops
- Escalate deadlocks to the user
- Aggregate results into a final response

**Contract:** `docs/contracts/orchestrator.json`

---

### Librarian (Agent)

Knowledge retrieval specialist. Searches the user's Obsidian vault.

**Tools:** Hybrid search (BM25 + semantic), note retrieval, link exploration, tag/folder filtering

**Backed by:** Memex RAG system

**Contract:** `docs/contracts/librarian.json`

---

### Coder (Agent)

Code generation and sandbox execution. Generates code based on specifications and vault context, executes it in an isolated subprocess.

**Tools:** Code generation, sandbox execution, package installation (whitelisted), revision

**Security:** Subprocess isolation, temp directory confinement, resource limits, package whitelist

**Contract:** `docs/contracts/coder.json`

---

### Critic (Agent)

Code review specialist. Analyzes code for correctness, security, performance, and style. Participates in debate loops with Coder.

**Tools:** Code review, static analysis, test suggestion, security scan, version comparison

**Debate role:** Reviews Coder's output, returns verdict (approved/changes requested/rejected). Loops until approval or max rounds.

**Contract:** `docs/contracts/critic.json`

---

### Blackboard (Infrastructure)

Shared key-value store for intermediate results. The spine of inter-agent data flow.

**Key convention:** `{producer}/{task_id}/{artifact_name}`

**Interface:** `put()`, `get()`, `list_keys()`, `clear_prefix()`, `clear_session()`

**Spec:** `docs/design/blackboard-spec.md`

---

### Planner (Infrastructure)

Stateless task decomposition service. Takes a user query, returns a task DAG.

**Why infrastructure, not agent:** Planner is a single LLM call. No decision loop, no memory, no tools. Pure function.

---

### Researcher (Infrastructure)

Stateless web search utility. Fetches and caches web results.

**Why infrastructure, not agent:** Researcher doesn't decide when to search or what is relevant. It fetches raw results on demand.

---

### Scribe (Infrastructure)

Stateless output composer. Takes aggregated results from all agents and formats them into the final response. Also prepares voice scripts for TTS.

**Why infrastructure, not agent:** Scribe applies formatting rules. No decision-making about content or structure.

---

### Voice Listener (I/O Adapter)

Speech-to-text converter. Wraps Whisper (local) or Whisper API.

**Input:** Audio stream or file
**Output:** Transcribed text

---

### Voice Speaker (I/O Adapter)

Text-to-speech converter. Wraps Piper TTS (local) or ElevenLabs API.

**Input:** Voice script from Scribe
**Output:** Audio file

---

## Data Flow

### Without Blackboard (rejected)

User → Orchestrator → Librarian → Orchestrator → Coder → Orchestrator → Critic → Orchestrator → Scribe → User
↑ ↑ ↑
2000 words code + notes code + review
bloating context bloating context bloating context

text

### With Blackboard (chosen)
User → Orchestrator: "Search ML notes, write analysis script"

Orchestrator → Librarian: "Search. Write to board."
Librarian → Blackboard: librarian-v1/task-001/ml_notes

Orchestrator → Coder: "Generate code. Context on board."
Coder → Blackboard: coder-v1/task-002/script_v1

Orchestrator → Critic: "Review. Code on board."
Critic → Blackboard: critic-v1/task-003/review_v1

Orchestrator → Scribe: "Compose. Everything on board."
Scribe → Orchestrator: final_response

Orchestrator → User: [formatted response]

text

The Orchestrator never touches the data. It only passes Blackboard key references.

---

## Communication Rules

1. **Orchestrator assigns tasks.** No agent self-initiates work.
2. **Agents return results to Orchestrator.** Never to other agents.
3. **Coder↔Critic debate is the only P2P channel.** And it's spawned and supervised by the Orchestrator.
4. **All data goes through Blackboard.** Messages carry keys, not payloads.
5. **Every message has a UUID and timestamp.** Full session replay is possible.

**Full protocol:** `docs/design/message-protocol.md`

---

## Memory Architecture

| Type | Storage | Scope | Purpose |
|------|---------|-------|---------|
| **Working** | Agent context window | Private per agent | Current task reasoning |
| **Episodic** | SQLite (`sessions`, `messages`) | Shared, append-only | Session replay, debugging |
| **Semantic** | Memex RAG | Shared, read-only | Obsidian vault knowledge |
| **Scratchpad** | Blackboard (dict or Redis) | Shared, ephemeral | Intermediate results during a session |

**Database schema:** `docs/design/database-schema.md`

---

## Security Model (Code Execution)

Defense in depth for sandboxed code execution:

| Layer | Mechanism |
|-------|-----------|
| Process isolation | Separate subprocess |
| Filesystem isolation | Temp directory per execution |
| Resource limits | 120s timeout, 512MB memory |
| Package control | Whitelist (`numpy`, `pandas`, etc.) |
| Review gate | Critic reviews before execution (optional) |

**Full spec:** `docs/adr/adr-004-sandbox-security.md`

---

## Technology Stack

| Component | Technology | Reason |
|-----------|------------|--------|
| Orchestration | LangGraph | Supervisor agent pattern, state management |
| LLM | Groq / DeepSeek API | BYOK model, no server costs |
| RAG | Memex (custom) | Hybrid search (BM25 + FAISS + RRF) |
| Database | SQLite | Zero dependencies, single-user local tool |
| STT | Whisper (local) | Offline-capable, portfolio-friendly |
| TTS | Piper TTS (local) | Offline-capable, no API costs |
| Sandbox | Python subprocess | Stdlib only, no Docker dependency |
| Voice Activity | Silero VAD | Lightweight, local |
| Config | `.env` + `pyproject.toml` | Standard Python tooling |

---

## Project Structure
synapsis/
├── README.md
├── pyproject.toml
├── .env.example
├── Dockerfile
│
├── docs/
│ ├── architecture.md ← This file
│ ├── adr/ ← Architecture Decision Records
│ │ ├── README.md
│ │ ├── adr-001-system-architecture.md
│ │ ├── adr-002-communication-protocol.md
│ │ ├── adr-003-agent-vs-infrastructure.md
│ │ ├── adr-004-sandbox-security.md
│ │ └── adr-005-voice-io-layer.md
│ ├── contracts/ ← JSON Schema agent contracts
│ │ ├── orchestrator.json
│ │ ├── librarian.json
│ │ ├── coder.json
│ │ ├── critic.json
│ │ └── message-envelope.json
│ └── design/ ← Detailed design specs
│ ├── blackboard-spec.md
│ ├── message-protocol.md
│ └── database-schema.md
│
├── src/
│ └── synapsis/
│ ├── agents/
│ ├── blackboard/
│ ├── infrastructure/
│ ├── voice/
│ ├── persistence/
│ └── config/
│
└── tests/

text

---

## Key Design Decisions

| Decision | Rationale | ADR |
|----------|-----------|-----|
| Hierarchical + Blackboard topology | Prevents Orchestrator data bottleneck, decouples agents | ADR-001 |
| Agents vs infrastructure separation | Clear criteria: decision loop, state, tools | ADR-003 |
| Messages carry keys, not data | Keeps context windows clean, enables traceability | ADR-002 |
| Voice as I/O adapter | Decouples modality from reasoning | ADR-005 |
| Subprocess sandbox, not Docker | Simpler, no external deps, sufficient for portfolio | ADR-004 |
| SQLite, no ORM | Zero dependencies, fast enough for single-user | Database schema |
| Contracts before implementation | Interfaces are stable, implementations can change | All contracts |

---

## References

- **Memex:** RAG system for Obsidian hybrid search
- **Mnemosys:** Single-agent system with OODA loop and tool use
- **LangGraph:** Agent orchestration framework
- **Blackboard Pattern:** Buschmann et al., *Pattern-Oriented Software Architecture*

