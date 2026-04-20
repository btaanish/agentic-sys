from dataclasses import dataclass, field
from enum import Enum


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

    def add_evidence(
        self,
        content: str,
        source: str,
        confidence: float,
        sub_question_index: int,
    ) -> None:
        self.evidence.append(
            Evidence(
                content=content,
                source=source,
                confidence=confidence,
                sub_question_index=sub_question_index,
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
            "confidence_scores": self.confidence_scores,
            "unresolved_issues": self.unresolved_issues,
            "dead_ends": self.dead_ends,
            "next_actions": self.next_actions,
        }
