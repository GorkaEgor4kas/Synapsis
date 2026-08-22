"""
Librarian agent - seraches the Obsidian vault via Memex (one of my previous projects)

The Librarian wraps MemexCore and exposes vault search as an agent
capability. It retrieves raw chunks and sources, writes them to the
Blackboard, and returns a task_result.

Librarian does NOT generate answers. It retrieves. Scribe composes.
This keeps retrieval and formatting cleanly separated

Link to Memex: https://github.com/GorkaEgor4kas/Memex
"""

from __future__ import annotations

import logging
import time
from typing import Any

from memex.core.core import MemexCore

from synapsis.agents.base import BaseAgent


#logging
logger = logging.getLogger(__name__)

class LibrarianAgent(BaseAgent):
    """
    Knowledge retrieval agent for Obsidian vault search

    Input (task_input):
        {
            "task_id": "task-001",
            "task_type": "search",
            "query": "linear regression",
            "num_results": 5,          # optional, defaults to 5
        }

    Output (task_result):
        {
            "task_id": "task-001",
            "status": "success" | "empty" | "failed",
            "results": [...],
            "sources": [...],
            "query_interpretation": str,
            "blackboard_keys": [...],
        }
    """

    agent_id = "librarian-v1"
    capabilities = [
        "search_vault",
        "retrieve_notes",
    ]
    default_timeout_seconds = 30
    max_retries = 2


    def __init__(
        self,
        blackboard,
        session_id: str,
        memex_core: MemexCore | None = None,
        **kwargs: Any
    ) -> None:
        """Initialize Librarian with a MemexCore instance

        Args:
            blackboard: Shared Blackboard for writing results.
            session_id: Current session identifier.
            memex_core: MemexCore instance. If None, creates a new one
            (lazy-loads models on first search).
        """
        super().__init__(blackboard=blackboard, session_id=session_id, **kwargs)
        self.memex = memex_core or MemexCore()

    def execute(self, task_input: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a search task.

        Args:
            task_input: Must contain task_id and query.

        Returns:
            Task result dict matching the Librarian's output schema.
        """

        task_id = task_input["task_id"]
        query  = task_input.get("query", "")
        num_results = task_input.get("num_results", 5)

        self._task_started(task_id=task_id)
        start_time = time.time()

        if not query:
            self._task_completed(task_id=task_id, success=False)
            return {
                "task_id": task_id,
                "status": "failed",
                "error": {
                    "error_type": "invalid_query",
                    "message": "Query is empty",
                },
            }

        try:
            memex_result = self.memex.search(query=query, offline=True)

            execution_time_ms = (time.time() - start_time) * 1000

            chunks = memex_result.get("chunks", [])
            sources = sorted(memex_result.get("sources", set()))

            if not chunks:
                self._task_completed(task_id=task_id, success=True)
                return {
                    "task_id": task_id,
                    "status": "success",
                    "results": [],
                    "sources": [],
                    "query_interpretation": query,
                    "blackboard_keys": [],
                    "execution_time_ms": execution_time_ms,
                }

            limited_chunks = chunks[:num_results]

            #write results to blackboard
            result_key = self._write_to_blackboard(
                task_id=task_id, 
                artifact_name="search_result",
                value={
                    "query": query,
                    "chunks": limited_chunks,
                    "sources": sources,
                    "total_found": len(chunks),
                },
                entry_type="search_results"
            )

            self._task_completed(task_id=task_id, success=True)

            return {
                "task_id": task_id,
                "status": "success",
                "results": limited_chunks,
                "sources": sources,
                "total_found": len(chunks),
                "query_interpretation": query,
                "blackboard_keys": [result_key],
                "execution_time_ms": execution_time_ms,
            }

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            logger.error("Librarian search failed for task %s: %s", task_id, e)

            self._task_completed(task_id=task_id, success=False)

            return {
                "task_id": task_id,
                "status": "failed",
                "error": {
                    "error_type": "memex_error",
                    "message": str(e),
                },
                "blackboard_keys": [],
                "execution_time_ms": execution_time_ms,
            }
        
