import pytest

from src.agents.base import BaseAgent


def test_base_agent_is_abstract():
    """BaseAgent cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseAgent("test", "test agent")  # type: ignore[abstract]


def test_base_agent_subclass():
    """A concrete subclass with execute() can be instantiated."""

    class ConcreteAgent(BaseAgent):
        async def execute(self, query: str) -> str:
            return f"response to {query}"

    agent = ConcreteAgent(name="test", description="a test agent")
    assert agent.name == "test"
    assert agent.description == "a test agent"


@pytest.mark.anyio
async def test_base_agent_execute():
    """Concrete agent execute() returns expected result."""

    class ConcreteAgent(BaseAgent):
        async def execute(self, query: str) -> str:
            return f"answer: {query}"

    agent = ConcreteAgent(name="qa", description="qa agent")
    result = await agent.execute("hello")
    assert result == "answer: hello"
