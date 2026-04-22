from unittest.mock import AsyncMock, patch

import pytest

from src.agents.retrieval_agent import RetrievalAgent
from src.core.llm_client import LLMClient
from src.core.research_state import ResearchState


@pytest.mark.anyio
async def test_retrieval_agent_attributes():
    llm = LLMClient()
    agent = RetrievalAgent(llm)
    assert agent.name == "retrieval"
    assert agent.description != ""


@pytest.mark.anyio
async def test_retrieval_agent_execute_returns_result():
    llm = LLMClient()
    agent = RetrievalAgent(llm, api_token="test-token")
    mock_gen = AsyncMock(return_value="retrieved sources")

    with patch.object(llm, "generate", mock_gen):
        result = await agent.execute("What is the GDP of France in 2024?")

    assert result == "retrieved sources"
    mock_gen.assert_called_once()
    assert "France" in mock_gen.call_args[0][0]


@pytest.mark.anyio
async def test_retrieval_agent_enables_web_search_tool():
    llm = LLMClient()
    agent = RetrievalAgent(llm, api_token="test-token")
    mock_gen = AsyncMock(return_value="retrieved")

    with patch.object(llm, "generate", mock_gen):
        await agent.execute("query")

    kwargs = mock_gen.call_args[1]
    assert "tools" in kwargs
    tools = kwargs["tools"]
    assert isinstance(tools, list)
    assert len(tools) == 1
    assert tools[0]["type"] == "web_search_20250305"
    assert tools[0]["name"] == "web_search"


@pytest.mark.anyio
async def test_retrieval_agent_adds_evidence_to_state():
    llm = LLMClient()
    agent = RetrievalAgent(llm)
    state = ResearchState(query="query")
    mock_gen = AsyncMock(return_value="retrieved content")

    with patch.object(llm, "generate", mock_gen):
        await agent.execute("query", state=state, sub_question_index=0)

    assert len(state.evidence) == 1
    assert state.evidence[0].source == "retrieval"
    assert state.evidence[0].confidence >= 0.8
    assert state.evidence[0].sub_question_index == 0
    assert state.evidence[0].content == "retrieved content"
