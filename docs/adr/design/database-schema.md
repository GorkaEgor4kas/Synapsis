# Database Schema

**Version:** 1.0  
**Date:** 2026-07-30  
**Project:** Synapsis

---

## Overview

The database serves three purposes:

1. **Session persistence** — track user sessions, their status, and final responses
2. **Message logging** — record every message exchanged between components for full session replay and debugging
3. **Blackboard persistence** — optionally persist Blackboard entries for crash recovery and long-running sessions

SQLite was chosen because it requires no external dependencies, is good for single-user local tools, and was already used in Mnemosys before.

---

## Design Principles

1. **Single-file database.** One `.db` file per vault or per user config directory. No complex multi-file setups.
2. **Append-heavy, read-light.** Messages are written frequently during a session, read only for replay or debugging.
3. **Text foreign keys.** `session_id`, `message_id`, and `task_id` are human-readable strings, not integer IDs. Makes debugging and export easier.
4. **JSON payloads.** The `payload` of messages and `value` of blackboard entries are stored as JSON text. SQLite's JSON functions can query them if needed.
5. **No ORM.** Direct SQL via `sqlite3` from Python stdlib. No SQLAlchemy dependency for a project this size.

---

## Table: `sessions`

Tracks each user conversation session.

| Column | Type | Description |
|--------|------|-------------|
| `session_id` | TEXT PRIMARY KEY | UUID, unique identifier of the session |
| `created_at` | TEXT NOT NULL | ISO-8601 timestamp, session start |
| `updated_at` | TEXT NOT NULL | ISO-8601 timestamp, last activity (message, heartbeat, etc.) |
| `status` | TEXT NOT NULL | Current session state: `active`, `completed`, `failed`, `cancelled` |
| `user_query` | TEXT | The original user query that started the session. Null if session was created but no query sent yet. |
| `final_response` | TEXT | The completed text response shown to the user. Null until session completes. |
| `summary_json` | TEXT | Aggregated execution summary as JSON. Includes: agents invoked, errors encountered, total time, debate rounds. Schema matches Orchestrator's `execution_summary`. Null until session completes. |
| `vault_path` | TEXT | Filesystem path to the Obsidian vault used in this session |
| `preferences_json` | TEXT | Snapshot of user preferences at session start. Schema matches Orchestrator's `preferences` input. |

### Example Row

session_id: abc-123-def
created_at: 2026-07-30T14:00:00Z
updated_at: 2026-07-30T14:05:23Z
status: completed
user_query: Write a Python script that analyzes my ML notes
final_response: # Analysis Script\n\nHere is your script...\n\nhttps://graph.png
summary_json: {"total_time_ms": 320000, "agents_invoked": ["librarian-v1", "coder-v1", "critic-v1"], "errors_encountered": 0, "debates_spawned": 1}
vault_path: /home/user/ObsidianVault
preferences_json: {"code_execution_enabled": true, "voice_output_enabled": false, "max_sandbox_timeout_seconds": 120}

---

## Table: `messages`

Records every message exchange between components. Enables full session replay and debugging.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-increment, internal row ID |
| `message_id` | TEXT NOT NULL UNIQUE | UUID from the message envelope |
| `session_id` | TEXT NOT NULL | References `sessions.session_id` |
| `timestamp` | TEXT NOT NULL | ISO-8601, when the message was created |
| `sender` | TEXT NOT NULL | Agent ID or component name |
| `receiver` | TEXT NOT NULL | Agent ID or component name |
| `message_type` | TEXT NOT NULL | `task_assignment`, `task_result`, `status_update`, `debate_proposal`, `debate_response`, `debate_verdict`, `escalation`, `heartbeat`, `error` |
| `payload_json` | TEXT NOT NULL | Full message payload as JSON |
| `correlation_id` | TEXT | UUID linking related messages together |
| `in_response_to` | TEXT | `message_id` this message replies to |
| `priority` | TEXT | `low`, `normal`, `high`, `critical` (default: `normal`) |

### Indexes

```sql
CREATE INDEX idx_messages_session ON messages(session_id);
CREATE INDEX idx_messages_correlation ON messages(correlation_id);
CREATE INDEX idx_messages_timestamp ON messages(session_id, timestamp);
```

### Example row

id: 42
message_id: msg-111-aaa
session_id: abc-123-def
timestamp: 2026-07-30T14:01:00Z
sender: orchestrator-v1
receiver: librarian-v1
message_type: task_assignment
payload_json: {"task_id":"task-001","task_type":"search","description":"Search vault for ML notes",...}
correlation_id: corr-task-001
in_response_to: null
priority: normal

## Table: `blackboard_entries`

Optional persistence of Blackboard state. Useful for crash recovery and inspecting sessions after they end.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER PRIMARY KEY` | `Auto-increment` |
| `session_id` | `INTEGER NOT NULL` | `References sessions.session_id` |
| `key` | `TEXT NOT NULL` | `Blackboard key (e.g., librarian-v1/task-001/ml_notes)` |
| `value_json` | `TEXT NOT NULL` | `The stored value as JSON` |
| `author` | `TEXT NOT NULL` | `Agent ID that wrote the entry` |
| `timestamp` | `TEXT NOT NULL` | `ISO-8601, The stored value as JSON` |
| `ttl_seconds` | `INTEGER NOT NULL` | `Time-to-live in seconds from timestamp` |
| `entry_type` | `TEXT NOT NULL` | `search_results, code_snippet, execution_result, review_notes, task_plan, final_output, web_cache` |
| `size_bytes` | `INTEGER` | `Approximate size of value_json` |

### Indexes
```sql
CREATE INDEX idx_blackboard_session ON blackboard_entries(session_id);
CREATE INDEX idx_blackboard_key ON blackboard_entries(session_id, key);
```

### Example row

id: 7
session_id: abc-123-def
key: librarian-v1/task-001/ml_notes
value_json: {"results":[...],"query_interpretation":"..."}
author: librarian-v1
timestamp: 2026-07-30T14:01:03Z
ttl_seconds: 3600
entry_type: search_results
size_bytes: 2147

### Query Patterns

## Get full session history (for replay)

```sql
SELECT * FROM messages 
WHERE session_id = ? 
ORDER BY timestamp ASC;
```

### Get all messages in a debate

```sql
SELECT * FROM messages 
WHERE correlation_id = ? 
ORDER BY timestamp ASC;
```

### Get Blackboard state at a point in time

```sql
SELECT key, value_json, author, entry_type 
FROM blackboard_entries 
WHERE session_id = ? 
  AND timestamp <= ? 
  AND (timestamp + ttl_seconds) > ?;
```

### List recent sessions

```sql
SELECT session_id, created_at, status, user_query 
FROM sessions 
ORDER BY created_at DESC 
LIMIT 20;
```

### Get session summary

```sql
SELECT session_id, status, user_query, final_response, summary_json 
FROM sessions 
WHERE session_id = ?;
File Location
```

The database file is stored at:

``` text
~/.synapsis/sessions.db
``` 

Or, if a vault-specific database is preferred: 

```text
{vault_path}/.synapsis/sessions.db
```

The config directory approach (~/.synapsis/) is the default because it keeps the database outside the vault, avoiding accidental sync conflicts if the user syncs their vault with Git or Obsidian Sync.

## What This Schema Does NOT Cover
- User accounts or auth. Single-user local tool. No login, no multi-tenancy.

- Vector embeddings. Memex handles embedding storage separately. Synapsis only references Memex.

- Configuration. User preferences are stored in a .env file or config.yaml, not the database. The preferences_json column is a snapshot, not the source of truth.

- Analytics or telemetry. No tracking. The database exists purely for the system to function.

## References
- ADR-001: System Architecture

- ADR-002: Communication Protocol

- docs/design/blackboard-spec.md

-  docs/contracts/message-envelope.json
