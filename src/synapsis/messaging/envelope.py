"""Message envelope for all inter-component communication.

Implements the schema defined in docs/contracts/message-envelope.json.
Every message in Synapsis — task assignments, results, debates, errors —
uses this envelope.
"""

from __future__ import annotations

import uuid 
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """All valid message types in Synapsis."""

    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    STATUS_UPDATE = "status_update"
    DEBATE_PROPOSAL = "debate_proposal"
    DEBATE_RESPONSE = "debate_response"
    DEBATE_VERDICT = "debate_verdict"
    ESCALATION = "escalation"
    HEARTBEAT = "heartbeat"
    ERROR = "error"


class Priority(str, Enum):
    """Message priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class Sender(str, Enum):
    """Valid sender/receiver identifiers."""

    ORCHESTRATOR = "orchestrator-v1"
    LIBRARIAN = "librarian-v1"
    CODER = "coder-v1"
    CRITIC = "critic-v1"
    PLANNER = "planner"
    RESEARCHER = "researcher"
    SCRIBE = "scribe"
    VOICE_LISTENER = "voice-listener"
    VOICE_SPEAKER = "voice-speaker"
    SYSTEM = "system"
    TEST = "test-agent"


class MessageEnvelope(BaseModel):
    """Standard envelope for all Synapsis messages.

    Large data payloads are never carried in messages. Instead, messages
    carry Blackboard keys that reference the actual data.
    """

    message_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this message",
    )

    session_id: str = Field(
        description="Session this message belongs to",
    )

    sender: Sender = Field(
        description="Component that sent this message",
    )

    receiver: Sender = Field(
        description="Component that should receive this message",
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="ISO-8601 timestamp when message was created",
    )

    message_type: MessageType = Field(
        description="Determines how the payload should be processed",
    )

    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Message-type-specific payload",
    )

    correlation_id: str | None = Field(
        default=None,
        description="Links related messages (e.g., all messages in a debate)",
    )

    in_response_to: str | None = Field(
        default=None,
        description="message_id this message is replying to",
    )
    priority: Priority = Field(
        default=Priority.NORMAL,
        description="Processing priority",
    )

    @classmethod
    def create(
        cls,
        session_id: str,
        sender: Sender | str,
        receiver: Sender | str,
        message_type: MessageType | str,
        payload: dict[str, Any] | None = None,
        **kwargs: Any,
    )-> MessageEnvelope:
        """Factory method that accepts strings or enums.

        Usage:
            msg = MessageEnvelope.create(
                session_id="abc-123",
                sender="orchestrator-v1",
                receiver="librarian-v1",
                message_type="task_assignment",
                payload={"task_id": "task-001"},
            )
        """
        return cls(
            session_id=session_id,
            sender=Sender(sender),
            receiver=Sender(receiver),
            message_type=MessageType(message_type),
            payload=payload or {},
            **kwargs,
        )

    def to_json(self) -> str:
        """Serialize to JSON string for storage or transport."""
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "MessageEnvelope":
        """Deserialize from JSON string."""
        return cls.model_validate_json(json_str)
