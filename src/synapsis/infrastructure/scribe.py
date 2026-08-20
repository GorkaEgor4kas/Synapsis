"""
Scribe is a LMM-povered output composer.

Takes raw agent results and composes them into clean, user-facing text.
Scribe is infrastructure, not an agent: it has no decision loop, no state,
and no tools. It makes one LLM call and returns the result.

The LLM does the heavy lifting here. Instead of maintaining templates for
every possible agent output combination, we let the model format the
response dynamically.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage


#logging 
logger = logging.getLogger(__name__)


class Scribe:
    """Formats raw agents data into user-facing markdown text"""
    def __init__(self, llm_client):
        """Initialize Scribe with an LLM client.

        Args:
            llm_client: Any LangChain-compatible chat model.
        Must have an .invoke() method.
        """
        self.llm_client = llm_client

    def compose(
        self,
        user_query: str,
        agents_results: dict[str, Any]
    ) -> str:
        
        """Compose a clean response from raw agent results.

        Args:
            user_query: The user's original question.
            agent_results: Dict mapping agent_id to their raw output.

        Returns:
            Markdown-formatted string ready for CLI display
        """

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(user_query, agents_results)

        logger.debug("Scribe composing response for query: %s", user_query[:100])

        response = self.llm_client.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )

        return response.content

    @staticmethod
    def _build_system_prompt() -> str:
        """The system prompt that defines Scribe's behavior"""
        return """
        You are the output formatter for Synapsis, a multi-agent system that searches an Obsidian vault and generates code.

        Your job: take raw results from agents and compose a clear, helpful response for the user.

        Rules:
        - Output in Markdown format
        - Be concise but complete — don't hide important information
        - Preserve technical accuracy — don't invent or modify search results
        - If results are empty, say so clearly and suggest what the user might try
        - If multiple agents contributed, organize their outputs logically
        - Use headers, lists, and formatting to improve readability
        - Always mention which notes from the vault were used (if any)
        - Never fabricate search results or code output
        - If the user asked a question, answer it directly using the results
        - If the results are partial or have errors, communicate that honestly
        """

    @staticmethod
    def _build_user_prompt(
        user_query: str,
        agents_results: dict[str, Any]
    ) -> str:
        """Build the user prompt containing the query and raw results"""
        import json

        results_json = json.dumps(agents_results, indent=2, default=str)

        return f"""
        User's original query: "{user_query}"

        Raw agent results:
        {results_json}

        Compose a response for the user based on the results above.
        """
    