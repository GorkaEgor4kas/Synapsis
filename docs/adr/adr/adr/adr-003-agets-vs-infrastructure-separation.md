# ADR-003: Agent vs Infrastructure Separation

**Status:** Draft
**Date:** 2026-07-26
**Project:** Synapsis

---

## Context

Synapsis has seven named components: Orchestrator, Librarian, Coder, Critic,
Planner, Researcher, Scribe, and a Blackboard. Not all of these should be agents.

During initial design, we considered making everything an agent — PlannerAgent,
ResearcherAgent, ScribeAgent. This would have been consistent but introduced
unnecessary complexity.

We needed criteria to decide: what makes something an agent vs a service?

## Decision

We classify components using three criteria:

| Criterion | Agent | Infrastructure Service |
|-----------|-------|----------------------|
| Has its own decision loop? | Yes (OODA/ReAct) | No (pure function) |
| Maintains session state? | Yes (working memory) | No (stateless) |
| Has tools it can invoke? | Yes | No (it *is* a tool) |

Applying these criteria:

**Agents (4):**
- **Orchestrator** — decides task decomposition, routes work, monitors progress
- **Librarian** — decides search strategy, relevance filtering
- **Coder** — decides implementation approach, debugs, revises
- **Critic** — decides review focus, severity classification

**Infrastructure Services (4):**
- **Planner** — query in, task DAG out. Stateless. Used by Orchestrator.
- **Researcher** — search query in, raw results out. Stateless.
- **Scribe** — raw results in, formatted output out. Stateless.
- **Blackboard** — key-value store. No logic at all.

**I/O Layer (2, outside both categories):**
- **Voice Listener** — audio in, text out
- **Voice Speaker** — text in, audio out

## Alternatives Considered

### Option A: Everything is an agent
All seven components have agent loops and tools.
Rejected: Planner doesn't need a decision loop — it's a single LLM call.
Giving it agent status means unnecessary context management, timeout handling,
and state tracking. Same for Researcher and Scribe.

### Option B: Everything is a tool on the Orchestrator
No separate agents. Orchestrator calls Planner, Researcher, Librarian as tools.
Rejected: Librarian, Coder, and Critic have complex multi-step workflows
that benefit from dedicated context windows. Flattening them into tools
would bloat the Orchestrator's context beyond manageable limits.

### Option C: Criteria-based separation (chosen)
Clear rules determine agent vs service. Simple to explain, easy to apply
to future components.

## Consequences

Easier:
- Testing: infrastructure services are pure functions — no mocking needed
- Reasoning: "does this component decide things?" is an intuitive test
- Onboarding: anyone reading the code can quickly see why something is classified as it is

Harder:
- Boundary policing: if Researcher starts filtering results intelligently,
  it's drifting toward agent behavior and should be reclassified
- Scribe might eventually need context awareness for complex formatting —
  if so, it can be promoted to agent in a future ADR

Risks:
- Low. The criteria are simple and the system is small enough that
  reclassification wouldn't be painful.

## References
- ADR-001: System Architecture
- OODA Loop pattern (used in Mnemosys agent)