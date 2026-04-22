import json
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.planner import PlannerAgent
from src.core.llm_client import LLMClient
from src.core.research_state import ResearchState, SubQuestion


@pytest.mark.anyio
async def test_planner_attributes():
    llm = LLMClient()
    agent = PlannerAgent(llm)
    assert agent.name == "planner"
    assert agent.description != ""


@pytest.mark.anyio
async def test_planner_parses_structured_output():
    llm = LLMClient()
    agent = PlannerAgent(llm, api_token="t")
    state = ResearchState(query="Does X improve Y?")
    state.sub_questions.append(SubQuestion(text="Does X improve Y in general?"))
    state.confidence_scores[0] = 0.3

    response = json.dumps({
        "refinements": [
            {"index": 0, "new_text": "Does X improve Y in controlled trials?", "reason": "low confidence"}
        ],
        "additions": [
            {"text": "What are the side effects of X?", "reason": "missing angle"}
        ],
        "retire": [],
    })

    with patch.object(llm, "generate", AsyncMock(return_value=response)):
        plan = await agent.plan(state)

    assert len(plan["refinements"]) == 1
    assert plan["refinements"][0]["index"] == 0
    assert "controlled trials" in plan["refinements"][0]["new_text"]
    assert len(plan["additions"]) == 1
    assert "side effects" in plan["additions"][0]["text"]


@pytest.mark.anyio
async def test_planner_returns_empty_on_parse_failure():
    llm = LLMClient()
    agent = PlannerAgent(llm)
    state = ResearchState(query="q")
    state.sub_questions.append(SubQuestion(text="sq"))

    with patch.object(llm, "generate", AsyncMock(return_value="no json here")):
        plan = await agent.plan(state)

    assert plan == {"refinements": [], "additions": [], "retire": []}


@pytest.mark.anyio
async def test_planner_prompt_includes_state_summary():
    llm = LLMClient()
    agent = PlannerAgent(llm, api_token="t")
    state = ResearchState(query="Is coffee healthy?")
    state.sub_questions.append(SubQuestion(text="Does coffee affect heart rate?"))
    state.confidence_scores[0] = 0.45
    state.add_unresolved("dosage not specified")

    mock_gen = AsyncMock(return_value='{"refinements": [], "additions": [], "retire": []}')

    with patch.object(llm, "generate", mock_gen):
        await agent.plan(state)

    prompt = mock_gen.call_args[0][0]
    assert "Is coffee healthy?" in prompt
    assert "Does coffee affect heart rate?" in prompt
    assert "0.45" in prompt
    assert "dosage not specified" in prompt
