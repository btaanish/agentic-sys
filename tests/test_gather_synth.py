from unittest.mock import AsyncMock, patch

import pytest

from src.agents.gather import GatherAgent
from src.agents.synthesizer import SynthesizerAgent
from src.core.llm_client import LLMClient


@pytest.mark.anyio
async def test_gather_agent_execute():
    llm = LLMClient()
    agent = GatherAgent(llm, api_token="test-token")
    mock_gen = AsyncMock(return_value="research findings")

    with patch.object(llm, "generate", mock_gen):
        result = await agent.execute("What is Python?")

    assert result == "research findings"
    mock_gen.assert_called_once()
    call_args = mock_gen.call_args
    assert "What is Python?" in call_args[0][0]
    assert call_args[1]["api_token"] == "test-token"


@pytest.mark.anyio
async def test_gather_agent_attributes():
    llm = LLMClient()
    agent = GatherAgent(llm)
    assert agent.name == "gather"
    assert agent.description != ""


@pytest.mark.anyio
async def test_synthesizer_agent_execute():
    llm = LLMClient()
    agent = SynthesizerAgent(llm, api_token="test-token")
    mock_gen = AsyncMock(return_value="synthesized answer")

    with patch.object(llm, "generate", mock_gen):
        result = await agent.execute("findings here")

    assert result == "synthesized answer"
    mock_gen.assert_called_once()
    assert "findings here" in mock_gen.call_args[0][0]


@pytest.mark.anyio
async def test_synthesizer_agent_attributes():
    llm = LLMClient()
    agent = SynthesizerAgent(llm)
    assert agent.name == "synthesizer"
    assert agent.description != ""
