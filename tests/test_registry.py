import pytest

from src.agents.base import BaseAgent
from src.agents.registry import AgentRegistry


class FakeAgent(BaseAgent):
    async def execute(self, query: str) -> str:
        return "fake"


def test_register_and_get():
    registry = AgentRegistry()
    agent = FakeAgent(name="test", description="test agent")
    registry.register(agent)
    assert registry.get("test") is agent


def test_get_missing_raises():
    registry = AgentRegistry()
    with pytest.raises(KeyError, match="not found"):
        registry.get("missing")


def test_list_agents():
    registry = AgentRegistry()
    registry.register(FakeAgent(name="a", description="agent a"))
    registry.register(FakeAgent(name="b", description="agent b"))
    assert sorted(registry.list_agents()) == ["a", "b"]


def test_list_agents_empty():
    registry = AgentRegistry()
    assert registry.list_agents() == []


def test_register_overwrites():
    registry = AgentRegistry()
    agent1 = FakeAgent(name="x", description="first")
    agent2 = FakeAgent(name="x", description="second")
    registry.register(agent1)
    registry.register(agent2)
    assert registry.get("x") is agent2
