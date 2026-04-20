import asyncio
import json
from collections.abc import Callable, Coroutine
from typing import Any

import anthropic

from src.agents.context_agent import ContextAgent
from src.agents.counterexample_agent import CounterexampleAgent
from src.agents.evidence_agent import EvidenceAgent
from src.agents.gap_detection_agent import GapDetectionAgent
from src.agents.synthesizer import SynthesizerAgent
from src.core.llm_client import LLMClient
from src.core.research_state import ResearchState, SubQuestion, SubQuestionStatus

EventCallback = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


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

    async def _emit(self, event: dict[str, Any]) -> None:
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
            state = ResearchState(query=query)

            # Step 1: Decompose
            await self._emit({"event": "status", "message": "Decomposing query into sub-questions"})
            sub_question_texts = await self._decompose(query)

            state.sub_questions = [
                SubQuestion(text=sq) for sq in sub_question_texts
            ]
            await self._emit({
                "event": "state_update",
                "message": "Sub-questions identified",
                "data": json.dumps(state.to_dict()),
            })

            # Step 2: Gather — run multiple agents per sub-question in parallel
            agents = [
                ContextAgent(self.llm_client, api_token=self.api_token),
                EvidenceAgent(self.llm_client, api_token=self.api_token),
                CounterexampleAgent(self.llm_client, api_token=self.api_token),
                GapDetectionAgent(self.llm_client, api_token=self.api_token),
            ]
            agent_names = [a.name for a in agents]

            async def run_agent(
                agent: ContextAgent | EvidenceAgent | CounterexampleAgent | GapDetectionAgent,
                sq_text: str,
                sq_index: int,
            ) -> str:
                result = await agent.execute(sq_text)
                state.add_evidence(result, source=agent.name, confidence=0.7, sub_question_index=sq_index)
                return result

            tasks = []
            for i, sq in enumerate(state.sub_questions):
                sq.status = SubQuestionStatus.IN_PROGRESS
                sq.assigned_agents = agent_names
                await self._emit({
                    "event": "status",
                    "message": f"Researching sub-topic: {sq.text}",
                })
                for agent in agents:
                    tasks.append(run_agent(agent, sq.text, i))

            dispatch_data = json.dumps(
                {"agents": agent_names, "sub_question_count": len(state.sub_questions)}
            )
            await self._emit({
                "event": "state_update",
                "message": "Agents dispatched",
                "data": dispatch_data,
            })

            await asyncio.gather(*tasks)

            for sq in state.sub_questions:
                sq.status = SubQuestionStatus.COMPLETED

            confidence_data = json.dumps(
                {"confidence_scores": state.confidence_scores}
            )
            await self._emit({
                "event": "state_update",
                "message": "Research complete",
                "data": confidence_data,
            })

            # Step 3: Synthesize
            await self._emit({"event": "status", "message": "Synthesizing results"})
            synthesizer = SynthesizerAgent(self.llm_client, api_token=self.api_token)

            synthesis_input = f"Original query: {query}\n\n"
            for i, sq in enumerate(state.sub_questions):
                relevant_evidence = [
                    e for e in state.evidence if e.sub_question_index == i
                ]
                synthesis_input += f"Sub-question {i + 1}: {sq.text}\n"
                for e in relevant_evidence:
                    synthesis_input += f"  [{e.source}] {e.content}\n"
                synthesis_input += "\n"

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
