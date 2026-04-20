from src.agents.base import BaseAgent


class AgentRegistry:
    """Registry that stores available agents by name."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register an agent by its name."""
        self._agents[agent.name] = agent

    def get(self, name: str) -> BaseAgent:
        """Get an agent by name. Raises KeyError if not found."""
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' not found in registry")
        return self._agents[name]

    def list_agents(self) -> list[str]:
        """Return a list of all registered agent names."""
        return list(self._agents.keys())
