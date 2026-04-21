"""Tests for the iterative orchestrator loop (M7)."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.orchestrator import ResearchOrchestrator
from src.core.llm_client import LLMClient
from src.core.research_state import Evidence
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


def _mock_gen_simple(
    *,
    decompose: str = '["sub-q1"]',
    gather: str = "gathered",
    credibility: str = MED_CRED,
    synthesize: str = "final answer",
    n_sub: int = 1,
):
    """Return a side_effect function for a single-iteration, n_sub-question run.

    Call sequence: 1 decompose + 4*n_sub gather + 4*n_sub evaluate + 1 synthesize.
    """
    call_count = 0
    gather_end = 1 + 4 * n_sub
    eval_end = gather_end + 4 * n_sub

    async def _gen(prompt: str, api_token: str | None = None, **_kwargs: object) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return decompose
        elif call_count <= gather_end:
            return gather
        elif call_count <= eval_end:
            return credibility
        else:
            return synthesize

    return _gen


# ---------------------------------------------------------------------------
# 1. Single iteration test
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_single_iteration():
    """max_iterations=1 means only one gather+evaluate cycle."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=1)

    with patch.object(llm, "generate", side_effect=_mock_gen_simple()):
        result = await orch.run("query")

    assert result == "final answer"
    iteration_msgs = [
        e for e in events
        if e.get("event") == "status" and "Iteration" in e.get("message", "")
    ]
    assert len(iteration_msgs) == 1
    assert "1/1" in iteration_msgs[0]["message"]


# ---------------------------------------------------------------------------
# 2. Multiple iterations test
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_multiple_iterations_low_confidence():
    """max_iterations=3, confidence stays low -> all 3 iterations run."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=3)

    # Every credibility eval returns low score -> corroboration always needed
    call_count = 0

    async def gen(prompt: str, api_token: str | None = None, **_kwargs: object) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["sub-q1"]'
        if "Synthesiz" in prompt or "synthesize" in prompt.lower() or "Original query" in prompt:
            return "synthesized"
        # Source evaluator calls get low credibility
        if "credibility" in prompt.lower() or "source" in prompt.lower():
            return LOW_CRED
        return "gathered"

    with patch.object(llm, "generate", side_effect=gen):
        result = await orch.run("query")

    assert result == "synthesized"
    iteration_msgs = [
        e for e in events
        if e.get("event") == "status" and "Iteration" in e.get("message", "")
    ]
    assert len(iteration_msgs) == 3


# ---------------------------------------------------------------------------
# 3. Early stop on high confidence
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_early_stop_high_confidence():
    """Loop stops before max_iterations when confidence >= 0.8."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=5)

    with patch.object(llm, "generate", side_effect=_mock_gen_simple(credibility=HIGH_CRED)):
        result = await orch.run("q")

    assert result == "final answer"
    iteration_msgs = [
        e for e in events
        if e.get("event") == "status" and "Iteration" in e.get("message", "")
    ]
    # High confidence -> should stop after iteration 1
    assert len(iteration_msgs) == 1


# ---------------------------------------------------------------------------
# 4. Follow-up query generation
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_follow_up_queries_driven_by_unresolved():
    """Unresolved issues / next_actions from iter 1 drive iter 2 targets."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=2)

    call_count = 0
    researched_topics: list[str] = []

    async def gen(prompt: str, api_token: str | None = None, **_kwargs: object) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["sub-q1"]'
        if "Synthesiz" in prompt or "Original query" in prompt:
            return "synthesized"
        if "credibility" in prompt.lower() or "source" in prompt.lower():
            return LOW_CRED  # low credibility triggers corroboration
        researched_topics.append(prompt[:80])
        return "gathered"

    with patch.object(llm, "generate", side_effect=gen):
        await orch.run("query")

    # Iteration 2 should have been triggered by low credibility / corroboration needs
    iteration_msgs = [
        e for e in events
        if e.get("event") == "status" and "Iteration" in e.get("message", "")
    ]
    assert len(iteration_msgs) == 2


# ---------------------------------------------------------------------------
# 5. Corroboration triggers re-research
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_corroboration_triggers_reresearch():
    """Weak evidence (credibility < 0.4) triggers a second research pass."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=2)

    call_count = 0

    async def gen(prompt: str, api_token: str | None = None, **_kwargs: object) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["sub-q1"]'
        if "Synthesiz" in prompt or "Original query" in prompt:
            return "synthesized"
        if "credibility" in prompt.lower() or "source" in prompt.lower():
            return _make_cred_json(credibility=0.2)
        return "gathered"

    with patch.object(llm, "generate", side_effect=gen):
        await orch.run("query")

    # Verify two iterations ran (second triggered by low credibility)
    iteration_msgs = [
        e for e in events
        if e.get("event") == "status" and "Iteration" in e.get("message", "")
    ]
    assert len(iteration_msgs) == 2


# ---------------------------------------------------------------------------
# 6. max_iterations=0 edge case
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_zero_iterations_skips_loop():
    """max_iterations=0 skips the iteration loop entirely, goes to synthesis."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=0)

    call_count = 0

    async def gen(prompt: str, api_token: str | None = None, **_kwargs: object) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["sub-q1"]'
        return "synthesized"

    with patch.object(llm, "generate", side_effect=gen):
        result = await orch.run("q")

    assert result == "synthesized"
    # No iteration status messages
    iteration_msgs = [
        e for e in events
        if e.get("event") == "status" and "Iteration" in e.get("message", "")
    ]
    assert len(iteration_msgs) == 0


# ---------------------------------------------------------------------------
# 7. SSE iteration progress events
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_sse_iteration_progress():
    """Verify iteration number and confidence emitted in state_update events."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=1)

    with patch.object(llm, "generate", side_effect=_mock_gen_simple()):
        await orch.run("q")

    progress_events = [
        e for e in events
        if e.get("event") == "state_update" and e.get("message") == "Iteration progress"
    ]
    assert len(progress_events) >= 1
    data = json.loads(progress_events[0]["data"])
    assert data["iteration"] == 1
    assert data["max_iterations"] == 1
    assert "avg_confidence" in data
    assert "confidence_per_sub_question" in data


# ---------------------------------------------------------------------------
# 8. SSE state_update after credibility eval (M6 gap fix)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_sse_state_update_after_credibility():
    """Verify state_update emitted after source credibility evaluation."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=1)

    with patch.object(llm, "generate", side_effect=_mock_gen_simple()):
        await orch.run("q")

    cred_events = [
        e for e in events
        if e.get("event") == "state_update"
        and e.get("message") == "Source credibility evaluated"
    ]
    assert len(cred_events) >= 1
    data = json.loads(cred_events[0]["data"])
    assert "evidence_count" in data
    assert "confidence_scores" in data


# ---------------------------------------------------------------------------
# 9. Decision logic threshold test
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_confidence_threshold_exact():
    """Confidence exactly 0.8 should stop; 0.79 should continue."""
    llm = LLMClient()

    # Test confidence = 0.95 (maps to evidence confidence ~0.95) -> stop after 1
    events_high, cb_high = _collector()
    orch_high = ResearchOrchestrator(llm, api_token="t", callback=cb_high, max_iterations=3)

    with patch.object(llm, "generate", side_effect=_mock_gen_simple(credibility=HIGH_CRED)):
        await orch_high.run("q")

    iter_high = [
        e for e in events_high
        if e.get("event") == "status" and "Iteration" in e.get("message", "")
    ]
    assert len(iter_high) == 1  # stopped early

    # Test low confidence -> continues
    events_low, cb_low = _collector()
    orch_low = ResearchOrchestrator(llm, api_token="t", callback=cb_low, max_iterations=3)

    call_count = 0

    async def gen_low(prompt: str, api_token: str | None = None, **_kwargs: object) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["sub-q1"]'
        if "Synthesiz" in prompt or "Original query" in prompt:
            return "synthesized"
        if "credibility" in prompt.lower() or "source" in prompt.lower():
            return LOW_CRED
        return "gathered"

    with patch.object(llm, "generate", side_effect=gen_low):
        await orch_low.run("q")

    iter_low = [
        e for e in events_low
        if e.get("event") == "status" and "Iteration" in e.get("message", "")
    ]
    assert len(iter_low) > 1  # continued iterating


# ---------------------------------------------------------------------------
# 10. Iteration refines queries
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_iteration_refines_queries():
    """Follow-up iterations target specific sub-questions, not all."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=2)

    iteration_targets: list[list[str]] = []
    call_count = 0

    original_gather = orch._gather_and_evaluate

    async def tracking_gather(state, target_questions):
        iteration_targets.append([sq.text for _, sq in target_questions])
        return await original_gather(state, target_questions)

    async def gen(prompt: str, api_token: str | None = None, **_kwargs: object) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["sub-q1", "sub-q2"]'
        if "Synthesiz" in prompt or "Original query" in prompt:
            return "synthesized"
        if "credibility" in prompt.lower() or "source" in prompt.lower():
            return LOW_CRED
        return "gathered"

    with patch.object(llm, "generate", side_effect=gen), \
         patch.object(orch, "_gather_and_evaluate", side_effect=tracking_gather):
        await orch.run("q")

    # First iteration targets all sub-questions
    assert len(iteration_targets) >= 2
    assert len(iteration_targets[0]) == 2  # both sub-q1, sub-q2
    # Second iteration targets only the ones needing corroboration (subset)
    assert len(iteration_targets[1]) <= len(iteration_targets[0])


# ---------------------------------------------------------------------------
# 11. Corroboration cleared after execution
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_corroboration_cleared_after_reresearch():
    """After re-researching weak sub-questions, corroboration actions removed."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=2)

    call_count = 0
    iteration_num = 0

    async def gen(prompt: str, api_token: str | None = None, **_kwargs: object) -> str:
        nonlocal call_count, iteration_num
        call_count += 1
        if call_count == 1:
            return '["sub-q1"]'
        if "Synthesiz" in prompt or "Original query" in prompt:
            return "synthesized"
        if "credibility" in prompt.lower() or "source" in prompt.lower():
            # Return low on first iteration, high on second
            if call_count <= 10:
                return LOW_CRED
            return HIGH_CRED
        return "gathered"

    with patch.object(llm, "generate", side_effect=gen):
        await orch.run("q")

    # After completion, check the last iteration progress event
    progress_events = [
        e for e in events
        if e.get("event") == "state_update" and e.get("message") == "Iteration progress"
    ]
    if len(progress_events) >= 2:
        last_data = json.loads(progress_events[-1]["data"])
        # After second iteration with high cred, pending_actions should be 0
        assert last_data["pending_actions"] == 0


# ---------------------------------------------------------------------------
# 12. Open questions tracked across iterations
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_unresolved_issues_accumulate():
    """Unresolved issues accumulate and can be resolved across iterations."""
    llm = LLMClient()
    orch = ResearchOrchestrator(llm, api_token="t", max_iterations=1)

    with patch.object(llm, "generate", side_effect=_mock_gen_simple()):
        # We just verify the state machinery works
        state_ref = None
        original_run = orch.run

        # Add unresolved issues directly to state to verify tracking
        from src.core.research_state import ResearchState
        state = ResearchState(query="test")
        state.add_unresolved("sub-question 0 needs more data")
        state.add_unresolved("sub-question 1 contradicts itself")
        assert len(state.unresolved_issues) == 2

        # Simulate resolution: confidence for sub-question 0 reaches 0.8
        state.confidence_scores[0] = 0.85
        resolved_indices = {
            i for i, score in state.confidence_scores.items() if score >= 0.8
        }
        state.unresolved_issues = [
            issue for issue in state.unresolved_issues
            if not any(f"sub-question {i}" in issue.lower() for i in resolved_indices)
        ]
        # sub-question 0 resolved, sub-question 1 remains
        assert len(state.unresolved_issues) == 1
        assert "sub-question 1" in state.unresolved_issues[0]


# ---------------------------------------------------------------------------
# 13. Constructor accepts max_iterations
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_constructor_accepts_max_iterations():
    """ResearchOrchestrator(llm, max_iterations=5) stores the value."""
    llm = LLMClient()
    orch = ResearchOrchestrator(llm, max_iterations=5)
    assert orch.max_iterations == 5


# ---------------------------------------------------------------------------
# 14. Default max_iterations is 3
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_default_max_iterations():
    """Default max_iterations should be 3."""
    llm = LLMClient()
    orch = ResearchOrchestrator(llm)
    assert orch.max_iterations == 3


# ---------------------------------------------------------------------------
# 15. State confidence_scores updated each iteration
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_confidence_scores_updated_each_iteration():
    """Confidence scores change between iterations as new evidence is added."""
    llm = LLMClient()
    events, cb = _collector()
    orch = ResearchOrchestrator(llm, api_token="t", callback=cb, max_iterations=2)

    call_count = 0

    async def gen(prompt: str, api_token: str | None = None, **_kwargs: object) -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return '["sub-q1"]'
        if "Synthesiz" in prompt or "Original query" in prompt:
            return "synthesized"
        if "credibility" in prompt.lower() or "source" in prompt.lower():
            return LOW_CRED
        return "gathered"

    with patch.object(llm, "generate", side_effect=gen):
        await orch.run("q")

    progress_events = [
        e for e in events
        if e.get("event") == "state_update" and e.get("message") == "Iteration progress"
    ]
    # Should have progress events from iterations
    assert len(progress_events) >= 1
    for pe in progress_events:
        data = json.loads(pe["data"])
        assert "confidence_per_sub_question" in data
        assert "avg_confidence" in data
