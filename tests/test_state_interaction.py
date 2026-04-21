"""Tests verifying agents directly read from and write to ResearchState."""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.context_agent import ContextAgent
from src.agents.counterexample_agent import CounterexampleAgent
from src.agents.evidence_agent import EvidenceAgent
from src.agents.gap_detection_agent import GapDetectionAgent
from src.agents.synthesizer import SynthesizerAgent
from src.core.llm_client import LLMClient
from src.core.research_state import ResearchState


@pytest.mark.anyio
async def test_context_agent_writes_evidence_to_state():
    llm = LLMClient()
    state = ResearchState(query="test")
    mock_gen = AsyncMock(return_value="context result")

    with patch.object(llm, "generate", mock_gen):
        agent = ContextAgent(llm, api_token="t")
        await agent.execute("q", state, sub_question_index=0)

    assert len(state.evidence) == 1
    assert state.evidence[0].source == "context"
    assert state.evidence[0].confidence == 0.7
    assert state.evidence[0].content == "context result"


@pytest.mark.anyio
async def test_evidence_agent_reads_existing_state_and_writes():
    llm = LLMClient()
    state = ResearchState(query="test")
    state.add_evidence("prior finding", source="context", confidence=0.7, sub_question_index=0)

    mock_gen = AsyncMock(return_value="new evidence")

    with patch.object(llm, "generate", mock_gen):
        agent = EvidenceAgent(llm, api_token="t")
        await agent.execute("q", state, sub_question_index=0)

    # Should have 2 evidence entries now
    assert len(state.evidence) == 2
    assert state.evidence[1].source == "evidence"
    assert state.evidence[1].confidence == 0.8
    # Prompt should include existing findings
    prompt_sent = mock_gen.call_args[0][0]
    assert "prior finding" in prompt_sent


@pytest.mark.anyio
async def test_counterexample_agent_writes_evidence_and_unresolved():
    llm = LLMClient()
    state = ResearchState(query="test")
    mock_gen = AsyncMock(return_value="counterexample found")

    with patch.object(llm, "generate", mock_gen):
        agent = CounterexampleAgent(llm, api_token="t")
        await agent.execute("claim", state, sub_question_index=1)

    assert len(state.evidence) == 1
    assert state.evidence[0].source == "counterexample"
    assert state.evidence[0].confidence == 0.6
    assert state.evidence[0].sub_question_index == 1
    assert len(state.unresolved_issues) == 1
    assert "Counterexamples found" in state.unresolved_issues[0]


@pytest.mark.anyio
async def test_gap_detection_agent_reads_state_and_writes_unresolved():
    llm = LLMClient()
    state = ResearchState(query="test")
    state.add_evidence("existing coverage", source="evidence", confidence=0.8, sub_question_index=0)

    mock_gen = AsyncMock(return_value="gaps found")

    with patch.object(llm, "generate", mock_gen):
        agent = GapDetectionAgent(llm, api_token="t")
        await agent.execute("q", state, sub_question_index=0)

    assert len(state.evidence) == 2
    assert state.evidence[1].source == "gap_detection"
    assert state.evidence[1].confidence == 0.5
    assert len(state.unresolved_issues) == 1
    assert "Gaps identified" in state.unresolved_issues[0]
    # Prompt should include existing evidence
    prompt_sent = mock_gen.call_args[0][0]
    assert "existing coverage" in prompt_sent


@pytest.mark.anyio
async def test_gap_detection_different_output_with_empty_vs_populated_state():
    """GapDetectionAgent builds different prompts depending on existing evidence."""
    llm = LLMClient()
    prompts_sent = []

    async def capture_prompt(prompt: str, api_token=None, **_kwargs):
        prompts_sent.append(prompt)
        return "result"

    # Empty state
    state_empty = ResearchState(query="test")
    with patch.object(llm, "generate", side_effect=capture_prompt):
        agent = GapDetectionAgent(llm, api_token="t")
        await agent.execute("q", state_empty, sub_question_index=0)

    # Populated state
    state_full = ResearchState(query="test")
    state_full.add_evidence("some finding", source="context", confidence=0.7, sub_question_index=0)
    with patch.object(llm, "generate", side_effect=capture_prompt):
        agent2 = GapDetectionAgent(llm, api_token="t")
        await agent2.execute("q", state_full, sub_question_index=0)

    assert len(prompts_sent) == 2
    assert "Already covered" not in prompts_sent[0]
    assert "Already covered" in prompts_sent[1]
    assert "some finding" in prompts_sent[1]


@pytest.mark.anyio
async def test_synthesizer_accepts_state_parameter():
    """SynthesizerAgent matches BaseAgent signature with state parameter."""
    llm = LLMClient()
    state = ResearchState(query="test")
    mock_gen = AsyncMock(return_value="synthesis")

    with patch.object(llm, "generate", mock_gen):
        agent = SynthesizerAgent(llm, api_token="t")
        result = await agent.execute("findings", state, sub_question_index=0)

    assert result == "synthesis"
