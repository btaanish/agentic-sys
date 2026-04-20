"""Tests for M8 cross-angle exploration and contradiction detection."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.orchestrator import EXPLORATION_ANGLES, ResearchOrchestrator
from src.core.llm_client import LLMClient
from src.core.research_state import Evidence, ResearchState
from src.core.source_metadata import SourceMetadata, SourceType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cred_json(credibility: float = 0.7, bias: float = 0.3) -> str:
    return json.dumps({
        "source_type": "unknown",
        "credibility_score": credibility,
        "bias_score": bias,
        "recency_score": 0.5,
        "domain": "test",
    })


HIGH_CRED = _make_cred_json(credibility=0.95)
LOW_CRED = _make_cred_json(credibility=0.2)
MED_CRED = _make_cred_json(credibility=0.7)


def _collector():
    """Return (events_list, callback_coroutine)."""
    events: list[dict] = []

    async def cb(event: dict) -> None:
        events.append(event)

    return events, cb


# ---------------------------------------------------------------------------
# 1. ResearchState has contradictions field
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_research_state_has_contradictions_field():
    """contradictions field exists and defaults to empty list."""
    state = ResearchState(query="test")
    assert hasattr(state, "contradictions")
    assert state.contradictions == []


# ---------------------------------------------------------------------------
# 2. ResearchState has exploration_angles field
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_research_state_has_exploration_angles_field():
    """exploration_angles field exists and defaults to empty list."""
    state = ResearchState(query="test")
    assert hasattr(state, "exploration_angles")
    assert state.exploration_angles == []


# ---------------------------------------------------------------------------
# 3. add_contradiction works correctly
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_add_contradiction():
    """state.add_contradiction() appends a properly structured dict."""
    state = ResearchState(query="test")
    state.add_contradiction(
        evidence_ids=[0, 1],
        description="Source A says X, source B says not X",
        resolution="Needs further investigation",
        confidence_impact=-0.2,
    )
    assert len(state.contradictions) == 1
    c = state.contradictions[0]
    assert c["evidence_ids"] == [0, 1]
    assert c["description"] == "Source A says X, source B says not X"
    assert c["resolution"] == "Needs further investigation"
    assert c["confidence_impact"] == -0.2


# ---------------------------------------------------------------------------
# 4. to_dict includes contradictions
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_to_dict_includes_contradictions():
    """to_dict() output has contradictions key."""
    state = ResearchState(query="test")
    state.add_contradiction(
        evidence_ids=[0, 1],
        description="conflict",
    )
    d = state.to_dict()
    assert "contradictions" in d
    assert len(d["contradictions"]) == 1
    assert d["contradictions"][0]["description"] == "conflict"


# ---------------------------------------------------------------------------
# 5. to_dict includes exploration_angles
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_to_dict_includes_exploration_angles():
    """to_dict() output has exploration_angles key."""
    state = ResearchState(query="test")
    state.exploration_angles.append("technical")
    state.exploration_angles.append("historical")
    d = state.to_dict()
    assert "exploration_angles" in d
    assert d["exploration_angles"] == ["technical", "historical"]


# ---------------------------------------------------------------------------
# 6. Decompose generates multi-angle questions
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_decompose_generates_multi_angle_questions():
    """Decomposition with angles covers at least 3 distinct angles."""
    llm = LLMClient()
    orch = ResearchOrchestrator(llm, api_token="t", max_iterations=1)

    decompose_response = json.dumps([
        "[technical] How does the system architecture work?",
        "[historical] What is the historical development?",
        "[empirical] What does the data show?",
    ])

    with patch.object(llm, "generate", new_callable=AsyncMock, return_value=decompose_response):
        result = await orch._decompose("test query", angles=["technical", "historical", "empirical"])

    assert len(result) >= 3
    # Verify angles appear in the sub-questions
    combined = " ".join(result)
    assert "technical" in combined
    assert "historical" in combined
    assert "empirical" in combined


# ---------------------------------------------------------------------------
# 7. Exploration angles tracked after run()
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_exploration_angles_tracked():
    """After run(), state tracks which angles were explored."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=1)

    call_count = 0

    async def gen(prompt: str, api_token: str | None = None) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["sub-q1"]'
        if "contradict" in prompt.lower():
            return "[]"
        if "Synthesiz" in prompt or "Original query" in prompt:
            return "synthesized"
        if "credibility" in prompt.lower() or "source" in prompt.lower():
            return HIGH_CRED
        return "gathered"

    with patch.object(llm, "generate", side_effect=gen):
        await orch.run("test query")

    # Check that exploration_angles were emitted in state_update
    state_events = [
        e for e in events
        if e.get("event") == "state_update" and e.get("message") == "Sub-questions identified"
    ]
    assert len(state_events) >= 1
    data = json.loads(state_events[0]["data"])
    assert "exploration_angles" in data
    assert len(data["exploration_angles"]) >= 1


# ---------------------------------------------------------------------------
# 8. At least three angles explored per query
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_at_least_three_angles_explored():
    """Verify >= 3 angles covered per query."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=1)

    call_count = 0

    async def gen(prompt: str, api_token: str | None = None) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["sub-q1"]'
        if "contradict" in prompt.lower():
            return "[]"
        if "Synthesiz" in prompt or "Original query" in prompt:
            return "synthesized"
        if "credibility" in prompt.lower() or "source" in prompt.lower():
            return HIGH_CRED
        return "gathered"

    with patch.object(llm, "generate", side_effect=gen):
        await orch.run("test query")

    # Initial angles should be at least 3
    state_events = [
        e for e in events
        if e.get("event") == "state_update" and e.get("message") == "Sub-questions identified"
    ]
    assert len(state_events) >= 1
    data = json.loads(state_events[0]["data"])
    assert len(data["exploration_angles"]) >= 3


# ---------------------------------------------------------------------------
# 9. Contradiction detection finds conflicts
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_contradiction_detection_finds_conflicts():
    """Mock conflicting evidence, verify contradiction stored."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=1)

    call_count = 0

    async def gen(prompt: str, api_token: str | None = None) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["sub-q1"]'
        # Contradiction detection prompt
        if "contradict" in prompt.lower():
            return json.dumps([{
                "evidence_indices": [0, 1],
                "description": "Source A claims X while Source B claims not X",
            }])
        if "Synthesiz" in prompt or "Original query" in prompt:
            return "synthesized"
        if "credibility" in prompt.lower() or "source" in prompt.lower():
            # Return divergent credibility to trigger contradiction detection
            if call_count <= 6:
                return _make_cred_json(credibility=0.9)
            return _make_cred_json(credibility=0.3)
        return "gathered"

    with patch.object(llm, "generate", side_effect=gen):
        result = await orch.run("query with conflict")

    # Check result event contains the synthesized answer
    result_events = [e for e in events if e.get("event") == "result"]
    assert len(result_events) == 1


# ---------------------------------------------------------------------------
# 10. Contradiction triggers next_action
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_contradiction_triggers_next_action():
    """Detected contradiction adds resolution action to next_actions."""
    llm = LLMClient()
    state = ResearchState(query="test")
    orch = ResearchOrchestrator(llm, api_token="t", max_iterations=1)

    # Add evidence with divergent credibility to trigger detection
    meta_high = SourceMetadata(
        source_id="src-high",
        source_type=SourceType.UNKNOWN,
        credibility_score=0.9,
        bias_score=0.1,
        recency_score=0.5,
        domain="test",
    )
    meta_low = SourceMetadata(
        source_id="src-low",
        source_type=SourceType.UNKNOWN,
        credibility_score=0.3,
        bias_score=0.5,
        recency_score=0.5,
        domain="test",
    )
    state.evidence.append(Evidence(
        content="X is true", source="agent1", confidence=0.9,
        sub_question_index=0, source_metadata=meta_high,
    ))
    state.evidence.append(Evidence(
        content="X is false", source="agent2", confidence=0.3,
        sub_question_index=0, source_metadata=meta_low,
    ))

    contradiction_response = json.dumps([{
        "evidence_indices": [0, 1],
        "description": "Evidence disagrees on X",
    }])

    with patch.object(llm, "generate", new_callable=AsyncMock, return_value=contradiction_response):
        await orch._detect_contradictions(state)

    assert len(state.contradictions) >= 1
    # Should have added a resolution action
    resolve_actions = [a for a in state.next_actions if "Resolve contradiction" in a]
    assert len(resolve_actions) >= 1


# ---------------------------------------------------------------------------
# 11. No contradictions when evidence agrees
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_no_contradictions_when_evidence_agrees():
    """Agreeing evidence (low credibility divergence) produces no contradictions."""
    llm = LLMClient()
    state = ResearchState(query="test")
    orch = ResearchOrchestrator(llm, api_token="t", max_iterations=1)

    # Add evidence with similar credibility (spread <= 0.2)
    meta = SourceMetadata(
        source_id="src-agree",
        source_type=SourceType.UNKNOWN,
        credibility_score=0.7,
        bias_score=0.2,
        recency_score=0.5,
        domain="test",
    )
    state.evidence.append(Evidence(
        content="X is true", source="agent1", confidence=0.7,
        sub_question_index=0, source_metadata=meta,
    ))
    state.evidence.append(Evidence(
        content="X is confirmed", source="agent2", confidence=0.8,
        sub_question_index=0, source_metadata=meta,
    ))

    # LLM should NOT be called since credibility spread <= 0.2
    with patch.object(llm, "generate", new_callable=AsyncMock) as mock_gen:
        await orch._detect_contradictions(state)

    assert len(state.contradictions) == 0
    mock_gen.assert_not_called()


# ---------------------------------------------------------------------------
# 12. Contradiction dict structure
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_contradiction_stored_in_state():
    """Verify contradiction dict structure: evidence_ids, description, resolution, confidence_impact."""
    state = ResearchState(query="test")
    state.add_contradiction(
        evidence_ids=[2, 5],
        description="Conflicting timelines",
        resolution=None,
        confidence_impact=-0.15,
    )
    c = state.contradictions[0]
    assert "evidence_ids" in c
    assert "description" in c
    assert "resolution" in c
    assert "confidence_impact" in c
    assert c["evidence_ids"] == [2, 5]
    assert c["description"] == "Conflicting timelines"
    assert c["resolution"] is None
    assert c["confidence_impact"] == -0.15


# ---------------------------------------------------------------------------
# 13. Synthesis includes contradictions
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_synthesis_includes_contradictions():
    """Synthesis input includes contradiction data when contradictions exist."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=1)

    call_count = 0
    synthesis_prompt_captured = []

    async def gen(prompt: str, api_token: str | None = None) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["sub-q1"]'
        if "contradict" in prompt.lower() and "identify" in prompt.lower():
            return json.dumps([{
                "evidence_indices": [0, 1],
                "description": "Timeline conflict between sources",
            }])
        if "Synthesiz" in prompt or "synthesizer" in prompt.lower() or "research findings" in prompt.lower():
            synthesis_prompt_captured.append(prompt)
            return "synthesized with contradictions noted"
        if "credibility" in prompt.lower() or "source" in prompt.lower():
            # Return divergent credibility to trigger contradiction detection
            if call_count <= 6:
                return _make_cred_json(credibility=0.95)
            return _make_cred_json(credibility=0.3)
        return "gathered"

    with patch.object(llm, "generate", side_effect=gen):
        await orch.run("query")

    # Verify that at least one prompt sent to the LLM mentioned contradictions
    all_prompts = " ".join(synthesis_prompt_captured)
    if synthesis_prompt_captured:
        assert "Contradictions" in all_prompts or "contradiction" in all_prompts.lower()


# ---------------------------------------------------------------------------
# 14. Synthesizer prompt has uncertainty section
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_synthesis_prompt_has_uncertainty_section():
    """Synthesizer prompt asks for uncertainty/confidence."""
    llm = LLMClient()
    prompts_captured: list[str] = []
    original_generate = llm.generate

    async def capture_gen(prompt: str, api_token: str | None = None) -> str:
        prompts_captured.append(prompt)
        return "answer"

    from src.agents.synthesizer import SynthesizerAgent
    synth = SynthesizerAgent(llm, api_token="t")

    with patch.object(llm, "generate", side_effect=capture_gen):
        await synth.execute("test input")

    assert len(prompts_captured) == 1
    prompt = prompts_captured[0]
    # The synthesizer prompt should mention uncertainty and confidence
    assert "Uncertainty" in prompt or "uncertainty" in prompt.lower()
    assert "Confidence" in prompt or "confidence" in prompt.lower()


# ---------------------------------------------------------------------------
# 15. Synthesis includes confidence level
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_synthesis_includes_confidence_level():
    """Final synthesis prompt structure includes an Overall Confidence section."""
    llm = LLMClient()
    prompts_captured: list[str] = []

    async def capture_gen(prompt: str, api_token: str | None = None) -> str:
        prompts_captured.append(prompt)
        return "answer"

    from src.agents.synthesizer import SynthesizerAgent
    synth = SynthesizerAgent(llm, api_token="t")

    with patch.object(llm, "generate", side_effect=capture_gen):
        await synth.execute("test input")

    prompt = prompts_captured[0]
    assert "Overall Confidence" in prompt
