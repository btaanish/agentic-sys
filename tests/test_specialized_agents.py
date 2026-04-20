from unittest.mock import AsyncMock, patch

import pytest

from src.agents.context_agent import ContextAgent
from src.agents.counterexample_agent import CounterexampleAgent
from src.agents.evidence_agent import EvidenceAgent
from src.agents.gap_detection_agent import GapDetectionAgent
from src.core.llm_client import LLMClient


@pytest.mark.anyio
async def test_context_agent_attributes():
    llm = LLMClient()
    agent = ContextAgent(llm)
    assert agent.name == "context"
    assert agent.description != ""


@pytest.mark.anyio
async def test_context_agent_execute():
    llm = LLMClient()
    agent = ContextAgent(llm, api_token="test-token")
    mock_gen = AsyncMock(return_value="background context")

    with patch.object(llm, "generate", mock_gen):
        result = await agent.execute("What is quantum computing?")

    assert result == "background context"
    mock_gen.assert_called_once()
    assert "quantum computing" in mock_gen.call_args[0][0]
    assert mock_gen.call_args[1]["api_token"] == "test-token"


@pytest.mark.anyio
async def test_evidence_agent_attributes():
    llm = LLMClient()
    agent = EvidenceAgent(llm)
    assert agent.name == "evidence"
    assert agent.description != ""


@pytest.mark.anyio
async def test_evidence_agent_execute():
    llm = LLMClient()
    agent = EvidenceAgent(llm, api_token="test-token")
    mock_gen = AsyncMock(return_value="evidence found")

    with patch.object(llm, "generate", mock_gen):
        result = await agent.execute("Does X cause Y?")

    assert result == "evidence found"
    mock_gen.assert_called_once()
    assert "Does X cause Y?" in mock_gen.call_args[0][0]
    assert mock_gen.call_args[1]["api_token"] == "test-token"


@pytest.mark.anyio
async def test_counterexample_agent_attributes():
    llm = LLMClient()
    agent = CounterexampleAgent(llm)
    assert agent.name == "counterexample"
    assert agent.description != ""


@pytest.mark.anyio
async def test_counterexample_agent_execute():
    llm = LLMClient()
    agent = CounterexampleAgent(llm, api_token="test-token")
    mock_gen = AsyncMock(return_value="counterexample found")

    with patch.object(llm, "generate", mock_gen):
        result = await agent.execute("All swans are white")

    assert result == "counterexample found"
    mock_gen.assert_called_once()
    assert "All swans are white" in mock_gen.call_args[0][0]
    assert mock_gen.call_args[1]["api_token"] == "test-token"


@pytest.mark.anyio
async def test_gap_detection_agent_attributes():
    llm = LLMClient()
    agent = GapDetectionAgent(llm)
    assert agent.name == "gap_detection"
    assert agent.description != ""


@pytest.mark.anyio
async def test_gap_detection_agent_execute():
    llm = LLMClient()
    agent = GapDetectionAgent(llm, api_token="test-token")
    mock_gen = AsyncMock(return_value="gaps identified")

    with patch.object(llm, "generate", mock_gen):
        result = await agent.execute("How does climate change affect oceans?")

    assert result == "gaps identified"
    mock_gen.assert_called_once()
    assert "climate change" in mock_gen.call_args[0][0]
    assert mock_gen.call_args[1]["api_token"] == "test-token"
