from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

from src.agents.base import BaseAgent
from src.core.llm_client import LLMClient
from src.core.source_metadata import SourceMetadata, SourceType

if TYPE_CHECKING:
    from src.core.research_state import ResearchState


class SourceEvaluator(BaseAgent):
    """Agent that evaluates source credibility and produces SourceMetadata."""

    def __init__(self, llm_client: LLMClient, api_token: str | None = None) -> None:
        super().__init__(
            name="source_evaluator",
            description="Evaluates source credibility, bias, and recency",
        )
        self.llm_client = llm_client
        self.api_token = api_token

    async def execute(
        self,
        query: str,
        state: ResearchState | None = None,
        sub_question_index: int = 0,
    ) -> str:
        """Standard agent interface — evaluates the query as evidence content."""
        metadata = await self.evaluate(query, "unknown")
        return json.dumps(
            {
                "source_id": metadata.source_id,
                "source_type": metadata.source_type.value,
                "credibility_score": metadata.credibility_score,
                "bias_score": metadata.bias_score,
                "recency_score": metadata.recency_score,
                "domain": metadata.domain,
                "overall_quality": metadata.overall_quality_score(),
            }
        )

    async def evaluate(
        self, evidence_content: str, evidence_source: str
    ) -> SourceMetadata:
        """Evaluate evidence and return SourceMetadata.

        Args:
            evidence_content: The text content of the evidence.
            evidence_source: The source identifier (URL, name, etc.).

        Returns:
            A SourceMetadata object with credibility assessment.
        """
        prompt = (
            "You are a source credibility evaluator. Analyze the following evidence "
            "and its source, then return a JSON object with these fields:\n"
            '- "source_type": one of "academic_paper", "news_article", "blog", '
            '"official_doc", "forum", "unknown"\n'
            '- "credibility_score": float 0-1 (1 = highly credible)\n'
            '- "bias_score": float 0-1 (1 = highly biased)\n'
            '- "recency_score": float 0-1 (1 = very recent/timely)\n'
            '- "domain": the domain or field of the source\n\n'
            "Return ONLY valid JSON, no other text.\n\n"
            f"Source: {evidence_source}\n"
            f"Evidence:\n{evidence_content}"
        )

        source_id = str(uuid.uuid4())

        try:
            result = await self.llm_client.generate(prompt, api_token=self.api_token)
            data = json.loads(result)

            source_type_str = data.get("source_type", "unknown")
            try:
                source_type = SourceType(source_type_str)
            except ValueError:
                source_type = SourceType.UNKNOWN

            return SourceMetadata(
                source_id=source_id,
                url=evidence_source if evidence_source.startswith("http") else "",
                domain=data.get("domain", ""),
                source_type=source_type,
                credibility_score=float(data.get("credibility_score", 0.5)),
                bias_score=float(data.get("bias_score", 0.5)),
                recency_score=float(data.get("recency_score", 0.5)),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return SourceMetadata(
                source_id=source_id,
                domain="",
                source_type=SourceType.UNKNOWN,
                credibility_score=0.4,
                bias_score=0.5,
                recency_score=0.3,
            )
