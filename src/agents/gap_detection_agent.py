from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.base import BaseAgent
from src.core.llm_client import LLMClient

if TYPE_CHECKING:
    from src.core.research_state import ResearchState


class GapDetectionAgent(BaseAgent):
    """Agent that identifies missing pieces and unanswered questions."""

    def __init__(self, llm_client: LLMClient, api_token: str | None = None) -> None:
        super().__init__(
            name="gap_detection",
            description="Identifies gaps, ambiguities, missing info, and unanswered questions",
        )
        self.llm_client = llm_client
        self.api_token = api_token

    async def execute(self, query: str, state: ResearchState | None = None, sub_question_index: int = 0) -> str:
        """Identify gaps and missing information for the query."""
        existing_coverage = ""
        if state is not None and state.evidence:
            existing_coverage = "\n\nAlready covered:\n"
            for e in state.evidence:
                existing_coverage += f"- [{e.source}] {e.content}\n"

        prompt = (
            "You are a research assistant specializing in identifying gaps in knowledge. "
            "For the following query, identify gaps, ambiguities, missing information, "
            "and unanswered questions that need further investigation:\n\n"
            f"{query}{existing_coverage}"
        )
        result = await self.llm_client.generate(prompt, api_token=self.api_token)
        if state is not None:
            state.add_evidence(result, source=self.name, confidence=0.5, sub_question_index=sub_question_index)
            state.add_unresolved(f"Gaps identified for sub-question {sub_question_index}: {result[:100]}")
        return result
