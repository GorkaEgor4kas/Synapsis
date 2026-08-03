# Database Schema

**Version** 1.0
**Date** 30.07.2026
**Project** Synapsis

---

# Overview

1. **Session persistence** — track user sessions, their status, and final responses
2. **Message logging** — record every message exchanged between components for full session replay and debugging
3. **Blackboard persistence** — optionally persist Blackboard entries for crash recovery and long-running sessions

SQLite was chosen because it requries no external deps., it's good for single user local tools, and was already used in Mnemosys before.

---

## Design Principles

1. **Single-file database.** One `.db` file per vault or per user config directory. No complex multi-file setups.
2. **Append-heavy, read-light.** Messages are written frequently during a session, read only for replay or debugging.
3. **Text foreign keys.** agent_id, session_id, and task_id are human-readable strings, not integer IDs. Makes debugging and export easier.
4. **JSON payloads.** The `payload` of messages and `value` of blackboard entries are stored as JSON text. SQLite's JSON functions can query them if needed.
5. **No ORM.** Direct SQL via `sqlite3` from Python stdlib. No SQLAlchemy dependency for a project this size.

---

## Columns desc. 
Column           |    Format   |  Desc
---
session_id          UUID         Unique identifier of the session
created_at          TEXT (ISO)   Session start timestamp
updated_at          TEXT (ISO)   Last activity timestamp
status              TEXT         Current session state. (active | non-active)
user_query          TEXT         The original user's query that started the session (may be Null)
final_response      Text         The completed text response shown to the user, that ended the session
summary_json        Text (JSON)  Aggregated execution summary. (Covers the list of agents been invoked, errors, timings, etc.)
vault_path          TEXT         Filesystem path to user's Obsidian vault (Alreday used in Mnemosys)
preferences_json    TEXT(JSON)   	Snapshot of user preferences at session start. Schema matches Orchestrator's preferences.



