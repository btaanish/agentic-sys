from src.agents.base import BaseAgent
from src.core.llm_client import LLMClient


class SynthesizerAgent(BaseAgent):
    """Agent that synthesizes multiple research findings into a coherent answer."""

    def __init__(self, llm_client: LLMClient, api_token: str | None = None) -> None:
        super().__init__(name="synthesizer", description="Synthesizes multiple findings into a coherent answer")
        self.llm_client = llm_client
        self.api_token = api_token

    async def execute(self, query: str) -> str:
        """Synthesize findings into a coherent answer.

        Args:
            query: A string containing the original query and all gathered findings.
        """
        prompt = (
            f"You are a research synthesizer. Given the following research findings, "
            f"produce a clear, well-organized, and coherent summary that answers the "
            f"original question:\n\n{query}"
        )
        return await self.llm_client.generate(prompt, api_token=self.api_token)
