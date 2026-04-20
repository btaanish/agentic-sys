from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SourceType(str, Enum):
    ACADEMIC_PAPER = "academic_paper"
    NEWS_ARTICLE = "news_article"
    BLOG = "blog"
    OFFICIAL_DOC = "official_doc"
    FORUM = "forum"
    UNKNOWN = "unknown"


@dataclass
class SourceMetadata:
    source_id: str
    url: str = ""
    domain: str = ""
    source_type: SourceType = SourceType.UNKNOWN
    published_at: str = ""  # ISO format or empty
    credibility_score: float = 0.5  # 0-1
    bias_score: float = 0.5  # 0-1
    recency_score: float = 0.5  # 0-1
    independently_verified: bool = False
    citation_density: Optional[float] = None

    def is_weak(self) -> bool:
        """Return True if credibility < 0.3"""
        return self.credibility_score < 0.3

    def overall_quality_score(self) -> float:
        """Weighted combination of scores."""
        return (
            self.credibility_score * 0.5
            + (1 - self.bias_score) * 0.3
            + self.recency_score * 0.2
        )
