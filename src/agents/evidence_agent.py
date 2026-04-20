from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.base import BaseAgent
from src.core.llm_client import LLMClient

if TYPE_CHECKING:
    from src.core.research_state import ResearchState


class EvidenceAgent(BaseAgent):
    """Agent that searches for direct evidence related to a query."""

    def __init__(self, llm_client: LLMClient, api_token: str | None = None) -> None:
        super().__init__(
            name="evidence",
            description="Searches for specific evidence, facts, and data",
        )
        self.llm_client = llm_client
        self.api_token = api_token

    async def execute(self, query: str, state: ResearchState | None = None, sub_question_index: int = 0) -> str:
        """Find specific evidence related to the query."""
        existing_context = ""
        if state is not None and state.evidence:
            existing_context = "\n\nExisting findings to build upon:\n"
            for e in state.evidence:
                existing_context += f"- [{e.source}] {e.content}\n"

        prompt = (
            "You are a research assistant specializing in finding evidence. "
            "For the following query, find specific evidence, facts, and data that "
            "support or refute the claim. Be thorough and cite sources where possible:\n\n"
            f"{query}{existing_context}"
        )
        result = await self.llm_client.generate(prompt, api_token=self.api_token)
        if state is not None:
            state.add_evidence(result, source=self.name, confidence=0.8, sub_question_index=sub_question_index)
        return result
