```markdown
# ADR-001: Hierarchical Multi-Agent Architecture with Blackboard Pattern

**Status:** Draft
**Date:** 2026-07-25
**Project:** Synapsis

---

## Context

Synapsis is a multi-agent system that searches an Obsidian vault (via Memex RAG),
generates and reviews code in a sandbox, and supports voice I/O. The system has
four specialized agents plus infrastructure services.

The core challenge: how should agents share intermediate results without making
the Orchestrator a data bottleneck? In early sketches, all data flowed through
the Orchestrator, bloating its context window and making debugging difficult.

We have one developer (me), no production constraints yet, and the goal is a
portfolio project that demonstrates architectural thinking.

## Decision

We chose a hierarchical topology with a Blackboard pattern for data sharing.

- One Orchestrator agent decomposes tasks and routes them
- Three Core Agents (Librarian, Coder, Critic) execute specialized work
- Infrastructure services (Planner, Researcher, Scribe) are stateless utilities
- A Blackboard acts as shared scratchpad — agents write results, other agents read them
- Voice I/O is an external layer, not part of the agent system

## Alternatives Considered

### Option A: Orchestrator as data forwarder
All agent results flow through the Orchestrator, which forwards them to the next agent.
Rejected: Orchestrator context window grows with every task, harder to debug data provenance.

### Option B: Direct agent-to-agent messaging
Agents call each other directly without the Orchestrator.
Rejected: Tight coupling, hard to change agent topology later, no central supervision.

### Option C: Blackboard pattern (chosen)
Agents write to a shared board, read what they need.
Retains Orchestrator supervision, decouples agents, makes data flow traceable.

## Consequences

Easier:
- Testing agents in isolation (mock the Blackboard)
- Swapping agent implementations later
- Debugging (every artifact has a known key on the board)

Harder:
- Blackboard is a single point of state — must be reliable
- Agents need to know Blackboard key conventions (mitigated by namespacing)

Risks:
- Blackboard could grow large for long sessions (mitigated by TTL-based cleanup)

## References
- Memex: [https://github.com/GorkaEgor4kas/Memex]
- Mnemosys: [https://github.com/GorkaEgor4kas/Mnemosys]
- "Blackboard Pattern" — Buschmann et al., Pattern-Oriented Software Architecture
```