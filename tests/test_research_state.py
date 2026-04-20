import pytest

from src.core.research_state import (
    Evidence,
    ResearchState,
    SubQuestion,
    SubQuestionStatus,
)


def test_research_state_init():
    state = ResearchState(query="test query")
    assert state.query == "test query"
    assert state.sub_questions == []
    assert state.evidence == []
    assert state.confidence_scores == {}
    assert state.unresolved_issues == []
    assert state.dead_ends == []
    assert state.next_actions == []


def test_add_evidence():
    state = ResearchState(query="q")
    state.add_evidence("some content", source="context", confidence=0.8, sub_question_index=0)
    assert len(state.evidence) == 1
    assert state.evidence[0].content == "some content"
    assert state.evidence[0].source == "context"
    assert state.evidence[0].confidence == 0.8
    assert state.evidence[0].sub_question_index == 0
    assert state.confidence_scores[0] == 0.8


def test_add_multiple_evidence_averages_confidence():
    state = ResearchState(query="q")
    state.add_evidence("e1", source="a", confidence=0.6, sub_question_index=0)
    state.add_evidence("e2", source="b", confidence=0.8, sub_question_index=0)
    assert len(state.evidence) == 2
    assert state.confidence_scores[0] == pytest.approx(0.7)


def test_add_evidence_different_sub_questions():
    state = ResearchState(query="q")
    state.add_evidence("e1", source="a", confidence=0.6, sub_question_index=0)
    state.add_evidence("e2", source="b", confidence=0.9, sub_question_index=1)
    assert state.confidence_scores[0] == 0.6
    assert state.confidence_scores[1] == 0.9


def test_mark_dead_end():
    state = ResearchState(query="q")
    state.mark_dead_end("tried approach X")
    assert state.dead_ends == ["tried approach X"]
    state.mark_dead_end("also tried Y")
    assert len(state.dead_ends) == 2


def test_add_unresolved():
    state = ResearchState(query="q")
    state.add_unresolved("missing data")
    assert state.unresolved_issues == ["missing data"]
    state.add_unresolved("unclear methodology")
    assert len(state.unresolved_issues) == 2


def test_sub_question_status_transitions():
    sq = SubQuestion(text="What is X?")
    assert sq.status == SubQuestionStatus.PENDING
    sq.status = SubQuestionStatus.IN_PROGRESS
    assert sq.status == SubQuestionStatus.IN_PROGRESS
    sq.status = SubQuestionStatus.COMPLETED
    assert sq.status == SubQuestionStatus.COMPLETED
    assert sq.status.value == "completed"


def test_to_dict_serialization():
    state = ResearchState(query="test query")
    state.sub_questions = [
        SubQuestion(text="sq1", status=SubQuestionStatus.COMPLETED, assigned_agents=["context"]),
    ]
    state.add_evidence("ev", source="context", confidence=0.7, sub_question_index=0)
    state.mark_dead_end("dead end 1")
    state.add_unresolved("unresolved 1")
    state.next_actions = ["investigate more"]

    d = state.to_dict()
    assert d["query"] == "test query"
    assert len(d["sub_questions"]) == 1
    assert d["sub_questions"][0]["text"] == "sq1"
    assert d["sub_questions"][0]["status"] == "completed"
    assert d["sub_questions"][0]["assigned_agents"] == ["context"]
    assert d["evidence_count"] == 1
    assert d["confidence_scores"] == {0: 0.7}
    assert d["dead_ends"] == ["dead end 1"]
    assert d["unresolved_issues"] == ["unresolved 1"]
    assert d["next_actions"] == ["investigate more"]


def test_evidence_dataclass():
    e = Evidence(content="data", source="evidence", confidence=0.85, sub_question_index=2)
    assert e.content == "data"
    assert e.source == "evidence"
    assert e.confidence == 0.85
    assert e.sub_question_index == 2


def test_sub_question_defaults():
    sq = SubQuestion(text="question")
    assert sq.text == "question"
    assert sq.status == SubQuestionStatus.PENDING
    assert sq.assigned_agents == []
