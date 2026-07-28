# Message Protocol

**Version:** 1.0
**Date:** 2026-07-26
**Project:** Synapsis

---

## Overview

Synapsis components communicate through structured messages. Every message uses
a common envelope (defined in `message-envelope.json`). The message_type field
determines the payload schema and processing rules.

This document defines every message type, its payload schema, when it is sent,
and how the receiver must respond.

---

## Core Principles

1. **Messages carry references, not data.** Large payloads (search results, code,
   reviews) are written to the Blackboard. Messages carry Blackboard keys.

2. **Orchestrator is the hub.** All task assignments originate from the
   Orchestrator. All task results return to it. The only exception is the
   Coder↔Critic debate loop — and even that is spawned and supervised by the
   Orchestrator.

3. **Every message is traceable.** UUIDs on every message, correlation IDs linking
   related messages, reply chains via in_response_to. Full session replay is
   possible from the message log.

4. **Errors are messages, not exceptions.** When an agent fails, it sends an error
   message. The Orchestrator decides how to recover.

---

## Communication Topology

        ┌─────────────┐
        │ORCHESTRATOR │
        └────┬─┬─┬────┘
             │ │ │
┌────────────┘ │ └────────────┐
▼              ▼              ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│LIBRARIAN │ │  CODER   │ │  CRITIC  │
└──────────┘ └────┬─────┘ └────┬─────┘
│                 │
└────  debate ────┘
(spawned by Orchestrator,
bounded by max_rounds)


### Who Talks to Whom

| Sender | Receiver | Message Types |
|--------|----------|---------------|
| Orchestrator | Librarian, Coder, Critic | task_assignment |
| Orchestrator | Planner, Researcher, Scribe | task_assignment (infrastructure variant) |
| Librarian, Coder, Critic | Orchestrator | task_result, status_update, heartbeat, error |
| Coder | Critic | debate_proposal |
| Critic | Coder | debate_response |
| Critic | Orchestrator | debate_verdict |
| Orchestrator | System | escalation |
| Voice Listener | Orchestrator | task_result (transcribed text) |
| Orchestrator | Voice Speaker | task_assignment (speak this text) |
| Any agent | Orchestrator | error |

---

## Message Types

### 1. task_assignment

**Sent by:** Orchestrator
**Received by:** Any agent or infrastructure service
**Purpose:** Assign work. The receiver must acknowledge, execute, and return a task_result.

**Payload Schema:**

```json
{
  "task_id": "task-001",
  "task_type": "search",
  "description": "Human-readable description of the task",
  "agent_input": {
    "query": "linear regression fundamentals",
    "num_results": 5,
    "search_mode": "hybrid"
  },
  "context_blackboard_keys": [
    "planner/task-000/original_plan"
  ],
  "output_blackboard_key_prefix": "librarian-v1/task-001/",
  "timeout_seconds": 30,
  "dependencies": [],
  "retry_policy": {
    "max_retries": 2,
    "backoff_strategy": "linear"
  }
}


Field	Type	Required	Description
task_id	string	Yes	Unique task identifier. Format: task-XXX
task_type	string	Yes	Agent-specific task type (see each agent's contract)
description	string	Yes	Human-readable description for logging
agent_input	object	Yes	Input matching the agent's input_schema
context_blackboard_keys	array	No	Keys the agent should read before starting
output_blackboard_key_prefix	string	Yes	Prefix for keys where the agent writes output
timeout_seconds	integer	Yes	Max execution time before the Orchestrator considers this task failed
dependencies	array	No	task_ids that must complete before this task starts
retry_policy	object	No	Override for the agent's default retry policy
Receiver must:

Acknowledge receipt immediately (implicit — the Orchestrator assumes receipt unless an error is returned)

Read context from Blackboard keys if provided

Execute the task

Write results to Blackboard using the output key prefix

Return a task_result message

2. task_result
Sent by: Any agent or infrastructure service
Received by: Orchestrator
Purpose: Report task completion, partial results, or failure.

Payload Schema:
{
  "task_id": "task-001",
  "status": "success",
  "blackboard_keys": [
    "librarian-v1/task-001/linear_regression_notes",
    "librarian-v1/task-001/ml_evaluation_notes"
  ],
  "summary": "Found 3 relevant notes on linear regression. Wrote results to 2 Blackboard entries.",
  "execution_time_ms": 1234,
  "error": null
}

Field	Type	Required	Description
task_id	string	Yes	The task this result is for
status	string	Yes	success, partial, empty, failed, timeout
blackboard_keys	array	Yes	Keys where output was written (empty if failed)
summary	string	Yes	Human-readable summary for logs and user display
execution_time_ms	number	Yes	Wall-clock time spent on this task
error	object	No	Present only if status is failed or timeout

Error sub-schema:
{
  "error_type": "agent_timeout",
  "message": "Librarian search exceeded 30 second timeout",
  "recoverable": true,
  "details": {}
}

Field	Type	Description
error_type	string	Machine-readable error code
message	string	Human-readable error description
recoverable	boolean	Can the Orchestrator retry this task?
details	object	Additional error context
Orchestrator must:

Log the result

Check status: if success or partial, proceed to next task. If failed or timeout, apply retry policy or escalate.

If the task had dependents, check if they can now proceed.

3. status_update
Sent by: Any agent during long-running tasks
Received by: Orchestrator
Purpose: Inform the Orchestrator of progress without completing the task. Used for user-facing progress indicators.

Payload Schema:
{
  "task_id": "task-002",
  "update_type": "progress",
  "message": "Generating code... 60% complete",
  "elapsed_time_ms": 45000,
  "estimated_remaining_ms": 30000,
  "progress_percent": 60
}


Field	Type	Required	Description
task_id	string	Yes	The task being updated
update_type	string	Yes	progress, blocked, waiting_for_context
message	string	Yes	Human-readable status
elapsed_time_ms	number	Yes	Time spent so far
estimated_remaining_ms	number	No	Estimated time to completion
progress_percent	integer	No	0-100 if determinable
Orchestrator must:

Log the update

Optionally display to user if the task is user-visible

Check if elapsed time exceeds the task timeout

4. debate_proposal
Sent by: Coder
Received by: Critic
Purpose: Submit code for review during a debate loop. This is the only direct agent-to-agent message type.

Payload Schema:
{
  "debate_id": "debate-001",
  "task_id": "task-002",
  "round": 2,
  "max_rounds": 5,
  "code_blackboard_key": "coder-v1/task-002/script_v2",
  "specification_blackboard_key": "librarian-v1/task-001/spec_notes",
  "execution_result_blackboard_key": "coder-v1/task-002/execution_result_v2",
  "changes_summary": "Added input validation and fixed the null check on line 23 as requested in round 1."
}


Field	Type	Required	Description
debate_id	string	Yes	Unique identifier for this debate
task_id	string	Yes	The parent task
round	integer	Yes	Current round number (1-indexed)
max_rounds	integer	Yes	Maximum rounds before forced resolution
code_blackboard_key	string	Yes	Where the code to review is stored
specification_blackboard_key	string	No	Where the original spec is stored
execution_result_blackboard_key	string	No	Where execution results are stored
changes_summary	string	Yes	What changed since the previous version
Critic must:

Read code and context from Blackboard

Perform review

Return a debate_response within the debate timeout

5. debate_response
Sent by: Critic
Received by: Coder (with copy to Orchestrator)
Purpose: Return review results during a debate loop.

Payload Schema:
{
  "debate_id": "debate-001",
  "round": 2,
  "review_blackboard_key": "critic-v1/task-003/review_script_v2",
  "verdict": "changes_requested",
  "critical_issues_count": 0,
  "major_issues_count": 1,
  "minor_issues_count": 2,
  "unresolved_from_previous_rounds": [],
  "debate_stance": "almost_there",
  "can_continue": true
}


Field	Type	Required	Description
debate_id	string	Yes	The debate this responds to
round	integer	Yes	Current round number
review_blackboard_key	string	Yes	Where the full review is stored
verdict	string	Yes	approved, approved_with_suggestions, changes_requested, rejected
critical_issues_count	integer	Yes	Number of critical-severity issues
major_issues_count	integer	Yes	Number of major-severity issues
minor_issues_count	integer	Yes	Number of minor-severity issues
unresolved_from_previous_rounds	array	Yes	Issue IDs still not resolved from earlier rounds
debate_stance	string	Yes	needs_major_changes, needs_minor_changes, almost_there, acceptable, cannot_approve_current_approach
can_continue	boolean	Yes	Can the debate productively continue? False triggers escalation.
Coder must:

If verdict is approved or approved_with_suggestions: stop and return final code to Orchestrator.

If verdict is changes_requested and can_continue is true: revise code and send a new debate_proposal.

If can_continue is false: stop and let the Orchestrator resolve.

Orchestrator must:

Monitor debate progress

If can_continue is false, or max_rounds is reached, or debate_timeout expires: send debate_verdict to resolve.

6. debate_verdict
Sent by: Orchestrator
Received by: Coder and Critic
Purpose: Force resolution of a debate. Sent when the debate loop must end.

Payload Schema:
{
  "debate_id": "debate-001",
  "resolution": "accept_coder_version",
  "reason": "max_rounds_reached",
  "final_code_blackboard_key": "coder-v1/task-002/script_v2",
  "message": "Debate ended after 5 rounds. Using Coder's latest version."
}


Field	Type	Required	Description
debate_id	string	Yes	The debate being resolved
resolution	string	Yes	accept_coder_version, accept_critic_demands, escalate_to_user
reason	string	Yes	max_rounds_reached, deadlock_detected, debate_timeout, user_intervention
final_code_blackboard_key	string	Yes	Which code version is accepted
message	string	Yes	Explanation for logs

7. escalation
Sent by: Orchestrator
Received by: System (displayed to user)
Purpose: Pause the system and ask the user to make a decision.

Payload Schema:
{
  "escalation_id": "esc-001",
  "session_id": "abc-123",
  "task_id": "task-002",
  "debate_id": "debate-001",
  "escalation_reason": "debate_deadlock",
  "summary": "Coder and Critic disagree on error handling approach after 4 rounds. Both approaches are valid but incompatible.",
  "options": [
    {
      "id": "opt-1",
      "label": "Accept Coder's approach (try/except with logging)",
      "consequence": "Code will be generated with Coder's error handling style. Less safe but simpler."
    },
    {
      "id": "opt-2",
      "label": "Accept Critic's suggestion (explicit validation functions)",
      "consequence": "Code will be rewritten with separate validation. More robust but more code."
    },
    {
      "id": "opt-3",
      "label": "Skip code generation",
      "consequence": "Task will be marked as cancelled. Explanation of the tradeoff will be shown instead."
    }
  ],
  "timeout_seconds": 300,
  "default_option": "opt-1"
}



Field	Type	Required	Description
escalation_id	string	Yes	Unique identifier
session_id	string	Yes	Session context
task_id	string	No	The task that triggered escalation
debate_id	string	No	The debate that triggered escalation, if applicable
escalation_reason	string	Yes	debate_deadlock, agent_timeout, dangerous_operation_requested, irreversible_action
summary	string	Yes	What happened and what the user needs to decide
options	array	Yes	2-4 options for the user
timeout_seconds	integer	Yes	How long to wait for user input before using default
default_option	string	Yes	Which option to use if the user doesn't respond

8. heartbeat
Sent by: Any agent during long-running operations
Received by: Orchestrator
Purpose: Signal that the agent is still alive and working. Prevents false timeout detection.

Payload Schema:

{
  "agent_id": "coder-v1",
  "agent_status": "executing",
  "current_task_id": "task-002",
  "elapsed_time_ms": 45000,
  "estimated_remaining_ms": 30000
}

Field	Type	Required	Description
agent_id	string	Yes	Who is sending the heartbeat
agent_status	string	Yes	idle, executing, waiting_for_context, recovering
current_task_id	string	No	Currently executing task
elapsed_time_ms	number	Yes	Time since task started
estimated_remaining_ms	number	No	Estimated time to completion
Orchestrator must:

Update the agent's last-seen timestamp

If no heartbeat is received for 2x the heartbeat interval, consider the agent timed out

Heartbeat interval: 10 seconds default. Configurable per agent.

9. error
Sent by: Any component
Received by: Orchestrator
Purpose: Report an unexpected error that is not tied to a specific task.

Payload Schema:

{
  "error_type": "blackboard_unavailable",
  "agent_id": "librarian-v1",
  "task_id": null,
  "message": "Cannot write to Blackboard: connection refused",
  "recoverable": false,
  "suggested_action": "restart_session",
  "stack_trace": "Traceback...",
  "timestamp": "2026-07-26T14:35:00Z"
}

Field	Type	Required	Description
error_type	string	Yes	Machine-readable error code
agent_id	string	Yes	Who encountered the error
task_id	string	No	Related task, if any
message	string	Yes	Human-readable description
recoverable	boolean	Yes	Can the system continue without intervention?
suggested_action	string	Yes	retry, skip_task, restart_session, shutdown
stack_trace	string	No	Full stack trace for debugging
timestamp	string	Yes	When the error occurred
Orchestrator must:

Log the error

If recoverable: retry or skip the affected task

If not recoverable: escalate to user or shut down gracefully

Message Flow Examples
Example 1: Simple Search

Orchestrator → Librarian:
  message_type: task_assignment
  payload: { task_id: "task-001", task_type: "search", ... }

Librarian → Blackboard:
  write: "librarian-v1/task-001/ml_notes"

Librarian → Orchestrator:
  message_type: task_result
  payload: { task_id: "task-001", status: "success", blackboard_keys: [...] }

Example 2: Code Generation with Debate (Happy Path)
Orchestrator → Coder:
  message_type: task_assignment
  payload: { task_id: "task-002", task_type: "generate_and_execute" }

Coder → Blackboard:
  write: "coder-v1/task-002/script_v1"

Coder → Critic:
  message_type: debate_proposal
  correlation_id: "debate-001"
  payload: { round: 1, code_blackboard_key: "coder-v1/task-002/script_v1" }

Critic → Blackboard:
  write: "critic-v1/task-003/review_script_v1"

Critic → Coder:
  message_type: debate_response
  correlation_id: "debate-001"
  payload: { round: 1, verdict: "changes_requested", major_issues_count: 2 }

Coder → Blackboard:
  write: "coder-v1/task-002/script_v2"

Coder → Critic:
  message_type: debate_proposal
  correlation_id: "debate-001"
  payload: { round: 2, code_blackboard_key: "coder-v1/task-002/script_v2" }

Critic → Blackboard:
  write: "critic-v1/task-003/review_script_v2"

Critic → Coder + Orchestrator:
  message_type: debate_response
  correlation_id: "debate-001"
  payload: { round: 2, verdict: "approved", critical_issues_count: 0, major_issues_count: 0 }

Coder → Orchestrator:
  message_type: task_result
  payload: { task_id: "task-002", status: "success", blackboard_keys: ["coder-v1/task-002/script_v2"] }

Example 3: Debate Deadlock → Escalation
[Debate continues for 4 rounds without resolution...]

Critic → Coder + Orchestrator:
  message_type: debate_response
  correlation_id: "debate-001"
  payload: { round: 4, verdict: "changes_requested", can_continue: false, debate_stance: "cannot_approve_current_approach" }

Orchestrator → System:
  message_type: escalation
  payload: {
    escalation_reason: "debate_deadlock",
    summary: "Coder and Critic disagree after 4 rounds...",
    options: [...]
  }

[System waits for user input...]

User selects option → Orchestrator resumes with user's choice

Error Recovery Patterns
Agent Timeout
Orchestrator sends task_assignment with timeout_seconds=30

30 seconds pass, no task_result or heartbeat received

Orchestrator marks task as timed out

If retries remain: Orchestrator resends task_assignment (possibly with a different agent or simplified input)

If no retries remain: Orchestrator sends escalation to user

Agent Crash (Detected via Missing Heartbeat)
Agent sends heartbeat every 10 seconds

20 seconds pass with no heartbeat

Orchestrator considers the agent dead

Orchestrator reassigns the task (if possible) or escalates

Blackboard Unavailable
Agent tries to write to Blackboard, gets an error

Agent sends error message to Orchestrator

Orchestrator enters degraded mode: tasks that require Blackboard are paused

Orchestrator escalates to user: "Blackboard is unavailable. Restart session?"

Irrecoverable Error
Any component sends error message with recoverable=false

Orchestrator logs the full error

Orchestrator sends final task_result with status=failed

Orchestrator returns partial results to user with error explanation

Session continues (user can ask a new question) but the failed task is not retried

Versioning
This is version 1.0 of the message protocol. All messages include the protocol
version implicitly through the message envelope schema $id field.

Backward-incompatible changes require a new schema $id (e.g.,
message-envelope-v2.json) and a new ADR.

References
docs/contracts/message-envelope.json — JSON Schema for the message envelope

ADR-002: Agent Communication Protocol

ADR-001: System Architecture (Blackboard pattern)
