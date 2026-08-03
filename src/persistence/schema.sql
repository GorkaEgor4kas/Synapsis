-- Synapsis Database Schema v1
-- SQLite 3.35+

-- Track applied migrations
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- User conversation sessions
CREATE TABLE IF NOT EXISTS sessions(
    session_id      TEXT PRIMARY KEY,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'completed', 'failed', 'cancelled')),
    user_query      TEXT,
    final_response  TEXT,
    summary_json    TEXT,
    vault_path      TEXT,
    preferences_json TEXT
);

-- All inter-component messages
CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id      TEXT NOT NULL UNIQUE,
    session_id      TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    sender          TEXT NOT NULL,
    receiver        TEXT NOT NULL,
    message_type    TEXT NOT NULL
                    CHECK (message_type IN (
                        'task_assignment', 'task_result', 'status_update',
                        'debate_proposal', 'debate_response', 'debate_verdict',
                        'escalation', 'heartbeat', 'error'
                    )),
    payload_json    TEXT NOT NULL,
    correlation_id  TEXT,
    in_response_to  TEXT,
    priority        TEXT NOT NULL DEFAULT 'normal'
                    CHECK (priority IN ('low', 'normal', 'high', 'critical')),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_correlation ON messages(correlation_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(session_id, timestamp);

-- Optional Blackboard persistence
CREATE TABLE IF NOT EXISTS blackboard_entries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    key             TEXT NOT NULL,
    value_json      TEXT NOT NULL,
    author          TEXT NOT NULL,
    timestamp       TEXT NOT NULL DEFAULT (datetime('now')),
    ttl_seconds     INTEGER NOT NULL DEFAULT 3600,
    entry_type      TEXT NOT NULL
                    CHECK (entry_type IN (
                        'search_results', 'code_snippet', 'execution_result',
                        'review_notes', 'task_plan', 'final_output', 'web_cache',
                        'session_metadata'
                    )),
    size_bytes      INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_blackboard_session ON blackboard_entries(session_id);
CREATE INDEX IF NOT EXISTS idx_blackboard_key ON blackboard_entries(session_id, key);

-- Seed the schema version
INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (1, datetime('now'));