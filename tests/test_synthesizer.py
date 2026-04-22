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
async def test_synthesizer_drops_meta_sections_from_llm_output():
    """Meta-sections about the research process must never reach the user."""
    llm = LLMClient()
    agent = SynthesizerAgent(llm, api_token="t")
    llm_output = (
        "## The topic\n"
        "This is the substantive answer.\n\n"
        "## Contradictions and Unresolved Tensions\n"
        "meta-commentary about conflicts\n\n"
        "## Remaining Uncertainty\n"
        "meta-commentary about gaps\n\n"
        "## Supporting Evidence\n"
        "citation list\n\n"
        "## Overall Confidence\n"
        "medium\n"
    )
    with patch.object(llm, "generate", AsyncMock(return_value=llm_output)):
        result = await agent.execute("findings")

    assert "substantive answer" in result
    assert "Contradictions" not in result
    assert "Unresolved Tensions" not in result
    assert "Remaining Uncertainty" not in result
    assert "Supporting Evidence" not in result
    assert "Overall Confidence" not in result
    assert "meta-commentary" not in result
    assert "citation list" not in result


@pytest.mark.anyio
async def test_synthesizer_unwraps_synthesis_answer_heading():
    """The model sometimes wraps the real answer under a meta heading like
    'Synthesis Answer to Original Question'. The heading must be stripped
    but the content preserved — otherwise the user sees nothing."""
    llm = LLMClient()
    agent = SynthesizerAgent(llm, api_token="t")
    llm_output = (
        "## Synthesis Answer to Original Question\n"
        "The answer is that parallels exist and they matter for X.\n\n"
        "Further elaboration on the topic here.\n"
    )
    with patch.object(llm, "generate", AsyncMock(return_value=llm_output)):
        result = await agent.execute("findings")

    assert "Synthesis Answer" not in result
    assert "The answer is that parallels exist" in result
    assert "Further elaboration on the topic" in result


def test_strip_drop_section_atx_headings():
    text = (
        "### The topic\n"
        "body1\n\n"
        "### Contradictions Found\n"
        "hidden\n\n"
        "### Remaining Uncertainty\n"
        "hidden too\n\n"
        "### Overall Confidence\n"
        "also hidden\n"
    )
    out = _strip_forbidden_sections(text)
    assert "body1" in out
    assert "hidden" not in out
    assert "Contradictions" not in out
    assert "Remaining Uncertainty" not in out
    assert "Overall Confidence" not in out


def test_strip_drop_section_bold_headings():
    text = (
        "**The topic**\n"
        "body1\n\n"
        "**Supporting Evidence**\n"
        "hidden\n\n"
        "**Overall Confidence**\n"
        "hidden too\n"
    )
    out = _strip_forbidden_sections(text)
    assert "body1" in out
    assert "hidden" not in out
    assert "Supporting Evidence" not in out


def test_strip_preserves_inline_mentions():
    text = (
        "## Part of the topic\n"
        "There is remaining uncertainty about X, per the literature.\n"
        "Overall confidence in this claim is low.\n"
    )
    out = _strip_forbidden_sections(text)
    assert "remaining uncertainty" in out
    assert "Overall confidence" in out


def test_strip_drop_section_not_at_end():
    text = (
        "## The topic\n"
        "body1\n\n"
        "## Contradictions\n"
        "hidden\n\n"
        "## Another aspect\n"
        "body2\n"
    )
    out = _strip_forbidden_sections(text)
    assert "body1" in out
    assert "body2" in out
    assert "hidden" not in out
    assert "Contradictions" not in out


def test_strip_unwrap_heading_preserves_content():
    text = (
        "## Main Findings\n"
        "The substantive answer lives here.\n"
        "More detail follows.\n"
    )
    out = _strip_forbidden_sections(text)
    assert "Main Findings" not in out
    assert "substantive answer" in out
    assert "More detail follows" in out


def test_strip_handles_synthesis_answer_variants():
    for heading in [
        "## Synthesis Answer",
        "## Synthesis Answer to Original Question",
        "## Synthesis Answer to the Original Question",
        "**Synthesis Answer to Original Question**",
    ]:
        text = f"{heading}\nThe real answer.\n"
        out = _strip_forbidden_sections(text)
        assert "Synthesis Answer" not in out, heading
        assert "The real answer" in out, heading


def test_strip_drops_contradictions_and_unresolved_tensions():
    text = (
        "## The topic\n"
        "body1\n\n"
        "## Contradictions and Unresolved Tensions\n"
        "hidden meta text\n"
    )
    out = _strip_forbidden_sections(text)
    assert "body1" in out
    assert "Contradictions" not in out
    assert "Unresolved Tensions" not in out
    assert "hidden meta text" not in out
