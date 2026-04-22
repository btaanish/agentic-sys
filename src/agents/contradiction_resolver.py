from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from src.agents.base import BaseAgent
from src.core.llm_client import LLMClient

if TYPE_CHECKING:
    from src.core.research_state import ResearchState


_SYSTEM_PROMPT = (Path(__file__).parent / "contradiction_resolver.md").read_text(encoding="utf-8")


class ContradictionResolverAgent(BaseAgent):
    """Agent that adjudicates a specific contradiction between evidence items."""

    def __init__(self, llm_client: LLMClient, api_token: str | None = None) -> None:
        super().__init__(
            name="contradiction_resolver",
            description="Adjudicates conflicts between evidence items and resolves or flags them",
        )
        self.llm_client = llm_client
        self.api_token = api_token

    async def execute(self, query: str, state: ResearchState | None = None, sub_question_index: int = 0) -> str:
        """Resolve the contradiction described by ``query``.

        ``query`` is expected to be a pre-formatted description of the conflict
        built by the orchestrator (including the evidence items involved).
        """
        result = await self.llm_client.generate(
            query,
            api_token=self.api_token,
            system=_SYSTEM_PROMPT,
            max_tokens=1024,
        )
        return result

    async def resolve(
        self,
        description: str,
        evidence_items: list[tuple[int, str, str, float]],
    ) -> dict:
        """Resolve a single contradiction.

        ``evidence_items`` is a list of ``(evidence_id, source, content, credibility)``.
        Returns the parsed JSON resolution or a fallback dict if parsing fails.
        """
        evidence_block = "\n\n".join(
            f"Evidence {eid} [source={source}, credibility={cred:.2f}]:\n{content}"
            for eid, source, content, cred in evidence_items
        )
        prompt = (
            f"Contradiction to adjudicate:\n{description}\n\n"
            f"Evidence items involved:\n{evidence_block}"
        )
        raw = await self.execute(prompt)
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except (json.JSONDecodeError, ValueError):
            return {
                "resolution_type": "open",
                "preferred_evidence_id": None,
                "explanation": raw.strip() or "Parser failed to extract structured resolution.",
                "confidence_impact": 0.0,
            }
