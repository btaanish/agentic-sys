# Progress

## M1: Project Scaffolding & Core Backend

### PR #1 — Project scaffolding (leo/project-scaffolding)

**Components added:**
- `src/agents/base.py` — Abstract `BaseAgent` class with `execute(query) -> str`
- `src/core/llm_client.py` — `LLMClient` wrapper around Anthropic SDK (async, configurable token)
- `src/api/routes.py` — FastAPI routes: `GET /health`, `POST /research`
- `src/main.py` — FastAPI app entry point
- `tests/test_health.py` — Health endpoint test
- `tests/test_agents.py` — BaseAgent abstraction tests
- `tests/test_structure.py` — Project structure verification tests
- `requirements.txt` — Project dependencies
