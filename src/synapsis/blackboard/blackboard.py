"""Shared scratchpad for inter-agent data exchange.

Implements the Blackboard pattern defined in docs/design/blackboard-spec.md.
Agents write intermediate results here, other agents read from it.
The Orchestrator passes Blackboard key references, never raw data.

Local implementation: thread-safe Python dict.
Cloud implementation (future): Redis with the same interface.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BlackboardEntry:
    """A single entry on the Blackboard."""

    key: str
    value: Any
    author: str
    timestamp: float
    ttl_seconds: int
    entry_type: str
    session_id: str


class Blackboard:
    """Thread-safe key-value store with TTL-based expiration.

    Interface:
        put(key, value, author, entry_type, ttl_seconds=None) -> str
        get(key) -> Any | None
        list_keys(prefix=None) -> list[str]
        clear_prefix(prefix) -> int
        clear_session() -> int
        get_session_stats() -> dict
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._store: dict[str, BlackboardEntry] = {}
        self._lock = threading.Lock()

    def put(
        self,
        key: str,
        value: Any,
        author: str,
        entry_type: str,
        ttl_seconds: int | None = None,
    ) -> str:
        """Write a value to the Blackboard. Returns the key.

        If the key already exists, it is overwritten (last write wins).
        """
        if ttl_seconds is None:
            ttl_seconds = self._default_ttl(entry_type)

        entry = BlackboardEntry(
            key=key,
            value=value,
            author=author,
            timestamp=time.time(),
            ttl_seconds=ttl_seconds,
            entry_type=entry_type,
            session_id=self.session_id,
        )

        with self._lock:
            self._store[key] = entry

        return key

    def get(self, key: str) -> Any | None:
        """Read a value from the Blackboard.

        Returns None if the key doesn't exist or the entry has expired.
        Expired entries are deleted lazily on read.
        """
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None

            if self._is_expired(entry):
                del self._store[key]
                return None

            return entry.value

    def list_keys(self, prefix: str | None = None) -> list[str]:
        """List all keys, optionally filtered by prefix.

        Examples:
            list_keys("librarian-v1/")  # all Librarian entries
            list_keys("coder-v1/task-002/")  # all versions for task-002
        """
        with self._lock:
            self._cleanup_expired_locked()

            if prefix is None:
                return sorted(self._store.keys())

            return sorted(k for k in self._store if k.startswith(prefix))

    def clear_prefix(self, prefix: str) -> int:
        """Delete all entries matching a prefix. Returns count deleted."""
        with self._lock:
            keys_to_delete = [k for k in self._store if k.startswith(prefix)]
            for key in keys_to_delete:
                del self._store[key]
            return len(keys_to_delete)

    def clear_session(self) -> int:
        """Delete all entries for the current session. Returns count."""
        with self._lock:
            count = len(self._store)
            self._store.clear()
            return count

    def get_session_stats(self) -> dict[str, Any]:
        """Return statistics about the current Blackboard state."""
        with self._lock:
            self._cleanup_expired_locked()

            entries_per_author: dict[str, int] = {}
            entries_per_type: dict[str, int] = {}
            total_entries = len(self._store)

            for entry in self._store.values():
                entries_per_author[entry.author] = (
                    entries_per_author.get(entry.author, 0) + 1
                )
                entries_per_type[entry.entry_type] = (
                    entries_per_type.get(entry.entry_type, 0) + 1
                )

            return {
                "session_id": self.session_id,
                "total_entries": total_entries,
                "entries_per_author": entries_per_author,
                "entries_per_type": entries_per_type,
            }

    def _is_expired(self, entry: BlackboardEntry) -> bool:
        """Check if an entry has expired based on timestamp + ttl."""
        return (entry.timestamp + entry.ttl_seconds) < time.time()

    def _cleanup_expired_locked(self) -> int:
        """Remove all expired entries. Must be called with lock held."""
        expired_keys = [
            key
            for key, entry in self._store.items()
            if self._is_expired(entry)
        ]
        for key in expired_keys:
            del self._store[key]
        return len(expired_keys)

    @staticmethod
    def _default_ttl(entry_type: str) -> int:
        """Default TTL values per entry type (from blackboard-spec.md)."""
        defaults = {
            "search_results": 3600,
            "code_snippet": 1800,
            "execution_result": 1800,
            "review_notes": 1800,
            "task_plan": 3600,
            "final_output": 3600,
            "web_cache": 7200,
            "session_metadata": 86400,
        }
        return defaults.get(entry_type, 3600)