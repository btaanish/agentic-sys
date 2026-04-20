from src.agents.base import BaseAgent
from src.core.llm_client import LLMClient


class CounterexampleAgent(BaseAgent):
    """Agent that looks for contradictions and opposing viewpoints."""

    def __init__(self, llm_client: LLMClient, api_token: str | None = None) -> None:
        super().__init__(
            name="counterexample",
            description="Finds counterexamples, opposing viewpoints, and weaknesses",
        )
        self.llm_client = llm_client
        self.api_token = api_token

    async def execute(self, query: str) -> str:
        """Find counterexamples and opposing viewpoints for the query."""
        prompt = (
            "You are a research assistant specializing in critical analysis. "
            "For the following query, find counterexamples, opposing viewpoints, "
            "and weaknesses in the argument. Challenge assumptions and identify "
            "potential flaws:\n\n"
            f"{query}"
        )
        return await self.llm_client.generate(prompt, api_token=self.api_token)
