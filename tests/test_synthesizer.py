from unittest.mock import AsyncMock, patch

import pytest

from src.agents.synthesizer import SynthesizerAgent, _strip_forbidden_sections
from src.core.llm_client import LLMClient


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


@pytest.mark.anyio
async def test_synthesizer_strips_forbidden_sections_from_llm_output():
    llm = LLMClient()
    agent = SynthesizerAgent(llm, api_token="t")
    llm_output = (
        "## 1. Main Findings\n"
        "The answer is X.\n\n"
        "## 2. Supporting Evidence\n"
        "Source A says X.\n\n"
        "## 3. Remaining Uncertainty\n"
        "We don't know Y.\n\n"
        "## 4. Overall Confidence\n"
        "Medium. Based on one source.\n"
    )
    with patch.object(llm, "generate", AsyncMock(return_value=llm_output)):
        result = await agent.execute("findings")

    assert "Main Findings" in result
    assert "Supporting Evidence" in result
    assert "Remaining Uncertainty" not in result
    assert "Overall Confidence" not in result
    assert "We don't know Y" not in result
    assert "Medium. Based on one source" not in result


def test_strip_forbidden_sections_atx_headings():
    text = (
        "### 1. Main Findings\n"
        "body1\n\n"
        "### 2. Supporting Evidence\n"
        "body2\n\n"
        "### 3. Remaining Uncertainty\n"
        "hidden\n\n"
        "### 4. Overall Confidence\n"
        "hidden too\n"
    )
    out = _strip_forbidden_sections(text)
    assert "body1" in out
    assert "body2" in out
    assert "hidden" not in out
    assert "Remaining Uncertainty" not in out
    assert "Overall Confidence" not in out


def test_strip_forbidden_sections_bold_headings():
    text = (
        "**1. Main Findings**\n"
        "body1\n\n"
        "**2. Supporting Evidence**\n"
        "body2\n\n"
        "**Remaining Uncertainty**\n"
        "hidden\n\n"
        "**Overall Confidence**\n"
        "hidden too\n"
    )
    out = _strip_forbidden_sections(text)
    assert "body1" in out
    assert "body2" in out
    assert "hidden" not in out


def test_strip_forbidden_sections_preserves_inline_mentions():
    text = (
        "## Main Findings\n"
        "The remaining uncertainty is large, per source A.\n"
        "Overall confidence in this claim is low.\n"
    )
    out = _strip_forbidden_sections(text)
    # Inline mentions inside a non-forbidden section are preserved.
    assert "remaining uncertainty" in out
    assert "Overall confidence" in out


def test_strip_forbidden_sections_forbidden_not_at_end():
    text = (
        "## Main Findings\n"
        "body1\n\n"
        "## Remaining Uncertainty\n"
        "hidden\n\n"
        "## Supporting Evidence\n"
        "body2\n"
    )
    out = _strip_forbidden_sections(text)
    assert "body1" in out
    assert "body2" in out
    assert "hidden" not in out
    assert "Remaining Uncertainty" not in out

