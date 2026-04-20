from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.source_metadata import SourceMetadata


class SubQuestionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass
class Evidence:
    content: str
    source: str  # which agent produced it
    confidence: float  # 0.0 to 1.0
    sub_question_index: int  # which sub-question this relates to
    source_metadata: SourceMetadata | None = None


@dataclass
class SubQuestion:
    text: str
    status: SubQuestionStatus = SubQuestionStatus.PENDING
    assigned_agents: list[str] = field(default_factory=list)


@dataclass
class ResearchState:
    query: str
    sub_questions: list[SubQuestion] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    confidence_scores: dict[int, float] = field(
        default_factory=dict
    )  # sub_question_index -> confidence
    unresolved_issues: list[str] = field(default_factory=list)
    dead_ends: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    contradictions: list[dict] = field(default_factory=list)
    exploration_angles: list[str] = field(default_factory=list)

    def add_evidence(
        self,
        content: str,
        source: str,
        confidence: float,
        sub_question_index: int,
        source_metadata: SourceMetadata | None = None,
    ) -> None:
        self.evidence.append(
            Evidence(
                content=content,
                source=source,
                confidence=confidence,
                sub_question_index=sub_question_index,
                source_metadata=source_metadata,
            )
        )
        # Update confidence score for this sub-question (average of all evidence)
        relevant = [
            e.confidence
            for e in self.evidence
            if e.sub_question_index == sub_question_index
        ]
        self.confidence_scores[sub_question_index] = sum(relevant) / len(relevant)

    def mark_dead_end(self, description: str) -> None:
        self.dead_ends.append(description)

    def add_unresolved(self, issue: str) -> None:
        self.unresolved_issues.append(issue)

    def add_contradiction(
        self,
        evidence_ids: list[int],
        description: str,
        resolution: str | None = None,
        confidence_impact: float = 0.0,
    ) -> None:
        self.contradictions.append({
            "evidence_ids": evidence_ids,
            "description": description,
            "resolution": resolution,
            "confidence_impact": confidence_impact,
        })

    def avg_confidence(self) -> float:
        """Return average confidence across all sub-questions, or 0.0 if none."""
        if not self.confidence_scores:
            return 0.0
        return sum(self.confidence_scores.values()) / len(self.confidence_scores)

    def to_dict(self) -> dict:
        """Return a serializable dict for SSE events."""
        return {
            "query": self.query,
            "sub_questions": [
                {
                    "text": sq.text,
                    "status": sq.status.value,
                    "assigned_agents": sq.assigned_agents,
                }
                for sq in self.sub_questions
            ],
            "evidence_count": len(self.evidence),
            "weak_sources": sum(
                1
                for e in self.evidence
                if e.source_metadata is not None and e.source_metadata.is_weak()
            ),
            "confidence_scores": self.confidence_scores,
            "unresolved_issues": self.unresolved_issues,
            "dead_ends": self.dead_ends,
            "next_actions": self.next_actions,
            "contradictions": self.contradictions,
            "exploration_angles": self.exploration_angles,
        }
