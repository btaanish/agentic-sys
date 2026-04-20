from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.research_state import ResearchState


class BaseAgent(ABC):
    """Abstract base class for all research agents."""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, query: str, state: ResearchState | None = None, sub_question_index: int = 0) -> str:
        """Execute the agent's task given a query."""
        ...
