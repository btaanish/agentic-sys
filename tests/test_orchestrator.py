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

    async def mock_generate(prompt: str, api_token: str | None = None) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Decompose call
            return '["sub-q1", "sub-q2"]'
        elif call_count <= 9:
            # Gather calls: 4 agents x 2 sub-questions = 8 calls
            return f"findings for call {call_count}"
        else:
            # Synthesize call
            return "final synthesized answer"

    with patch.object(llm, "generate", side_effect=mock_generate):
        result = await orchestrator.run("test query")

    assert result == "final synthesized answer"
    assert call_count == 10  # 1 decompose + 8 gather (4 agents x 2 sub-q) + 1 synthesize

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

    async def mock_generate(prompt: str, api_token: str | None = None) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["q1"]'
        elif call_count <= 5:
            return "gathered"
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

    async def mock_generate(prompt: str, api_token: str | None = None) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "not valid json"
        elif call_count <= 5:
            return "gathered"
        else:
            return "synthesized"

    with patch.object(llm, "generate", side_effect=mock_generate):
        result = await orchestrator.run("original query")

    assert result == "synthesized"
    assert call_count == 6  # 1 decompose + 4 gather (4 agents x 1 fallback sub-q) + 1 synthesize


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
