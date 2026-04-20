from src.agents.base import BaseAgent
from src.core.llm_client import LLMClient


class ContextAgent(BaseAgent):
    """Agent that explores background context for a query."""

    def __init__(self, llm_client: LLMClient, api_token: str | None = None) -> None:
        super().__init__(
            name="context",
            description="Explores background context, key concepts, and relevant frameworks",
        )
        self.llm_client = llm_client
        self.api_token = api_token

    async def execute(self, query: str) -> str:
        """Provide background context for the given query."""
        prompt = (
            "You are a research assistant specializing in providing background context. "
            "For the following query, provide relevant background context, key concepts, "
            "and any applicable frameworks or theories that help understand the topic:\n\n"
            f"{query}"
        )
        return await self.llm_client.generate(prompt, api_token=self.api_token)
