from src.agents.base import BaseAgent
from src.core.llm_client import LLMClient


class GatherAgent(BaseAgent):
    """Agent that researches a sub-question using the LLM."""

    def __init__(self, llm_client: LLMClient, api_token: str | None = None) -> None:
        super().__init__(name="gather", description="Researches a sub-question and returns findings")
        self.llm_client = llm_client
        self.api_token = api_token

    async def execute(self, query: str) -> str:
        """Research a sub-question and return findings."""
        prompt = (
            f"You are a research assistant. Thoroughly research the following question "
            f"and provide detailed, factual findings:\n\n{query}"
        )
        return await self.llm_client.generate(prompt, api_token=self.api_token)
