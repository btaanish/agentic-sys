from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from src.agents.base import BaseAgent
from src.core.llm_client import LLMClient

if TYPE_CHECKING:
    from src.core.research_state import ResearchState


_SYSTEM_PROMPT = (Path(__file__).parent / "counterexample_agent.md").read_text(encoding="utf-8")


class CounterexampleAgent(BaseAgent):
    """Agent that looks for contradictions and opposing viewpoints."""

    def __init__(self, llm_client: LLMClient, api_token: str | None = None) -> None:
        super().__init__(
            name="counterexample",
            description="Finds counterexamples, opposing viewpoints, and weaknesses",
        )
        self.llm_client = llm_client
        self.api_token = api_token

    async def execute(self, query: str, state: ResearchState | None = None, sub_question_index: int = 0) -> str:
        """Find counterexamples and opposing viewpoints for the query."""
        existing_claims = ""
        if state is not None and state.evidence:
            relevant = [e for e in state.evidence if e.sub_question_index == sub_question_index]
            if relevant:
                existing_claims = "\n\nExisting claims to challenge:\n"
                for e in relevant:
                    existing_claims += f"- [{e.source}] {e.content[:400]}\n"

        prompt = f"Target:\n\n{query}{existing_claims}"
        result = await self.llm_client.generate(prompt, api_token=self.api_token, system=_SYSTEM_PROMPT)
        if state is not None:
            state.add_evidence(result, source=self.name, confidence=0.6, sub_question_index=sub_question_index)
            state.add_unresolved(f"Counterexamples found for sub-question {sub_question_index}: {result[:100]}")
        return result
