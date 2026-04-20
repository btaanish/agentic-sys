"""Tests for SourceMetadata model and SourceType enum."""

from src.core.source_metadata import SourceMetadata, SourceType


class TestSourceType:
    def test_enum_values(self):
        assert SourceType.ACADEMIC_PAPER.value == "academic_paper"
        assert SourceType.NEWS_ARTICLE.value == "news_article"
        assert SourceType.BLOG.value == "blog"
        assert SourceType.OFFICIAL_DOC.value == "official_doc"
        assert SourceType.FORUM.value == "forum"
        assert SourceType.UNKNOWN.value == "unknown"

    def test_enum_is_str(self):
        assert isinstance(SourceType.BLOG, str)
        assert SourceType.BLOG == "blog"


class TestSourceMetadata:
    def test_defaults(self):
        meta = SourceMetadata(source_id="abc")
        assert meta.source_id == "abc"
        assert meta.url == ""
        assert meta.domain == ""
        assert meta.source_type == SourceType.UNKNOWN
        assert meta.published_at == ""
        assert meta.credibility_score == 0.5
        assert meta.bias_score == 0.5
        assert meta.recency_score == 0.5
        assert meta.independently_verified is False
        assert meta.citation_density is None

    def test_is_weak_true(self):
        meta = SourceMetadata(source_id="w1", credibility_score=0.2)
        assert meta.is_weak() is True

    def test_is_weak_false(self):
        meta = SourceMetadata(source_id="s1", credibility_score=0.3)
        assert meta.is_weak() is False

    def test_is_weak_boundary(self):
        meta = SourceMetadata(source_id="b1", credibility_score=0.29)
        assert meta.is_weak() is True

    def test_overall_quality_score(self):
        meta = SourceMetadata(
            source_id="q1",
            credibility_score=0.8,
            bias_score=0.2,
            recency_score=0.6,
        )
        # 0.8*0.5 + (1-0.2)*0.3 + 0.6*0.2 = 0.4 + 0.24 + 0.12 = 0.76
        assert abs(meta.overall_quality_score() - 0.76) < 1e-9

    def test_overall_quality_score_zeros(self):
        meta = SourceMetadata(
            source_id="z1",
            credibility_score=0.0,
            bias_score=0.0,
            recency_score=0.0,
        )
        # 0*0.5 + 1*0.3 + 0*0.2 = 0.3
        assert abs(meta.overall_quality_score() - 0.3) < 1e-9

    def test_overall_quality_score_ones(self):
        meta = SourceMetadata(
            source_id="o1",
            credibility_score=1.0,
            bias_score=1.0,
            recency_score=1.0,
        )
        # 1*0.5 + 0*0.3 + 1*0.2 = 0.7
        assert abs(meta.overall_quality_score() - 0.7) < 1e-9
