from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from src.agents.base import BaseAgent
from src.core.llm_client import LLMClient

if TYPE_CHECKING:
    from src.core.research_state import ResearchState


_SYSTEM_PROMPT = (Path(__file__).parent / "context_agent.md").read_text(encoding="utf-8")


class ContextAgent(BaseAgent):
    """Agent that explores background context for a query."""

    def __init__(self, llm_client: LLMClient, api_token: str | None = None) -> None:
        super().__init__(
            name="context",
            description="Explores background context, key concepts, and relevant frameworks",
        )
        self.llm_client = llm_client
        self.api_token = api_token

    async def execute(self, query: str, state: ResearchState | None = None, sub_question_index: int = 0) -> str:
        """Provide background context for the given query."""
        prompt = f"Query:\n\n{query}"
        result = await self.llm_client.generate(prompt, api_token=self.api_token, system=_SYSTEM_PROMPT)
        if state is not None:
            state.add_evidence(result, source=self.name, confidence=0.7, sub_question_index=sub_question_index)
        return result
