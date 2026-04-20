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

## M2: Research Pipeline — Agents, Orchestrator, SSE

### PR #2 — Research pipeline (leo/research-pipeline)

**Components added:**
- `src/agents/registry.py` — `AgentRegistry` class with register/get/list_agents methods
- `src/agents/gather.py` — `GatherAgent(BaseAgent)` that researches sub-questions via LLM
- `src/agents/synthesizer.py` — `SynthesizerAgent(BaseAgent)` that synthesizes findings into coherent answers
- `src/agents/orchestrator.py` — `ResearchOrchestrator` that decomposes queries, dispatches to gather agents, synthesizes results; supports async event callbacks; handles API/auth/timeout errors
- `src/api/routes.py` — Updated `POST /research` to SSE streaming endpoint with `text/event-stream` content type
- `tests/test_registry.py` — Unit tests for AgentRegistry (5 tests)
- `tests/test_gather_synth.py` — Unit tests for GatherAgent and SynthesizerAgent with mocked LLM (4 tests)
- `tests/test_orchestrator.py` — Unit tests for orchestrator pipeline, fallback, and error handling (5 tests)
- `tests/test_sse.py` — Integration tests for SSE endpoint (2 tests)

## M3: Frontend & Documentation

### PR #3 — Frontend UI (leo/m3-frontend)

**Components added:**
- `src/main.py` — Added CORS middleware, static file serving (`/static`), root route serving `index.html`
- `static/index.html` — Research form with query input, API token field, progress and result sections
- `static/style.css` — Frontend styles
- `static/app.js` — Vanilla JS client: form submission, SSE stream parsing, progress/result/error display

### PR #4 — Documentation (noah/m3-docs)

**Components added:**
- `README.md` — Project overview, setup instructions, usage guide, test instructions, architecture overview
- `progress.md` — Updated with M3 components

## M4: Polish, Add-ons & Final Validation

### PR #5 — SSE event field fix (leo/sse-fix)

**Components fixed:**
- `static/app.js` — Fixed SSE event field mismatch: changed `event.type` to `event.event` and `event.content` to `event.data` to match server-sent event format
- `tests/test_sse_fields.py` — Regression tests for correct SSE field usage (10 tests)

### PR #6 — Add-on features (maya/m4-addons)

**Components added:**
- `static/index.html` — Added query history section, clear history button, loading spinner element, result action buttons (copy/download)
- `static/app.js` — Query history with localStorage (save, load, render, clear, max 10 entries), copy-to-clipboard and download-as-txt for results, loading spinner show/hide during research
- `static/style.css` — Styles for query history items, secondary buttons, result actions, and animated loading spinner
- `tests/test_addons.py` — Tests for add-on features: query history HTML/JS, export/copy buttons, loading spinner, localStorage usage (10 tests)

### Test Summary

45 tests passing across 10 test files covering project structure, health endpoint, agents, registry, gather/synthesize pipeline, orchestrator, SSE streaming, SSE field correctness, frontend structure, and add-on features.
