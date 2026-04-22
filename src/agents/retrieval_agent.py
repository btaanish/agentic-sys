from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from src.agents.base import BaseAgent
from src.core.llm_client import LLMClient

if TYPE_CHECKING:
    from src.core.research_state import ResearchState


_SYSTEM_PROMPT = (Path(__file__).parent / "retrieval_agent.md").read_text(encoding="utf-8")

_WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 3,
}


class RetrievalAgent(BaseAgent):
    """Agent that retrieves fresh primary-source material via web search."""

    def __init__(self, llm_client: LLMClient, api_token: str | None = None) -> None:
        super().__init__(
            name="retrieval",
            description="Retrieves fresh primary-source material via web search",
        )
        self.llm_client = llm_client
        self.api_token = api_token

    async def execute(self, query: str, state: ResearchState | None = None, sub_question_index: int = 0) -> str:
        prompt = f"Sub-question to research:\n\n{query}"
        result = await self.llm_client.generate(
            prompt,
            api_token=self.api_token,
            system=_SYSTEM_PROMPT,
            max_tokens=2048,
            tools=[_WEB_SEARCH_TOOL],
        )
        if state is not None:
            state.add_evidence(result, source=self.name, confidence=0.85, sub_question_index=sub_question_index)
        return result
