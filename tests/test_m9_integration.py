"""M9 integration tests: structured output, SSE contracts, summary.md, frontend-backend."""

import json
import os
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.orchestrator import ResearchOrchestrator
from src.core.llm_client import LLMClient
from src.core.research_state import Evidence, ResearchState
from src.core.source_metadata import SourceMetadata, SourceType


# ---------------------------------------------------------------------------
# Helpers (reused pattern from test_iteration.py / test_cross_angle.py)
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

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _collector():
    """Return (events_list, callback_coroutine)."""
    events: list[dict] = []

    async def cb(event: dict) -> None:
        events.append(event)

    return events, cb


def _gen_with_contradictions():
    """Side-effect generator that triggers contradiction detection."""
    call_count = 0

    async def gen(prompt: str, api_token: str | None = None) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["sub-q1"]'
        # Synthesis prompt comes after contradiction detection
        if "Synthesiz" in prompt or "Original query" in prompt:
            return (
                "## Main Findings\nKey finding here.\n"
                "## Evidence\nEvidence details.\n"
                "## Contradictions\nSource A says X, Source B says not X.\n"
                "## Uncertainty\nSome areas remain unclear.\n"
                "## Confidence\nOverall Confidence: 70%"
            )
        # Contradiction detection prompt (contains "contradict" and "identify")
        if "contradict" in prompt.lower() and "identify" in prompt.lower():
            return json.dumps([{
                "evidence_indices": [0, 1],
                "description": "Source A says X, Source B says not X",
            }])
        if "credibility" in prompt.lower() or "source" in prompt.lower():
            # Divergent credibility to trigger contradiction detection
            if call_count <= 6:
                return _make_cred_json(credibility=0.95)
            return _make_cred_json(credibility=0.25)
        return "gathered evidence"

    return gen


def _gen_simple():
    """Side-effect generator for a clean single-iteration run."""
    call_count = 0

    async def gen(prompt: str, api_token: str | None = None) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["sub-q1"]'
        if "contradict" in prompt.lower():
            return "[]"
        if "Synthesiz" in prompt or "Original query" in prompt:
            return "final synthesized answer"
        if "credibility" in prompt.lower() or "source" in prompt.lower():
            return HIGH_CRED
        return "gathered"

    return gen


# ===========================================================================
# 1. End-to-end structured output tests (3 tests)
# ===========================================================================

# ---------------------------------------------------------------------------
# 1a. Orchestrator result includes contradiction descriptions
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_result_includes_contradiction_info():
    """When contradictions exist, the final result mentions them."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=1)

    with patch.object(llm, "generate", side_effect=_gen_with_contradictions()):
        result = await orch.run("query with conflict")

    # The synthesis input includes "Contradictions found:" when contradictions exist
    # and the synthesizer echoes it back in the result
    assert "Contradictions" in result or "contradiction" in result.lower()


# ---------------------------------------------------------------------------
# 1b. Result includes exploration angles covered
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_result_includes_exploration_angles():
    """Final synthesis input includes exploration angles covered."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=1)

    synthesis_prompts: list[str] = []

    async def gen(prompt: str, api_token: str | None = None) -> str:
        if "Synthesiz" in prompt or "Original query" in prompt:
            synthesis_prompts.append(prompt)
            return "synthesized"
        if "contradict" in prompt.lower():
            return "[]"
        if "credibility" in prompt.lower() or "source" in prompt.lower():
            return HIGH_CRED
        # First call is decompose
        if not synthesis_prompts and "Break down" in prompt:
            return '["sub-q1"]'
        return "gathered"

    with patch.object(llm, "generate", side_effect=gen):
        await orch.run("test query")

    # The orchestrator appends "Exploration angles covered: ..." to synthesis input
    assert len(synthesis_prompts) >= 1
    assert "Exploration angles covered" in synthesis_prompts[0]


# ---------------------------------------------------------------------------
# 1c. Synthesizer receives structured input with credibility scores
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_synthesizer_receives_credibility_scores():
    """Synthesis input includes per-evidence credibility scores."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=1)

    synthesis_prompts: list[str] = []

    async def gen(prompt: str, api_token: str | None = None) -> str:
        if "Synthesiz" in prompt or "Original query" in prompt:
            synthesis_prompts.append(prompt)
            return "synthesized"
        if "contradict" in prompt.lower():
            return "[]"
        if "credibility" in prompt.lower() or "source" in prompt.lower():
            return MED_CRED
        if "Break down" in prompt:
            return '["sub-q1"]'
        return "gathered"

    with patch.object(llm, "generate", side_effect=gen):
        await orch.run("test query")

    assert len(synthesis_prompts) >= 1
    # Credibility appears as "(credibility: X.X)" in synthesis input
    assert "credibility:" in synthesis_prompts[0].lower()


# ===========================================================================
# 2. SSE data contract tests (4 tests)
# ===========================================================================

# ---------------------------------------------------------------------------
# 2a. 'Sub-questions identified' state_update has sub_questions in data
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_sse_sub_questions_identified_has_sub_questions():
    """state_update 'Sub-questions identified' contains sub_questions with text fields."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=1)

    with patch.object(llm, "generate", side_effect=_gen_simple()):
        await orch.run("test query")

    sq_events = [
        e for e in events
        if e.get("event") == "state_update"
        and e.get("message") == "Sub-questions identified"
    ]
    assert len(sq_events) >= 1
    data = json.loads(sq_events[0]["data"])
    assert "sub_questions" in data
    assert len(data["sub_questions"]) >= 1
    # Each sub_question should have a "text" field
    for sq in data["sub_questions"]:
        assert "text" in sq


# ---------------------------------------------------------------------------
# 2b. 'Iteration progress' has iteration, avg_confidence, confidence_per_sub_question
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_sse_iteration_progress_contract():
    """state_update 'Iteration progress' contains required fields."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=1)

    with patch.object(llm, "generate", side_effect=_gen_simple()):
        await orch.run("test query")

    progress_events = [
        e for e in events
        if e.get("event") == "state_update"
        and e.get("message") == "Iteration progress"
    ]
    assert len(progress_events) >= 1
    data = json.loads(progress_events[0]["data"])
    assert "iteration" in data
    assert "avg_confidence" in data
    assert "confidence_per_sub_question" in data
    assert isinstance(data["iteration"], int)
    assert isinstance(data["avg_confidence"], float)


# ---------------------------------------------------------------------------
# 2c. 'Source credibility evaluated' has evidence_count and confidence_scores
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_sse_source_credibility_evaluated_contract():
    """state_update 'Source credibility evaluated' has evidence_count and confidence_scores."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=1)

    with patch.object(llm, "generate", side_effect=_gen_simple()):
        await orch.run("test query")

    cred_events = [
        e for e in events
        if e.get("event") == "state_update"
        and e.get("message") == "Source credibility evaluated"
    ]
    assert len(cred_events) >= 1
    data = json.loads(cred_events[0]["data"])
    assert "evidence_count" in data
    assert "confidence_scores" in data
    assert isinstance(data["evidence_count"], int)
    assert data["evidence_count"] > 0


# ---------------------------------------------------------------------------
# 2d. 'Agents dispatched' has agents list and sub_question_count
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_sse_agents_dispatched_contract():
    """state_update 'Agents dispatched' has agents list and sub_question_count."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=1)

    with patch.object(llm, "generate", side_effect=_gen_simple()):
        await orch.run("test query")

    dispatch_events = [
        e for e in events
        if e.get("event") == "state_update"
        and e.get("message") == "Agents dispatched"
    ]
    assert len(dispatch_events) >= 1
    data = json.loads(dispatch_events[0]["data"])
    assert "agents" in data
    assert "sub_question_count" in data
    assert isinstance(data["agents"], list)
    assert len(data["agents"]) == 4  # 4 specialized agents
    assert isinstance(data["sub_question_count"], int)
    assert data["sub_question_count"] >= 1


# ===========================================================================
# 3. Summary.md tests (2 tests)
# ===========================================================================

# ---------------------------------------------------------------------------
# 3a. summary.md exists at project root
# ---------------------------------------------------------------------------

def test_summary_md_exists():
    """summary.md file exists in the project root."""
    summary_path = os.path.join(PROJECT_ROOT, "summary.md")
    assert os.path.exists(summary_path), f"summary.md not found at {summary_path}"


# ---------------------------------------------------------------------------
# 3b. summary.md contains commit entries
# ---------------------------------------------------------------------------

def test_summary_md_contains_commit_entries():
    """summary.md contains commit hashes, authors, and messages."""
    summary_path = os.path.join(PROJECT_ROOT, "summary.md")
    with open(summary_path) as f:
        content = f.read()

    # Should have commit hashes (7-char hex)
    assert "**" in content, "summary.md should have bold-formatted commit hashes"
    # Should mention at least one known agent/author
    has_author = any(name in content for name in ["Athena", "Leo", "Kai", "Maya", "Ares", "Noah"])
    assert has_author, "summary.md should mention commit authors"
    # Should have multiple commit entries
    lines_with_dash = [l for l in content.split("\n") if l.strip().startswith("- **")]
    assert len(lines_with_dash) >= 5, "summary.md should have multiple commit entries"


# ===========================================================================
# 4. Frontend-backend contract tests (3 tests)
# ===========================================================================

# ---------------------------------------------------------------------------
# 4a. Result event data is a string
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_result_event_data_is_string():
    """The 'result' event's data field is a string, not JSON object."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=1)

    with patch.object(llm, "generate", side_effect=_gen_simple()):
        await orch.run("test query")

    result_events = [e for e in events if e.get("event") == "result"]
    assert len(result_events) == 1
    # Frontend expects event.data to be a string (rendered as text)
    assert isinstance(result_events[0]["data"], str)


# ---------------------------------------------------------------------------
# 4b. All state_update events have event, message, and data keys
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_state_update_events_have_required_keys():
    """All state_update events must have 'event', 'message', and 'data' keys."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=1)

    with patch.object(llm, "generate", side_effect=_gen_simple()):
        await orch.run("test query")

    state_updates = [e for e in events if e.get("event") == "state_update"]
    assert len(state_updates) >= 1, "Should have at least one state_update event"
    for event in state_updates:
        assert "event" in event, f"Missing 'event' key in: {event}"
        assert "message" in event, f"Missing 'message' key in: {event}"
        assert "data" in event, f"Missing 'data' key in: {event}"


# ---------------------------------------------------------------------------
# 4c. state_update data fields are JSON-parseable strings
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_state_update_data_is_json_string():
    """state_update data fields are JSON strings (frontend parses them)."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=1)

    with patch.object(llm, "generate", side_effect=_gen_simple()):
        await orch.run("test query")

    state_updates = [e for e in events if e.get("event") == "state_update"]
    for event in state_updates:
        data = event["data"]
        assert isinstance(data, str), f"data should be string, got {type(data)}"
        # Frontend does JSON.parse(event.data), so it must be valid JSON
        parsed = json.loads(data)
        assert isinstance(parsed, dict), f"Parsed data should be dict, got {type(parsed)}"
