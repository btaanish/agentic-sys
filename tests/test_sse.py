import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.anyio
async def test_sse_endpoint_streams_events():
    """Integration test: POST /research returns SSE event stream."""
    call_count = 0

    async def mock_generate(prompt: str, api_token: str | None = None, **_kwargs: object) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["sub-question-1"]'
        elif call_count <= 6:
            # 5 agents x 1 sub-question = 5 gather calls
            return "research findings"
        else:
            return "final answer"

    with patch("src.core.llm_client.LLMClient.generate", side_effect=mock_generate):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/research",
                json={"query": "test query", "api_token": "fake-token"},
                timeout=30.0,
            )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    # Parse SSE events
    events = []
    for line in response.text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            data = json.loads(line[6:])
            events.append(data)

    # Should have status events and a result event
    assert len(events) >= 3
    assert any(e["event"] == "status" for e in events)
    assert any(e["event"] == "result" for e in events)
    result_event = next(e for e in events if e["event"] == "result")
    assert result_event["data"] == "final answer"


@pytest.mark.anyio
async def test_sse_endpoint_error_handling():
    """SSE endpoint handles LLM errors gracefully."""
    import anthropic

    with patch(
        "src.core.llm_client.LLMClient.generate",
        side_effect=anthropic.AuthenticationError(
            message="bad key",
            response=AsyncMock(status_code=401),
            body=None,
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/research",
                json={"query": "test", "api_token": "bad"},
                timeout=30.0,
            )

    assert response.status_code == 200  # SSE stream still returns 200
    events = []
    for line in response.text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    assert any(e["event"] == "error" for e in events)
