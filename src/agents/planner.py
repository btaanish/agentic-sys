from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from src.agents.base import BaseAgent
from src.core.llm_client import LLMClient

if TYPE_CHECKING:
    from src.core.research_state import ResearchState


_SYSTEM_PROMPT = (Path(__file__).parent / "planner.md").read_text(encoding="utf-8")


class PlannerAgent(BaseAgent):
    """Agent that revises sub-questions between research iterations."""

    def __init__(self, llm_client: LLMClient, api_token: str | None = None) -> None:
        super().__init__(
            name="planner",
            description="Revises sub-questions between iterations based on gathered state",
        )
        self.llm_client = llm_client
        self.api_token = api_token

    async def execute(self, query: str, state: ResearchState | None = None, sub_question_index: int = 0) -> str:
        """Return the raw planner output for ``query`` (a pre-formatted state summary)."""
        return await self.llm_client.generate(
            query,
            api_token=self.api_token,
            system=_SYSTEM_PROMPT,
            max_tokens=1024,
        )

    async def plan(self, state: ResearchState) -> dict:
        """Plan revisions based on current research state. Returns a structured dict."""
        sq_lines: list[str] = []
        for i, sq in enumerate(state.sub_questions):
            confidence = state.confidence_scores.get(i, 0.0)
            sq_lines.append(
                f"  [{i}] (confidence={confidence:.2f}, status={sq.status.value}) {sq.text}"
            )
        sub_q_block = "\n".join(sq_lines) if sq_lines else "  (none)"

        unresolved = "\n".join(f"  - {issue}" for issue in state.unresolved_issues) or "  (none)"

        contradictions_lines: list[str] = []
        for c in state.contradictions:
            desc = c.get("description", "")
            resolution = c.get("resolution") or "unresolved"
            contradictions_lines.append(f"  - [{resolution}] {desc}")
        contradictions_block = "\n".join(contradictions_lines) or "  (none)"

        prompt = (
            f"Original query:\n{state.query}\n\n"
            f"Current sub-questions:\n{sub_q_block}\n\n"
            f"Unresolved issues:\n{unresolved}\n\n"
            f"Contradictions:\n{contradictions_block}\n\n"
            "Revise the plan per the rules. Return JSON only."
        )
        raw = await self.execute(prompt)
        try:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            parsed = json.loads(raw[start:end])
        except (json.JSONDecodeError, ValueError):
            return {"refinements": [], "additions": [], "retire": []}

        return {
            "refinements": parsed.get("refinements", []) or [],
            "additions": parsed.get("additions", []) or [],
            "retire": parsed.get("retire", []) or [],
        }
