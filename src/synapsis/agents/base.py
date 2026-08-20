"""
Abstract base class for all Synapsis agents

Implements the agent criteria from ADR-003:
- Agents have a decision loop (execute method)
- Agents maintain state (self.state)
- Agents have tools they can invoke (self.tools)

Scribe, Planner and Researcher are not included.
"""

from __future__ import annotations

import logging
import uuid 
from abc import ABC, abstractmethod
from typing import Any

from synapsis.blackboard.blackboard import Blackboard
from synapsis.messaging.envelope import MessageEnvelope, MessageType, Priority, Sender

#logging
logger = logging.getLogger(__name__)


class AgentState:
    """
    Current state of an agent during a session

    Tracks what agent is working on, whether it's available, and the last task is completed.
    """

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        self.status: str = "idle" # | executing | waiting | recovering
        self.current_task_id: str = None
        self.last_activity: float = 0.0
        self.tasks_completed: int = 0
        self.tasks_failed: int = 0

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize state for the status updates
        """
        return {
            "agent_id": self.agent_id,
            "status": self.status,
            "current_task_id": self.current_task_id,
            "last_activity": self.last_activity,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed
        }

    def __repr__(self):
        return f"AgentState(agent_id={self.agent_id!r}, status={self.status!r})"


class BaseAgent(ABC):
    """
    Abstract base class for all Synapsis agents.
    """

    agent_id: str
    capabilities: list[str] = []
    default_timeout_seconds: int = 30
    max_retries: int = 2

    def __init__(
        self,
        blackboard: Blackboard,
        session_id: str,
        **kwargs: Any
    ) -> None:
        self.blackboard = blackboard
        self.session_id = session_id
        self.state = AgentState(self.agent_id)
        self.config = kwargs

    @abstractmethod
    def execute(self, task_input: dict[str, Any]) -> dict[str, Any]:
        """Execute a task and return the result.

        This is the agent's decision loop. The Orchestrator calls this
        with a task_input matching the agent's input_schema (from its
        JSON Schema contract), and expects a task_result matching the
        agent's output_schema.

        Args:
            task_input: Task assignment data. Must contain at minimum:
                - task_id: str
                - task_type: str
                Plus agent-specific fields.

        Returns:
            Task result dict. Must contain at minimum:
                - status: success | partial | empty | failed | timeout
                - task_id: str
                Plus agent-specific fields.
        """
        ...

    def _task_started(self, task_id: str) -> None:
        """Mark the agent as busy with a new task"""
        import time

        self.state.status = "executing"
        self.state.current_task_id = task_id
        self.state.last_activity = time.time()
        logger.debug(
            "Agent %s started task %s",
            self.agent_id,
            task_id
        )

    def _task_completed(self, task_id: str, success: bool = True) -> None:
        """Mark the agent as idle and record the task outcome"""
        import time

        self.state.status = "idle"
        self.state.current_task_id = None
        self.state.last_activity = time.time()

        if success:
            self.state.tasks_completed += 1
        else:
            self.state.tasks_failed += 1


        logger.debug(
            "Agent %s completed task %s (success=%s)",
            self.agent_id,
            task_id,
            success
        )

    def _send_heartbeat(self, task_id: str) -> MessageEnvelope:
        """Send a heartbeat message to the Orchestrator
        
        Used during long-running tasks to prevent false timeout detection.
        """

        return MessageEnvelope.create(
            session_id=self.session_id,
            sender=self.agent_id,
            message_type=MessageType.HEARTBEAT,
            receiver=Sender.ORCHESTRATOR,
            payload={
                "agent_id":self.agent_id,
                "agent_status":self.state.status,
                "current_task_id": task_id,
                "elapsed_time_ms": 0
            }
        )

    def _send_result(
        self,
        task_id: str,
        status: str,
        blackboard_keys: list[str],
        summary: str,
        execution_time_ms: float,
        error: dict[str, Any] | None = None
    ) -> MessageEnvelope:
        """Construct a task_result message to send it to the Orchestrator."""

        payload = {
            "task_id": task_id,
            "status": status,
            "blackboard_keys": blackboard_keys,
            "summary": summary,
            "execution_time_ms": execution_time_ms
        }

        if error:
            payload["error"] = error

        return MessageEnvelope(
            session_id=self.session_id,
            sender=self.agent_id,
            receiver=Sender.ORCHESTRATOR,
            message_type=MessageType.TASK_RESULT,
            payload=payload,
            priority=Priority.HIGH if status == "failed" else Priority.NORMAL
        )

    def _send_error(
        self,
        error_type: str,
        message: str,
        task_id: str | None = None,
        recoverable: bool = True
    ) -> MessageEnvelope:
        """Construct an error message to send to the Orchestrator."""

        return MessageEnvelope(
            session_id=self.session_id,
            sender=self.agent_id,
            receiver=Sender.ORCHESTRATOR,
            message_type=MessageType.ERROR,
            payload={
                "error_type": error_type,
                "agent_id": self.agent_id,
                "task_id": task_id,
                "message": message,
                "recoverable": recoverable,
                "suggested_action": "retry" if recoverable else "skip_task"
            },
            priority=Priority.HIGH
        )

    def _blackboard_key(
        self,
        task_id: str,
        artifact_name: str
    ) -> str:
        """Build a Blackboard key using the standard convention.

        Convention: {agent_id}/{task_id}/{artifact_name}
        """
        return f"{self.agent_id}/{task_id}/{artifact_name}"


    def _write_to_blackboard(
        self,
        task_id: str,
        artifact_name: str,
        value: Any,
        entry_type: str,
    ) -> str:
        """Write a result to the Blackboard and return the key."""


        key = self._blackboard_key(task_id, artifact_name)
        self.blackboard.put(
            key=key,
            value=value,
            author=self.agent_id,
            entry_type=entry_type
        )

        return key


    def _read_from_blackboard(self, key: str) -> Any | None:
        """Read a value from the Blackboard"""
        return self.blackboard.get(key)


    def _new_correlation_id(self) -> str:
        """Generate a correlation ID for linking related messages"""
        return str(uuid.uuid4())


    # ------ Dunder methods ------
    def __repr__(self) ->str:
        return f"{self.__class__.__name__}(agent_id={self.agent_id!r})"

    
