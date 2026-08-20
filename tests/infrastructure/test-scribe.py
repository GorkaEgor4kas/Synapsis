# tests/infrastructure/test_scribe.py

"""Tests for the Scribe output composer."""

import pytest

from synapsis.infrastructure.scribe import Scribe


class MockLLM:
    """Fake LLM client for testing Scribe without API calls."""

    def __init__(self, response: str = "Formatted response"):
        self.response = response
        self.last_messages = None

    def invoke(self, messages):
        self.last_messages = messages
        return MockResponse(content=self.response)


class MockResponse:
    """Mimics LangChain response object."""

    def __init__(self, content: str):
        self.content = content


@pytest.fixture
def mock_llm():
    return MockLLM(response="## Search Results\n\nFound 2 notes")


@pytest.fixture
def scribe(mock_llm):
    return Scribe(llm_client=mock_llm)


def test_compose_returns_string(scribe):
    """Scribe returns the LLM-generated text."""
    result = scribe.compose(
        user_query="What notes do I have about ML?",
        agents_results={"librarian-v1": {"status": "success", "results": []}},
    )

    assert result == "## Search Results\n\nFound 2 notes"


def test_compose_sends_system_and_user_messages(scribe, mock_llm):
    """Scribe sends both a system prompt and user content."""
    scribe.compose(
        user_query="Test query",
        agents_results={"test": {"data": "value"}},
    )

    messages = mock_llm.last_messages

    # First message is system prompt
    assert messages[0].type == "system"
    assert "output formatter" in messages[0].content.lower()

    # Second message contains user query and results
    assert messages[1].type == "human"
    assert "Test query" in messages[1].content
    assert "test" in messages[1].content
    assert "value" in messages[1].content


def test_user_prompt_contains_agents_results(scribe):
    """The prompt includes all agent results as JSON."""
    prompt = scribe._build_user_prompt(
        user_query="Find notes",
        agents_results={
            "librarian-v1": {
                "status": "success",
                "results": [{"title": "Note 1"}],
            }
        },
    )

    assert "Find notes" in prompt
    assert "librarian-v1" in prompt
    assert "Note 1" in prompt
    assert "success" in prompt


def test_system_prompt_defines_rules(scribe):
    """System prompt includes formatting rules."""
    prompt = scribe._build_system_prompt()

    assert "Markdown" in prompt
    assert "never fabricate" in prompt.lower()
    assert "concise" in prompt.lower()