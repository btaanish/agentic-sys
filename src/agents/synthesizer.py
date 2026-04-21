from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from src.agents.base import BaseAgent
from src.core.llm_client import LLMClient

if TYPE_CHECKING:
    from src.core.research_state import ResearchState


_SYSTEM_PROMPT = (Path(__file__).parent / "synthesizer.md").read_text(encoding="utf-8")


class SynthesizerAgent(BaseAgent):
    """Agent that synthesizes multiple research findings into a coherent answer."""

    def __init__(self, llm_client: LLMClient, api_token: str | None = None) -> None:
        super().__init__(name="synthesizer", description="Synthesizes multiple findings into a coherent answer")
        self.llm_client = llm_client
        self.api_token = api_token

    async def execute(self, query: str, state: ResearchState | None = None, sub_question_index: int = 0) -> str:
        """Synthesize findings into a coherent answer.

        Args:
            query: A string containing the original query and all gathered findings.
            state: Optional ResearchState (not used by synthesizer but accepted for interface consistency).
            sub_question_index: Optional sub-question index (not used by synthesizer).
        """
        return await self.llm_client.generate(
            query,
            api_token=self.api_token,
            system=_SYSTEM_PROMPT,
            max_tokens=4096,
        )
