from src.agents.base import BaseAgent
from src.core.llm_client import LLMClient


class GapDetectionAgent(BaseAgent):
    """Agent that identifies missing pieces and unanswered questions."""

    def __init__(self, llm_client: LLMClient, api_token: str | None = None) -> None:
        super().__init__(
            name="gap_detection",
            description="Identifies gaps, ambiguities, missing info, and unanswered questions",
        )
        self.llm_client = llm_client
        self.api_token = api_token

    async def execute(self, query: str) -> str:
        """Identify gaps and missing information for the query."""
        prompt = (
            "You are a research assistant specializing in identifying gaps in knowledge. "
            "For the following query, identify gaps, ambiguities, missing information, "
            "and unanswered questions that need further investigation:\n\n"
            f"{query}"
        )
        return await self.llm_client.generate(prompt, api_token=self.api_token)
