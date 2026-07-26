```markdown
# ADR-002: Agent Communication Protocol

**Status:** Draft
**Date:** 2026-07-26
**Project:** Synapsis

---

## Context

Synapsis has multiple components — agents and infrastructure services — that need
to exchange data during a session. ADR-001 established the Blackboard pattern for
data sharing, but we still need to define:

1. How the Orchestrator assigns tasks to agents
2. How agents report results back
3. How the Coder-Critic debate loop works
4. What message format all components understand

Without a shared protocol, every agent would implement its own communication style,
making the system fragile and hard to debug.

## Decision

We define two communication channels with distinct purposes:

### Channel 1: Orchestrator - Agent (Task Assignment)

The Orchestrator assigns work via structured task messages. Agents respond with result messages. This is a request-response pattern.

**Task Assignment Message:**
- `message_type: "task_assignment"`
- Contains: task_id, assigned_agent, task_description, references to Blackboard keys for context
- Agent acknowledges receipt, then execute, then posts resutl

**Task Result Message:**
- `message_type: "task_result"`
- Contains: task_id, status (success/partial/failed), Blackboard keys where output was written, error info if failed


### Channel 2: Agent - Blackboard (Data Sharing)

Agents write intermediate results to the Blackboard. Other agents read from it when the Orchestrator tells them to. The Orchestrator never carries data - it only passes Blackboard key references.

**Key Convention:** `{producer_agent}/{task_id}/{artifact_name}`

Examples:
- `librarian/task-001/linear_regression_notes`
- `coder/task-002/script_v3`
- `critic/task-002/review_script_v3`

### Coder-Critic Debate

This is the only A2A communication. It is spawned and  supervised by the Orchestrator, bounded by max_rounds, and uses a structured debate format.

1. Coder writes code to Blackboard
2. Orchestrator notifies Critic "review `coder/task-X/script_vN`"
3. Critic writes review to Blackboard 
4. If changes requested: Orchestrator notifies Coder, loop cont.
5. If approved or reached max_rounds limit - debate ends, Orchestrator proceeds.

### Message Envelope Schema

All messages use a common envelope:

{
    message_id: UUID,
    session_id: str,
    sender: agent_id,
    receiver: agent_id | "blackboard" | "orchestrator",
    timestamp: ISO,
    message_type: "task_assignment" | "task_result" | "status_update" |"debate_proposal" | "debate_response" | "escalation",
    payloads: object,
    correlation_id: UUID (links related messages)
}

## Alternatives Considered

### Option A: Direct function calls between agents
Agents import each other and call methods directly.
Rejected: Tight coupling, impossible to change agent implementations independently,
no traceability — can't log or replay communication.

### Option B: Central message queue (RabbitMQ/Redis pub-sub)
All communication through a dedicated message broker.
Rejected: Overengineered for a single-process system. Adds infrastructure complexity
without benefit at this scale. The Blackboard provides sufficient decoupling.

### Option C: Envelope schema + Blackboard (chosen)
Structured messages for task assignment, Blackboard for data sharing.
Simple to implement (dicts + JSON), traceable (every message has an ID and timestamp),
easy to upgrade to a message queue later if needed.

## Consequences

Easier:
- Debugging: every message has a UUID and timestamp, full session replay is possible
- Testing: mock the message envelope, test agents in isolation
- Future-proofing: the envelope schema can wrap different transports (HTTP, Redis, gRPC)

Harder:
- Message schema must be versioned if it evolves (mitigated: single developer, can break things)
- Debate loop requires careful timeout handling to prevent infinite Coder↔Critic cycles

Risks:
- Payload size could grow large (mitigated: large data goes to Blackboard, messages only carry references)

## References
- ADR-001: System Architecture (Blackboard pattern)
- JSON Schema specification: https://json-schema.org/
```