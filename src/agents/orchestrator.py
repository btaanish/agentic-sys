import json
from collections.abc import Callable, Coroutine
from typing import Any

import anthropic

from src.agents.gather import GatherAgent
from src.agents.synthesizer import SynthesizerAgent
from src.core.llm_client import LLMClient

EventCallback = Callable[[dict[str, str]], Coroutine[Any, Any, None]]


class ResearchOrchestrator:
    """Orchestrates the research pipeline: decompose, gather, synthesize."""

    def __init__(
        self,
        llm_client: LLMClient,
        api_token: str | None = None,
        callback: EventCallback | None = None,
    ) -> None:
        self.llm_client = llm_client
        self.api_token = api_token
        self.callback = callback

    async def _emit(self, event: dict[str, str]) -> None:
        if self.callback:
            await self.callback(event)

    async def _decompose(self, query: str) -> list[str]:
        """Decompose a query into 2-4 sub-questions using the LLM."""
        prompt = (
            f"Break down the following research query into 2-4 specific sub-questions. "
            f"Return ONLY a JSON array of strings, no other text:\n\n{query}"
        )
        try:
            raw = await self.llm_client.generate(prompt, api_token=self.api_token)
            # Extract JSON array from response
            start = raw.index("[")
            end = raw.rindex("]") + 1
            sub_questions: list[str] = json.loads(raw[start:end])
            return sub_questions[:4]
        except (json.JSONDecodeError, ValueError):
            # Fallback: treat entire query as single sub-question
            return [query]

    async def run(self, query: str) -> str:
        """Run the full research pipeline."""
        try:
            # Step 1: Decompose
            await self._emit({"event": "status", "message": "Decomposing query into sub-questions"})
            sub_questions = await self._decompose(query)

            # Step 2: Gather
            gather_agent = GatherAgent(self.llm_client, api_token=self.api_token)
            findings: list[str] = []
            for sq in sub_questions:
                await self._emit({"event": "status", "message": f"Researching sub-topic: {sq}"})
                result = await gather_agent.execute(sq)
                findings.append(result)

            # Step 3: Synthesize
            await self._emit({"event": "status", "message": "Synthesizing results"})
            synthesizer = SynthesizerAgent(self.llm_client, api_token=self.api_token)

            synthesis_input = f"Original query: {query}\n\n"
            for i, (sq, finding) in enumerate(zip(sub_questions, findings), 1):
                synthesis_input += f"Sub-question {i}: {sq}\nFindings: {finding}\n\n"

            final_answer = await synthesizer.execute(synthesis_input)

            await self._emit({"event": "result", "data": final_answer})
            await self._emit({"event": "status", "message": "Done"})

            return final_answer

        except anthropic.AuthenticationError as e:
            error_msg = f"Authentication failed: {e}"
            await self._emit({"event": "error", "message": error_msg})
            return error_msg
        except anthropic.APIError as e:
            error_msg = f"API error: {e}"
            await self._emit({"event": "error", "message": error_msg})
            return error_msg
        except TimeoutError as e:
            error_msg = f"Request timed out: {e}"
            await self._emit({"event": "error", "message": error_msg})
            return error_msg
