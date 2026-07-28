# Blackboard Specification

**Version:** 1.0
**Date:** 2026-07-26
**Project:** Synapsis

---

## Overview

The Blackboard is a shared, ephemeral key-value store that enables indirect
communication between agents. Agents write intermediate results to the Blackboard
and read context from it. The Orchestrator coordinates by passing Blackboard key
references, not raw data.

## Design Principles

1. **Dumb store, smart agents.** The Blackboard has no logic — it stores and retrieves. Agents interpret.
2. **Session-scoped.** All entries belong to a session. When the session ends, entries are cleaned up.
3. **Namespaced keys.** Every key follows a convention that encodes provenance.
4. **Self-cleaning.** Entries have TTLs. Expired entries are removed on read and by periodic sweep.

---

## Key Convention

{producer}/{task_id}/{artifact_name}


### Components

| Part | Description | Example |
|------|-------------|---------|
| `producer` | Agent ID or service name that created the entry | `librarian-v1`, `coder-v1`, `researcher` |
| `task_id` | Task identifier from Orchestrator's plan | `task-001`, `task-002` |
| `artifact_name` | Descriptive name of the artifact | `ml_notes`, `script_v3`, `review_v3` |

### Examples

librarian-v1/task-001/linear_regression_notes
librarian-v1/task-001/ml_model_evaluation_notes
coder-v1/task-002/script_v1
coder-v1/task-002/script_v2
coder-v1/task-002/execution_result_v2
critic-v1/task-003/review_script_v1
critic-v1/task-003/review_script_v2
researcher/task-004/scikit_docs_raw
scribe/task-005/final_output_draft
planner/task-000/original_plan


### Reserved Prefixes

| Prefix | Purpose |
|--------|---------|
| `planner/` | Task decomposition plans |
| `scribe/` | Final output drafts |
| `system/` | Session metadata, configuration snapshots |

---

## Entry Schema

Each entry stored on the Blackboard:

```json
{
  "key": "librarian-v1/task-001/ml_notes",
  "value": {
    "results": [...],
    "query_interpretation": "..."
  },
  "author": "librarian-v1",
  "timestamp": "2026-07-26T14:30:00Z",
  "ttl_seconds": 3600,
  "entry_type": "search_results",
  "content_type": "application/json",
  "size_bytes": 2147,
  "session_id": "abc-123-def"
}