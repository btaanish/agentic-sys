from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from src.agents.base import BaseAgent
from src.core.llm_client import LLMClient

if TYPE_CHECKING:
    from src.core.research_state import ResearchState


_SYSTEM_PROMPT = (Path(__file__).parent / "evidence_agent.md").read_text(encoding="utf-8")


class EvidenceAgent(BaseAgent):
    """Agent that searches for direct evidence related to a query."""

    def __init__(self, llm_client: LLMClient, api_token: str | None = None) -> None:
        super().__init__(
            name="evidence",
            description="Searches for specific evidence, facts, and data",
        )
        self.llm_client = llm_client
        self.api_token = api_token

    async def execute(
        self,
        query: str,
        state: ResearchState | None = None,
        sub_question_index: int = 0,
    ) -> str:
        """Find specific evidence related to the query."""
        existing_context = ""
        if state is not None and state.evidence:
            existing_context = "\n\nExisting findings to build upon:\n"
            for e in state.evidence:
                existing_context += f"- [{e.source}] {e.content}\n"

        prompt = f"""Claim Under Investigation:

{query}{existing_context}
"""

        result = await self.llm_client.generate(
            prompt,
            api_token=self.api_token,
            system=_SYSTEM_PROMPT,
        )

        if state is not None:
            state.add_evidence(
                result,
                source=self.name,
                confidence=0.8,
                sub_question_index=sub_question_index,
            )
        return result