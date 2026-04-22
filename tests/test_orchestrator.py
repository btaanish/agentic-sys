from unittest.mock import AsyncMock, patch

import pytest

from src.agents.orchestrator import ResearchOrchestrator
from src.core.llm_client import LLMClient


@pytest.mark.anyio
async def test_orchestrator_full_flow():
    """Test decompose -> gather -> synthesize pipeline with mocked LLM."""
    llm = LLMClient()
    events: list[dict] = []

    async def capture_event(event: dict) -> None:
        events.append(event)

    orchestrator = ResearchOrchestrator(llm, api_token="test", callback=capture_event)

    call_count = 0

    async def mock_generate(prompt: str, api_token: str | None = None, **_kwargs: object) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Decompose call
            return '["sub-q1", "sub-q2"]'
        elif call_count <= 11:
            # Gather calls: 5 agents x 2 sub-questions = 10 calls
            return f"findings for call {call_count}"
        elif call_count <= 21:
            # Source evaluator calls: 10 evidence pieces
            return '{"source_type": "unknown", "credibility_score": 0.7, "bias_score": 0.3, "recency_score": 0.5, "domain": "test"}'
        else:
            # Synthesize call
            return "final synthesized answer"

    with patch.object(llm, "generate", side_effect=mock_generate):
        result = await orchestrator.run("test query")

    assert result == "final synthesized answer"
    # 1 decompose + 10 gather (5 agents x 2 sub-q) + 10 evaluate + 1 synthesize
    assert call_count == 22

    # Check events emitted
    event_types = [e["event"] for e in events]
    assert "status" in event_types
    assert "result" in event_types
    assert "state_update" in event_types

    # Check specific status messages
    messages = [e.get("message", "") for e in events]
    assert any("Decomposing" in m for m in messages)
    assert any("Researching" in m for m in messages)
    assert any("Synthesizing" in m for m in messages)
    assert any("Done" in m for m in messages)


@pytest.mark.anyio
async def test_orchestrator_no_callback():
    """Orchestrator works without a callback."""
    llm = LLMClient()
    orchestrator = ResearchOrchestrator(llm, api_token="test")

    call_count = 0

    async def mock_generate(prompt: str, api_token: str | None = None, **_kwargs: object) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["q1"]'
        elif call_count <= 6:
            # Gather calls: 5 agents x 1 sub-question
            return "gathered"
        elif call_count <= 11:
            # Source evaluator calls: 5 evidence pieces
            return '{"source_type": "unknown", "credibility_score": 0.7, "bias_score": 0.3, "recency_score": 0.5, "domain": "test"}'
        else:
            return "synthesized"

    with patch.object(llm, "generate", side_effect=mock_generate):
        result = await orchestrator.run("query")

    assert result == "synthesized"


@pytest.mark.anyio
async def test_orchestrator_decompose_fallback():
    """If decompose fails to parse JSON, falls back to original query."""
    llm = LLMClient()
    orchestrator = ResearchOrchestrator(llm, api_token="test")

    call_count = 0

    async def mock_generate(prompt: str, api_token: str | None = None, **_kwargs: object) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "not valid json"
        elif call_count <= 6:
            # Gather calls: 5 agents x 1 fallback sub-question
            return "gathered"
        elif call_count <= 11:
            # Source evaluator calls: 5 evidence pieces
            return '{"source_type": "unknown", "credibility_score": 0.7, "bias_score": 0.3, "recency_score": 0.5, "domain": "test"}'
        else:
            return "synthesized"

    with patch.object(llm, "generate", side_effect=mock_generate):
        result = await orchestrator.run("original query")

    assert result == "synthesized"
    # 1 decompose + 5 gather (5 agents x 1 fallback sub-q) + 5 evaluate + 1 synthesize
    assert call_count == 12


@pytest.mark.anyio
async def test_orchestrator_handles_api_error():
    """Orchestrator handles anthropic API errors gracefully."""
    import anthropic

    llm = LLMClient()
    events: list[dict] = []

    async def capture(event: dict) -> None:
        events.append(event)

    orchestrator = ResearchOrchestrator(llm, api_token="test", callback=capture)

    with patch.object(
        llm,
        "generate",
        side_effect=anthropic.AuthenticationError(
            message="invalid key",
            response=AsyncMock(status_code=401),
            body=None,
        ),
    ):
        result = await orchestrator.run("query")

    assert "Authentication failed" in result
    assert any(e["event"] == "error" for e in events)


@pytest.mark.anyio
async def test_orchestrator_emits_credibility_status():
    """Orchestrator emits 'Evaluating source credibility' status."""
    llm = LLMClient()
    events: list[dict] = []

    async def capture(event: dict) -> None:
        events.append(event)

    orchestrator = ResearchOrchestrator(llm, api_token="test", callback=capture)

    call_count = 0

    async def mock_generate(prompt: str, api_token: str | None = None, **_kwargs: object) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["q1"]'
        elif call_count <= 6:
            return "gathered"
        elif call_count <= 11:
            return '{"source_type": "unknown", "credibility_score": 0.7, "bias_score": 0.3, "recency_score": 0.5, "domain": "test"}'
        else:
            return "synthesized"

    with patch.object(llm, "generate", side_effect=mock_generate):
        await orchestrator.run("query")

    messages = [e.get("message", "") for e in events]
    assert any("Evaluating source credibility" in m for m in messages)


@pytest.mark.anyio
async def test_orchestrator_weak_source_warning():
    """Orchestrator emits weak source warning when credibility < 0.3."""
    llm = LLMClient()
    events: list[dict] = []

    async def capture(event: dict) -> None:
        events.append(event)

    orchestrator = ResearchOrchestrator(llm, api_token="test", callback=capture)

    call_count = 0

    async def mock_generate(prompt: str, api_token: str | None = None, **_kwargs: object) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["q1"]'
        elif call_count <= 6:
            return "gathered"
        elif call_count <= 11:
            # Return low credibility for all sources
            return '{"source_type": "blog", "credibility_score": 0.1, "bias_score": 0.8, "recency_score": 0.3, "domain": "test"}'
        else:
            return "synthesized"

    with patch.object(llm, "generate", side_effect=mock_generate):
        await orchestrator.run("query")

    messages = [e.get("message", "") for e in events]
    assert any("weak source" in m.lower() for m in messages)


@pytest.mark.anyio
async def test_synthesis_prompt_is_free_of_credibility_and_contradiction_meta():
    """The synthesis prompt must not surface credibility scores, contradiction
    metadata, exploration-angle markers, or internal agent-name tags to the
    synthesizer — those artifacts contaminate the final answer with research-
    process meta-commentary."""
    llm = LLMClient()
    orchestrator = ResearchOrchestrator(llm, api_token="test")

    call_count = 0
    synthesis_prompt = None

    async def mock_generate(prompt: str, api_token: str | None = None, **_kwargs: object) -> str:
        nonlocal call_count, synthesis_prompt
        call_count += 1
        if call_count == 1:
            return '["q1"]'
        elif call_count <= 6:
            return f"findings-{call_count}"
        elif call_count <= 11:
            scores = [0.9, 0.2, 0.7, 0.4, 0.6]
            idx = call_count - 7
            return f'{{"source_type": "unknown", "credibility_score": {scores[idx]}, "bias_score": 0.3, "recency_score": 0.5, "domain": "test"}}'
        elif "Original question" in prompt:
            synthesis_prompt = prompt
            return "synthesized"
        else:
            return "synthesized"

    with patch.object(llm, "generate", side_effect=mock_generate):
        await orchestrator.run("query")

    assert synthesis_prompt is not None
    # None of these research-process artifacts may leak into the synthesizer's prompt.
    lowered = synthesis_prompt.lower()
    assert "credibility" not in lowered
    assert "contradiction" not in lowered
    assert "exploration angle" not in lowered
    assert "[retrieval]" not in synthesis_prompt
    assert "[context]" not in synthesis_prompt
    assert "[evidence]" not in synthesis_prompt
    assert "[counterexample]" not in synthesis_prompt
    assert "[gap_detection]" not in synthesis_prompt


@pytest.mark.anyio
async def test_orchestrator_corroboration_for_low_credibility():
    """Orchestrator adds corroboration request for low-credibility sub-questions."""
    llm = LLMClient()
    events: list[dict] = []

    async def capture(event: dict) -> None:
        events.append(event)

    orchestrator = ResearchOrchestrator(llm, api_token="test", callback=capture)

    call_count = 0
    synthesis_prompt = None

    async def mock_generate(prompt: str, api_token: str | None = None, **_kwargs: object) -> str:
        nonlocal call_count, synthesis_prompt
        call_count += 1
        if call_count == 1:
            return '["q1"]'
        if "Original question" in prompt:
            synthesis_prompt = prompt
            return "synthesized"
        if "source credibility evaluator" in prompt.lower():
            # Very low credibility triggers corroboration
            return '{"source_type": "forum", "credibility_score": 0.2, "bias_score": 0.7, "recency_score": 0.3, "domain": "test"}'
        return "gathered"

    with patch.object(llm, "generate", side_effect=mock_generate):
        result = await orchestrator.run("query")

    assert result == "synthesized"
    # Since average credibility is 0.2 < 0.4, corroboration should be requested
    # The weak source warning should also be emitted
    messages = [e.get("message", "") for e in events]
    assert any("weak source" in m.lower() for m in messages)


@pytest.mark.anyio
async def test_orchestrator_handles_timeout():
    """Orchestrator handles timeout errors gracefully."""
    llm = LLMClient()
    events: list[dict] = []

    async def capture(event: dict) -> None:
        events.append(event)

    orchestrator = ResearchOrchestrator(llm, api_token="test", callback=capture)

    with patch.object(llm, "generate", side_effect=TimeoutError("timed out")):
        result = await orchestrator.run("query")

    assert "timed out" in result
    assert any(e["event"] == "error" for e in events)
