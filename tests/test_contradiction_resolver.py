import json
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.contradiction_resolver import ContradictionResolverAgent
from src.core.llm_client import LLMClient


@pytest.mark.anyio
async def test_contradiction_resolver_attributes():
    llm = LLMClient()
    agent = ContradictionResolverAgent(llm)
    assert agent.name == "contradiction_resolver"
    assert agent.description != ""


@pytest.mark.anyio
async def test_contradiction_resolver_parses_json():
    llm = LLMClient()
    agent = ContradictionResolverAgent(llm, api_token="t")
    response = json.dumps({
        "resolution_type": "resolved_for_a",
        "preferred_evidence_id": 0,
        "explanation": "Evidence 0 is a primary source; evidence 1 is a blog.",
        "confidence_impact": 0.05,
    })

    with patch.object(llm, "generate", AsyncMock(return_value=response)):
        result = await agent.resolve(
            "Claim A vs claim B",
            [
                (0, "primary", "X is true per official doc", 0.9),
                (1, "blog", "Some blogger says X is false", 0.2),
            ],
        )

    assert result["resolution_type"] == "resolved_for_a"
    assert result["preferred_evidence_id"] == 0
    assert "primary source" in result["explanation"].lower()
    assert result["confidence_impact"] == 0.05


@pytest.mark.anyio
async def test_contradiction_resolver_open_when_unparseable():
    llm = LLMClient()
    agent = ContradictionResolverAgent(llm, api_token="t")

    with patch.object(llm, "generate", AsyncMock(return_value="not valid json")):
        result = await agent.resolve(
            "Claim A vs claim B",
            [(0, "s1", "A", 0.5), (1, "s2", "B", 0.5)],
        )

    assert result["resolution_type"] == "open"
    assert result["preferred_evidence_id"] is None


@pytest.mark.anyio
async def test_contradiction_resolver_prompt_includes_evidence():
    llm = LLMClient()
    agent = ContradictionResolverAgent(llm, api_token="t")
    mock_gen = AsyncMock(return_value='{"resolution_type": "open"}')

    with patch.object(llm, "generate", mock_gen):
        await agent.resolve(
            "conflict about date",
            [
                (3, "nyt", "happened in 2023", 0.8),
                (7, "blog", "happened in 2022", 0.3),
            ],
        )

    prompt = mock_gen.call_args[0][0]
    assert "conflict about date" in prompt
    assert "Evidence 3" in prompt
    assert "Evidence 7" in prompt
    assert "happened in 2023" in prompt
    assert "happened in 2022" in prompt
