import json
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.orchestrator import ResearchOrchestrator
from src.core.llm_client import LLMClient


@pytest.mark.anyio
async def test_orchestrator_runs_agents_in_parallel():
    """Verify that all 4 agents run for each sub-question (parallel via gather)."""
    llm = LLMClient()
    call_count = 0

    async def mock_generate(prompt: str, api_token: str | None = None) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["sq1", "sq2"]'
        elif call_count <= 9:
            return f"agent result {call_count}"
        elif call_count <= 17:
            # Source evaluator calls: 8 evidence pieces
            return '{"source_type": "unknown", "credibility_score": 0.7, "bias_score": 0.3, "recency_score": 0.5, "domain": "test"}'
        else:
            return "final answer"

    orchestrator = ResearchOrchestrator(llm, api_token="test")

    with patch.object(llm, "generate", side_effect=mock_generate):
        result = await orchestrator.run("test query")

    assert result == "final answer"
    # 1 decompose + 4 agents * 2 sub-questions + 8 evaluate + 1 synthesize = 18
    assert call_count == 18


@pytest.mark.anyio
async def test_orchestrator_populates_research_state():
    """After run, the state_update events show evidence was collected."""
    llm = LLMClient()
    events: list[dict] = []

    async def capture(event: dict) -> None:
        events.append(event)

    call_count = 0

    async def mock_generate(prompt: str, api_token: str | None = None) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["sq1"]'
        elif call_count <= 5:
            return f"evidence {call_count}"
        else:
            return "synthesis"

    orchestrator = ResearchOrchestrator(llm, api_token="test", callback=capture)

    with patch.object(llm, "generate", side_effect=mock_generate):
        await orchestrator.run("test")

    # Find the state_update with "Sub-questions identified"
    sub_q_events = [e for e in events if e.get("message") == "Sub-questions identified"]
    assert len(sub_q_events) == 1
    data = json.loads(sub_q_events[0]["data"])
    assert len(data["sub_questions"]) == 1
    assert data["sub_questions"][0]["text"] == "sq1"


@pytest.mark.anyio
async def test_orchestrator_state_has_confidence_scores():
    """After gathering, state_update 'Research complete' includes confidence scores."""
    llm = LLMClient()
    events: list[dict] = []

    async def capture(event: dict) -> None:
        events.append(event)

    call_count = 0

    async def mock_generate(prompt: str, api_token: str | None = None) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["sq1"]'
        elif call_count <= 5:
            return "findings"
        else:
            return "final"

    orchestrator = ResearchOrchestrator(llm, api_token="test", callback=capture)

    with patch.object(llm, "generate", side_effect=mock_generate):
        await orchestrator.run("query")

    research_complete = [e for e in events if e.get("message") == "Research complete"]
    assert len(research_complete) == 1
    data = json.loads(research_complete[0]["data"])
    assert "confidence_scores" in data
    # 4 agents add evidence with confidence 0.7, 0.8, 0.6, 0.5 → avg 0.65
    assert data["confidence_scores"]["0"] == pytest.approx(0.65)


@pytest.mark.anyio
async def test_orchestrator_enriched_sse_events():
    """Verify new state_update events are emitted alongside existing events."""
    llm = LLMClient()
    events: list[dict] = []

    async def capture(event: dict) -> None:
        events.append(event)

    call_count = 0

    async def mock_generate(prompt: str, api_token: str | None = None) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["sq1", "sq2"]'
        elif call_count <= 9:
            return "data"
        else:
            return "answer"

    orchestrator = ResearchOrchestrator(llm, api_token="test", callback=capture)

    with patch.object(llm, "generate", side_effect=mock_generate):
        await orchestrator.run("q")

    event_types = [e["event"] for e in events]

    # Must have state_update events (new enrichment)
    state_updates = [e for e in events if e["event"] == "state_update"]
    assert len(state_updates) >= 3  # sub-questions identified, agents dispatched, research complete

    # Must still have traditional status events
    assert "status" in event_types
    assert "result" in event_types

    # Verify specific state_update messages
    su_messages = [e["message"] for e in state_updates]
    assert "Sub-questions identified" in su_messages
    assert "Agents dispatched" in su_messages
    assert "Research complete" in su_messages
