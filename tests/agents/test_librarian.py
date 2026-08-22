# tests/agents/test_librarian.py

"""Tests for the Librarian agent."""

import uuid

import pytest

from synapsis.agents.librarian.librarian import LibrarianAgent
from synapsis.blackboard.blackboard import Blackboard


class MockMemex:
    """Fake MemexCore for testing without a real vault."""

    def __init__(self, chunks=None, should_fail=False):
        self.chunks = chunks or []
        self.should_fail = should_fail
        self.last_query = None
        self.last_offline = None

    def search(self, query: str, offline: bool = False) -> dict:
        self.last_query = query
        self.last_offline = offline

        if self.should_fail:
            raise RuntimeError("Memex index not built")

        if not self.chunks:
            return {
                "status": "empty",
                "chunks": [],
                "answer": None,
                "sources": set(),
            }

        sources = set()
        for chunk in self.chunks:
            source = chunk.get("metadata", {}).get("source_file", "unknown.md")
            sources.add(source)

        return {
            "status": "chunks",
            "chunks": self.chunks,
            "answer": None,
            "sources": sources,
        }


@pytest.fixture
def blackboard():
    return Blackboard(session_id=str(uuid.uuid4()))


@pytest.fixture
def sample_chunks():
    return [
        {
            "text": "Linear regression models the relationship between variables.",
            "metadata": {
                "source_file": "ML/Linear Regression.md",
                "chunk_id": 1,
            },
            "score": 0.92,
        },
        {
            "text": "R² score measures how well the model fits the data.",
            "metadata": {
                "source_file": "ML/Model Evaluation.md",
                "chunk_id": 1,
            },
            "score": 0.78,
        },
    ]


def test_search_success(blackboard, sample_chunks):
    """Librarian returns results and writes to Blackboard."""
    memex = MockMemex(chunks=sample_chunks)
    librarian = LibrarianAgent(
        blackboard=blackboard,
        session_id=blackboard.session_id,
        memex_core=memex,
    )

    result = librarian.execute(
        {
            "task_id": "task-001",
            "query": "linear regression",
        }
    )

    assert result["status"] == "success"
    assert result["total_found"] == 2
    assert len(result["results"]) == 2
    assert "ML/Linear Regression.md" in result["sources"]

    # Check Blackboard
    bb_key = result["blackboard_keys"][0]
    bb_value = blackboard.get(bb_key)
    assert bb_value["query"] == "linear regression"
    assert len(bb_value["chunks"]) == 2


def test_search_empty(blackboard):
    """Librarian returns empty status when no chunks found."""
    memex = MockMemex(chunks=[])
    librarian = LibrarianAgent(
        blackboard=blackboard,
        session_id=blackboard.session_id,
        memex_core=memex,
    )

    result = librarian.execute(
        {
            "task_id": "task-002",
            "query": "nonexistent topic",
        }
    )

    assert result["status"] == "empty"
    assert result["results"] == []
    assert result["blackboard_keys"] == []


def test_search_error(blackboard):
    """Librarian handles Memex failures gracefully."""
    memex = MockMemex(should_fail=True)
    librarian = LibrarianAgent(
        blackboard=blackboard,
        session_id=blackboard.session_id,
        memex_core=memex,
    )

    result = librarian.execute(
        {
            "task_id": "task-003",
            "query": "anything",
        }
    )

    assert result["status"] == "failed"
    assert result["error"]["error_type"] == "memex_error"


def test_empty_query(blackboard):
    """Librarian fails on empty query."""
    memex = MockMemex()
    librarian = LibrarianAgent(
        blackboard=blackboard,
        session_id=blackboard.session_id,
        memex_core=memex,
    )

    result = librarian.execute(
        {
            "task_id": "task-004",
            "query": "",
        }
    )

    assert result["status"] == "failed"
    assert result["error"]["error_type"] == "invalid_query"


def test_uses_offline_mode(blackboard, sample_chunks):
    """Librarian always calls Memex with offline=True."""
    memex = MockMemex(chunks=sample_chunks)
    librarian = LibrarianAgent(
        blackboard=blackboard,
        session_id=blackboard.session_id,
        memex_core=memex,
    )

    librarian.execute(
        {
            "task_id": "task-005",
            "query": "test",
        }
    )

    assert memex.last_offline is True


def test_num_results_limits_output(blackboard, sample_chunks):
    """Librarian respects num_results limit."""
    memex = MockMemex(chunks=sample_chunks)
    librarian = LibrarianAgent(
        blackboard=blackboard,
        session_id=blackboard.session_id,
        memex_core=memex,
    )

    result = librarian.execute(
        {
            "task_id": "task-006",
            "query": "linear regression",
            "num_results": 1,
        }
    )

    assert result["total_found"] == 2  # Memex found 2
    assert len(result["results"]) == 1  # But we only return 1


def test_state_updated_after_search(blackboard, sample_chunks):
    """Agent state reflects task completion."""
    memex = MockMemex(chunks=sample_chunks)
    librarian = LibrarianAgent(
        blackboard=blackboard,
        session_id=blackboard.session_id,
        memex_core=memex,
    )

    librarian.execute(
        {
            "task_id": "task-007",
            "query": "test",
        }
    )

    assert librarian.state.status == "idle"
    assert librarian.state.tasks_completed == 1
    assert librarian.state.tasks_failed == 0