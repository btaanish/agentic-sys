# Deep Research Agent System

A multi-agent research pipeline built with FastAPI and the Anthropic SDK. Submit a research question and the system decomposes it into sub-questions, gathers findings in parallel via LLM-powered agents, and synthesizes a coherent answer — all streamed back to the browser in real time.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the Server

```bash
uvicorn src.main:app --reload
```

The app serves the frontend at [http://localhost:8000](http://localhost:8000).

## Usage

1. Open your browser to `http://localhost:8000`
2. Enter a research query in the text field
3. Paste your Anthropic API token (or set the `ANTHROPIC_API_KEY` environment variable)
4. Click **Research** — progress updates stream in real time, followed by the synthesized result

## Running Tests

```bash
python3 -m pytest tests/
```

## Architecture

```
Browser (vanilla JS)
  │
  ├─ POST /research  (SSE stream)
  │
FastAPI backend
  │
  ├─ ResearchOrchestrator
  │     1. Decompose query → 2-4 sub-questions (LLM)
  │     2. GatherAgent × N  → research each sub-question (LLM)
  │     3. SynthesizerAgent  → merge findings into final answer (LLM)
  │
  └─ LLMClient (Anthropic SDK wrapper)
```

**Key components:**

| Path | Description |
|------|-------------|
| `src/main.py` | FastAPI app entry point, CORS middleware, static file serving |
| `src/api/routes.py` | `GET /health`, `POST /research` (SSE streaming) |
| `src/agents/base.py` | Abstract `BaseAgent` class |
| `src/agents/gather.py` | `GatherAgent` — researches a sub-question via LLM |
| `src/agents/synthesizer.py` | `SynthesizerAgent` — synthesizes findings into a coherent answer |
| `src/agents/orchestrator.py` | `ResearchOrchestrator` — decomposes, gathers, synthesizes |
| `src/agents/registry.py` | `AgentRegistry` — stores agents by name |
| `src/core/llm_client.py` | `LLMClient` — async Anthropic SDK wrapper |
| `static/` | Frontend UI (HTML, CSS, JS) |
| `tests/` | pytest test suite |
