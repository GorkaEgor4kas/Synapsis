# tests/agents/test_base.py

"""Tests for the BaseAgent abstract class."""

import uuid
from typing import Any

import pytest

from synapsis.agents.base import AgentState, BaseAgent
from synapsis.blackboard.blackboard import Blackboard


class TestAgent(BaseAgent):
    """Minimal concrete agent for testing."""

    agent_id = "test-agent"
    capabilities = ["echo"]
    default_timeout_seconds = 10
    max_retries = 1

    def execute(self, task_input: dict[str, Any]) -> dict[str, Any]:
        task_id = task_input["task_id"]
        self._task_started(task_id)

        # Echo the input value as output
        value = task_input.get("value", "no-value")
        key = self._write_to_blackboard(
            task_id=task_id,
            artifact_name="echo_result",
            value={"echo": value},
            entry_type="search_results",
        )

        self._task_completed(task_id, success=True)

        return {
            "task_id": task_id,
            "status": "success",
            "blackboard_keys": [key],
        }


@pytest.fixture
def blackboard():
    return Blackboard(session_id=str(uuid.uuid4()))


@pytest.fixture
def agent(blackboard):
    return TestAgent(blackboard=blackboard, session_id=blackboard.session_id)


def test_agent_has_state(agent):
    """Every agent has an AgentState."""
    assert agent.state.agent_id == "test-agent"
    assert agent.state.status == "idle"


def test_execute_updates_state(agent):
    """Executing a task changes agent state."""
    result = agent.execute({"task_id": "task-001", "value": "hello"})

    assert result["status"] == "success"
    assert agent.state.status == "idle"
    assert agent.state.tasks_completed == 1
    assert agent.state.tasks_failed == 0


def test_write_to_blackboard_uses_convention(agent):
    """Blackboard keys follow {agent_id}/{task_id}/{artifact_name}."""
    key = agent._write_to_blackboard(
        task_id="task-001",
        artifact_name="test_artifact",
        value={"data": 42},
        entry_type="search_results",
    )

    assert key == "test-agent/task-001/test_artifact"
    assert agent.blackboard.get(key) == {"data": 42}


def test_blackboard_key_helper(agent):
    """_blackboard_key builds correct keys."""
    key = agent._blackboard_key("task-007", "result_v1")
    assert key == "test-agent/task-007/result_v1"


def test_send_result_message(agent):
    """_send_result constructs a valid task_result message."""
    msg = agent._send_result(
        task_id="task-001",
        status="success",
        blackboard_keys=["test-agent/task-001/result"],
        summary="Done",
        execution_time_ms=100.0,
    )

    assert msg.message_type.value == "task_result"
    assert msg.sender.value == "test-agent"
    assert msg.receiver.value == "orchestrator-v1"
    assert msg.payload["task_id"] == "task-001"
    assert msg.payload["status"] == "success"


def test_send_error_message(agent):
    """_send_error constructs a valid error message."""
    msg = agent._send_error(
        error_type="test_error",
        message="Something went wrong",
        task_id="task-001",
        recoverable=True,
    )

    assert msg.message_type.value == "error"
    assert msg.priority.value == "high"
    assert msg.payload["error_type"] == "test_error"
    assert msg.payload["recoverable"] is True


def test_cannot_instantiate_abstract(blackboard):
    """BaseAgent cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseAgent(blackboard=blackboard, session_id="test")