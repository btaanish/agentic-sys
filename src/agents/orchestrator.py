import asyncio
import json
from collections.abc import Callable, Coroutine
from typing import Any

import anthropic

from src.agents.context_agent import ContextAgent
from src.agents.counterexample_agent import CounterexampleAgent
from src.agents.evidence_agent import EvidenceAgent
from src.agents.gap_detection_agent import GapDetectionAgent
from src.agents.source_evaluator import SourceEvaluator
from src.agents.synthesizer import SynthesizerAgent
from src.core.llm_client import LLMClient
from src.core.research_state import ResearchState, SubQuestion, SubQuestionStatus

EventCallback = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]

EXPLORATION_ANGLES = [
    "technical",
    "historical",
    "empirical",
    "comparative",
    "skeptical",
    "practical",
]


class ResearchOrchestrator:
    """Orchestrates the research pipeline: decompose, gather, synthesize."""

    def __init__(
        self,
        llm_client: LLMClient,
        api_token: str | None = None,
        callback: EventCallback | None = None,
        max_iterations: int = 3,
    ) -> None:
        self.llm_client = llm_client
        self.api_token = api_token
        self.callback = callback
        self.max_iterations = max_iterations

    async def _emit(self, event: dict[str, Any]) -> None:
        if self.callback:
            await self.callback(event)

    async def _decompose(self, query: str, angles: list[str] | None = None) -> list[str]:
        """Decompose a query into 2-4 sub-questions using the LLM."""
        angle_instruction = ""
        if angles:
            angle_list = ", ".join(angles)
            angle_instruction = (
                f" Generate sub-questions that explore these investigative angles: {angle_list}."
                f" Prefix each sub-question with its angle in brackets, e.g. [technical] ..."
            )
        prompt = (
            f"Break down the following research query into 2-4 specific sub-questions.{angle_instruction} "
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

    async def _gather_and_evaluate(
        self,
        state: ResearchState,
        target_questions: list[tuple[int, SubQuestion]],
    ) -> None:
        """Run gather agents and evaluate credibility for target sub-questions."""
        agents = [
            ContextAgent(self.llm_client, api_token=self.api_token),
            EvidenceAgent(self.llm_client, api_token=self.api_token),
            CounterexampleAgent(self.llm_client, api_token=self.api_token),
            GapDetectionAgent(self.llm_client, api_token=self.api_token),
        ]
        agent_names = [a.name for a in agents]

        # Gather phase
        tasks = []
        for idx, sq in target_questions:
            sq.status = SubQuestionStatus.IN_PROGRESS
            sq.assigned_agents = agent_names
            await self._emit({
                "event": "status",
                "message": f"Researching sub-topic: {sq.text}",
            })
            for agent in agents:
                tasks.append(agent.execute(sq.text, state, idx))

        dispatch_data = json.dumps(
            {"agents": agent_names, "sub_question_count": len(target_questions)}
        )
        await self._emit({
            "event": "state_update",
            "message": "Agents dispatched",
            "data": dispatch_data,
        })

        await asyncio.gather(*tasks)

        for _, sq in target_questions:
            sq.status = SubQuestionStatus.COMPLETED

        confidence_data = json.dumps(
            {"confidence_scores": state.confidence_scores}
        )
        await self._emit({
            "event": "state_update",
            "message": "Research complete",
            "data": confidence_data,
        })

        # Evaluate source credibility
        source_evaluator = SourceEvaluator(self.llm_client, api_token=self.api_token)
        await self._emit({"event": "status", "message": "Evaluating source credibility"})

        for evidence in state.evidence:
            if evidence.source_metadata is None:
                metadata = await source_evaluator.evaluate(evidence.content, evidence.source)
                evidence.source_metadata = metadata

        # Emit credibility evaluation state_update (M6 SSE gap fix)
        await self._emit({
            "event": "state_update",
            "message": "Source credibility evaluated",
            "data": json.dumps({
                "evidence_count": len(state.evidence),
                "confidence_scores": state.confidence_scores,
            }),
        })

        # Flag weak sources
        weak_sources = [e for e in state.evidence if e.source_metadata and e.source_metadata.is_weak()]
        if weak_sources:
            await self._emit({
                "event": "state_update",
                "message": f"Warning: {len(weak_sources)} weak source(s) detected (credibility < 0.3)",
                "data": json.dumps({"weak_source_count": len(weak_sources)}),
            })

    def _check_corroboration(self, state: ResearchState) -> list[int]:
        """Check which sub-questions need corroboration (avg credibility < 0.4).

        Returns list of sub-question indices needing corroboration.
        """
        needs_corroboration = []
        for i, sq in enumerate(state.sub_questions):
            relevant_evidence = [
                e for e in state.evidence if e.sub_question_index == i
            ]
            if relevant_evidence:
                avg_credibility = sum(
                    e.source_metadata.credibility_score if e.source_metadata else 0.5
                    for e in relevant_evidence
                ) / len(relevant_evidence)
                if avg_credibility < 0.4:
                    needs_corroboration.append(i)
        return needs_corroboration

    async def _detect_contradictions(self, state: ResearchState) -> None:
        """Detect contradictions between evidence items using LLM analysis.

        Only invokes LLM when evidence within a sub-question group shows
        meaningful credibility divergence (spread > 0.2), which signals
        potential conflicting information worth analyzing.
        """
        # Group evidence by sub_question_index
        groups: dict[int, list[tuple[int, Any]]] = {}
        for idx, evidence in enumerate(state.evidence):
            groups.setdefault(evidence.sub_question_index, []).append((idx, evidence))

        for sq_idx, items in groups.items():
            if len(items) < 2:
                continue

            # Only analyze groups with meaningful credibility divergence
            credibilities = [
                e.source_metadata.credibility_score if e.source_metadata else 0.5
                for _, e in items
            ]
            if max(credibilities) - min(credibilities) <= 0.2:
                continue

            evidence_text = "\n".join(
                f"Evidence {i}: [{e.source}] {e.content}" for i, e in items
            )
            prompt = (
                f"Given these evidence items for a research sub-question, identify any contradictions "
                f"between them. Return ONLY a JSON array of objects with keys 'evidence_indices' "
                f"(list of integer indices) and 'description' (string). If no contradictions, "
                f"return an empty array [].\n\n{evidence_text}"
            )
            try:
                raw = await self.llm_client.generate(prompt, api_token=self.api_token)
                start = raw.index("[")
                end = raw.rindex("]") + 1
                detected: list[dict] = json.loads(raw[start:end])
                for c in detected:
                    evidence_ids = [items[i][0] for i in c.get("evidence_indices", []) if i < len(items)]
                    description = c.get("description", "")
                    if evidence_ids and description:
                        state.add_contradiction(evidence_ids=evidence_ids, description=description)
                        action = f"Resolve contradiction: {description}"
                        if action not in state.next_actions:
                            state.next_actions.append(action)
            except (json.JSONDecodeError, ValueError):
                continue

    async def run(self, query: str) -> str:
        """Run the full research pipeline with iterative refinement."""
        try:
            state = ResearchState(query=query)

            # Step 1: Decompose with exploration angles
            await self._emit({"event": "status", "message": "Decomposing query into sub-questions"})
            initial_angles = EXPLORATION_ANGLES[:3]
            sub_question_texts = await self._decompose(query, angles=initial_angles)
            state.exploration_angles.extend(initial_angles)

            state.sub_questions = [
                SubQuestion(text=sq) for sq in sub_question_texts
            ]
            await self._emit({
                "event": "state_update",
                "message": "Sub-questions identified",
                "data": json.dumps(state.to_dict()),
            })

            # Step 2: Iterative gather + evaluate loop
            for iteration in range(self.max_iterations):
                if iteration == 0:
                    # First iteration: all sub-questions
                    target_questions = list(enumerate(state.sub_questions))
                else:
                    # Subsequent iterations: only sub-questions needing corroboration
                    corroboration_indices = self._check_corroboration(state)
                    if not corroboration_indices:
                        break
                    target_questions = [
                        (i, state.sub_questions[i]) for i in corroboration_indices
                    ]
                    # Clear processed corroboration requests
                    state.next_actions = [
                        a for a in state.next_actions
                        if not a.startswith("Corroboration needed for:")
                    ]

                await self._gather_and_evaluate(state, target_questions)

                # Detect contradictions
                await self._detect_contradictions(state)

                # Track new angles for subsequent iterations
                if iteration > 0:
                    angle_start = ((iteration % ((len(EXPLORATION_ANGLES) + 2) // 3)) * 3)
                    new_angles = EXPLORATION_ANGLES[angle_start:angle_start + 3]
                    for angle in new_angles:
                        if angle not in state.exploration_angles:
                            state.exploration_angles.append(angle)

                # Check corroboration needs and populate next_actions
                corroboration_indices = self._check_corroboration(state)
                for i in corroboration_indices:
                    action = f"Corroboration needed for: {state.sub_questions[i].text}"
                    if action not in state.next_actions:
                        state.next_actions.append(action)

                # Update unresolved issues — remove resolved ones (confidence >= 0.8)
                resolved_indices = {
                    i for i, score in state.confidence_scores.items() if score >= 0.8
                }
                state.unresolved_issues = [
                    issue for issue in state.unresolved_issues
                    if not any(
                        f"sub-question {i}" in issue.lower()
                        for i in resolved_indices
                    )
                ]

                avg_conf = state.avg_confidence()

                # Emit iteration progress
                await self._emit({
                    "event": "status",
                    "message": f"Iteration {iteration + 1}/{self.max_iterations} complete — confidence: {avg_conf:.2f}",
                })
                await self._emit({
                    "event": "state_update",
                    "message": "Iteration progress",
                    "data": json.dumps({
                        "iteration": iteration + 1,
                        "max_iterations": self.max_iterations,
                        "avg_confidence": avg_conf,
                        "confidence_per_sub_question": state.confidence_scores,
                        "remaining_gaps": len(state.unresolved_issues),
                        "pending_actions": len(state.next_actions),
                    }),
                })

                # Decision: stop early if confidence is high enough
                if avg_conf >= 0.8:
                    break

                # Decision: stop if no actionable follow-ups
                if not state.next_actions:
                    break

            # Step 3: Synthesize
            await self._emit({"event": "status", "message": "Synthesizing results"})
            synthesizer = SynthesizerAgent(self.llm_client, api_token=self.api_token)

            synthesis_input = f"Original query: {query}\n\n"
            for i, sq in enumerate(state.sub_questions):
                relevant_evidence = [
                    e for e in state.evidence if e.sub_question_index == i
                ]
                # Rank by credibility (highest first)
                relevant_evidence.sort(
                    key=lambda e: e.source_metadata.credibility_score if e.source_metadata else 0.5,
                    reverse=True,
                )
                synthesis_input += f"Sub-question {i + 1}: {sq.text}\n"
                for e in relevant_evidence:
                    cred = e.source_metadata.credibility_score if e.source_metadata else 0.5
                    synthesis_input += f"  [{e.source}] (credibility: {cred:.1f}) {e.content}\n"
                synthesis_input += "\n"

            if state.contradictions:
                synthesis_input += "Contradictions found:\n"
                for c in state.contradictions:
                    synthesis_input += f"  - {c['description']} (evidence IDs: {c['evidence_ids']})\n"
                synthesis_input += "\n"

            if state.exploration_angles:
                synthesis_input += f"Exploration angles covered: {', '.join(state.exploration_angles)}\n\n"

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
