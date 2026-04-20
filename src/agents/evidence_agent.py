from src.agents.base import BaseAgent
from src.core.llm_client import LLMClient


class EvidenceAgent(BaseAgent):
    """Agent that searches for direct evidence related to a query."""

    def __init__(self, llm_client: LLMClient, api_token: str | None = None) -> None:
        super().__init__(
            name="evidence",
            description="Searches for specific evidence, facts, and data",
        )
        self.llm_client = llm_client
        self.api_token = api_token

    async def execute(self, query: str) -> str:
        """Find specific evidence related to the query."""
        prompt = (
            "You are a research assistant specializing in finding evidence. "
            "For the following query, find specific evidence, facts, and data that "
            "support or refute the claim. Be thorough and cite sources where possible:\n\n"
            f"{query}"
        )
        return await self.llm_client.generate(prompt, api_token=self.api_token)
