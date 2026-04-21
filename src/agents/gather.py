from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from src.agents.base import BaseAgent
from src.core.llm_client import LLMClient

if TYPE_CHECKING:
    from src.core.research_state import ResearchState


_SYSTEM_PROMPT = (Path(__file__).parent / "gather.md").read_text(encoding="utf-8")


class GatherAgent(BaseAgent):
    """Agent that researches a sub-question using the LLM."""

    def __init__(self, llm_client: LLMClient, api_token: str | None = None) -> None:
        super().__init__(name="gather", description="Researches a sub-question and returns findings")
        self.llm_client = llm_client
        self.api_token = api_token

    async def execute(self, query: str, state: ResearchState | None = None, sub_question_index: int = 0) -> str:
        """Research a sub-question and return findings."""
        prompt = f"Question:\n\n{query}"
        return await self.llm_client.generate(prompt, api_token=self.api_token, system=_SYSTEM_PROMPT)
