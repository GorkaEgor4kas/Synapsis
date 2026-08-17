# tests/test_blackboard.py

"""Tests for the Blackboard implementation."""

import time
import uuid

import pytest

from synapsis.blackboard.blackboard import Blackboard


@pytest.fixture
def blackboard():
    """Create a fresh Blackboard for each test."""
    session_id = str(uuid.uuid4())
    return Blackboard(session_id=session_id)


def test_put_and_get(blackboard):
    """Basic write and read."""
    key = blackboard.put(
        key="librarian-v1/task-001/results",
        value={"notes": ["note1.md", "note2.md"]},
        author="librarian-v1",
        entry_type="search_results",
    )

    assert key == "librarian-v1/task-001/results"
    result = blackboard.get(key)
    assert result == {"notes": ["note1.md", "note2.md"]}


def test_get_missing_key_returns_none(blackboard):
    """Reading a non-existent key returns None, not an error."""
    assert blackboard.get("nonexistent/key") is None


def test_list_keys_with_prefix(blackboard):
    """Prefix filtering works."""
    blackboard.put(
        key="librarian-v1/task-001/results",
        value={"data": "A"},
        author="librarian-v1",
        entry_type="search_results",
    )
    blackboard.put(
        key="coder-v1/task-002/script_v1",
        value={"code": "print('hello')"},
        author="coder-v1",
        entry_type="code_snippet",
    )

    librarian_keys = blackboard.list_keys(prefix="librarian-v1/")
    assert librarian_keys == ["librarian-v1/task-001/results"]

    all_keys = blackboard.list_keys()
    assert len(all_keys) == 2


def test_clear_prefix(blackboard):
    """Deleting entries by prefix."""
    blackboard.put(
        key="coder-v1/task-001/script_v1",
        value={"code": "v1"},
        author="coder-v1",
        entry_type="code_snippet",
    )
    blackboard.put(
        key="coder-v1/task-001/script_v2",
        value={"code": "v2"},
        author="coder-v1",
        entry_type="code_snippet",
    )
    blackboard.put(
        key="critic-v1/task-002/review",
        value={"verdict": "approved"},
        author="critic-v1",
        entry_type="review_notes",
    )

    deleted = blackboard.clear_prefix("coder-v1/")
    assert deleted == 2
    assert blackboard.list_keys() == ["critic-v1/task-002/review"]


def test_expiration(blackboard):
    """Entries with short TTL expire and return None."""
    key = blackboard.put(
        key="test/short_ttl",
        value={"data": "temporary"},
        author="test",
        entry_type="search_results",
        ttl_seconds=1,
    )

    assert blackboard.get(key) == {"data": "temporary"}

    time.sleep(1.1)

    assert blackboard.get(key) is None


def test_overwrite_key(blackboard):
    """Last write wins."""
    key = "test/key"
    blackboard.put(
        key=key,
        value={"version": 1},
        author="test",
        entry_type="code_snippet",
    )
    blackboard.put(
        key=key,
        value={"version": 2},
        author="test",
        entry_type="code_snippet",
    )

    result = blackboard.get(key)
    assert result == {"version": 2}


def test_session_stats(blackboard):
    """Stats reflect current state."""
    blackboard.put(
        key="lib/task-001/results",
        value={"data": "A"},
        author="librarian-v1",
        entry_type="search_results",
    )
    blackboard.put(
        key="coder/task-002/script",
        value={"code": "x"},
        author="coder-v1",
        entry_type="code_snippet",
    )

    stats = blackboard.get_session_stats()
    assert stats["total_entries"] == 2
    assert stats["entries_per_author"] == {
        "librarian-v1": 1,
        "coder-v1": 1,
    }