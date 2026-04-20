"""Tests for Evidence enrichment with source_metadata and ResearchState.to_dict weak_sources."""

from src.core.research_state import Evidence, ResearchState, SubQuestion
from src.core.source_metadata import SourceMetadata, SourceType


class TestEvidenceSourceMetadata:
    def test_evidence_default_no_metadata(self):
        ev = Evidence(content="text", source="agent", confidence=0.8, sub_question_index=0)
        assert ev.source_metadata is None

    def test_evidence_with_metadata(self):
        meta = SourceMetadata(source_id="m1", credibility_score=0.9)
        ev = Evidence(
            content="text", source="agent", confidence=0.8,
            sub_question_index=0, source_metadata=meta,
        )
        assert ev.source_metadata is meta
        assert ev.source_metadata.credibility_score == 0.9

    def test_add_evidence_with_metadata(self):
        state = ResearchState(query="test")
        meta = SourceMetadata(source_id="s1", credibility_score=0.7)
        state.add_evidence("content", "agent", 0.8, 0, source_metadata=meta)
        assert state.evidence[0].source_metadata is meta


class TestToDictWeakSources:
    def test_to_dict_no_weak_sources(self):
        state = ResearchState(query="q")
        strong = SourceMetadata(source_id="s1", credibility_score=0.8)
        state.add_evidence("c1", "a1", 0.9, 0, source_metadata=strong)
        d = state.to_dict()
        assert d["weak_sources"] == 0

    def test_to_dict_with_weak_sources(self):
        state = ResearchState(query="q")
        weak = SourceMetadata(source_id="w1", credibility_score=0.2)
        strong = SourceMetadata(source_id="s1", credibility_score=0.8)
        state.add_evidence("c1", "a1", 0.5, 0, source_metadata=weak)
        state.add_evidence("c2", "a2", 0.9, 0, source_metadata=strong)
        d = state.to_dict()
        assert d["weak_sources"] == 1

    def test_to_dict_none_metadata_not_counted_as_weak(self):
        state = ResearchState(query="q")
        state.add_evidence("c1", "a1", 0.5, 0)
        d = state.to_dict()
        assert d["weak_sources"] == 0
