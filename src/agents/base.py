from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """Abstract base class for all research agents."""

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, query: str) -> str:
        """Execute the agent's task given a query."""
        ...
