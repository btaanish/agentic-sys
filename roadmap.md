# Roadmap

## Project Goal
Build a multi-agent deep research system that performs iterative information discovery and analysis. Given a user query, it decomposes into parallel investigative threads, assigns specialized agents, maintains shared research state, iterates based on findings, and synthesizes a structured answer with evidence and confidence levels. Must have interactive UI with API key input, SSE streaming, and summary.md tracking.

## Phase 1 Milestones (Scaffolding — COMPLETE)

### M1: Project Scaffolding & Core Backend (Budget: 4 cycles)
- FastAPI project structure, basic agent framework, LLM integration, endpoints, pytest setup
- **Status: COMPLETE** (1 cycle used, 10 tests)

### M2: Multi-Agent Research Pipeline (Budget: 6 cycles)
- Research orchestrator, gather/synthesizer agents, SSE streaming
- **Status: COMPLETE** (PR #2 merged, 26 tests passing)

### M3: Frontend UI, End-to-End Testing & README (Budget: 5 cycles)
- Web UI, API token input, SSE progress display, README
- **Status: COMPLETE** (PRs #3, #4, #5 merged; 33 tests passing)

### M4: Polish, Add-ons & Final Validation (Budget: 4 cycles)
- Query history, export/copy, loading spinner, API token validation
- **Status: COMPLETE** (PRs #5, #6, #7 merged; 45 tests passing)

## Phase 2 Milestones (Core Agentic Intelligence — IN PROGRESS)

Phase 1 built a working prototype with UI, API, and a basic 3-stage pipeline. However, independent evaluation reveals the core "agentic" capabilities from the spec are missing. The current system runs a fixed linear pipeline (decompose → gather → synthesize) with no iteration, no parallel execution, no shared state, and no evidence reasoning.

### M5: Shared Research State & Parallel Agent Execution (Budget: 6 cycles)
- Implement a `ResearchState` data structure: subquestions, evidence collected, confidence scores, unresolved issues, dead ends, next actions
- Refactor orchestrator to use shared state instead of simple string aggregation
- Add parallel agent execution (asyncio.gather for concurrent sub-question investigation)
- Add specialized agent types: context agent, evidence agent, counterexample agent, gap-detection agent
- Agents read from and write to shared state
- Tests for state management and parallel execution
- **Status: PENDING**

### M6: Iterative Research Loop & Dynamic Decision-Making (Budget: 6 cycles)
- Replace single-pass pipeline with iterative loop (configurable max iterations)
- After each gather round, evaluate shared state to decide next steps: clarify terms, validate claims, expand partial answers, resolve conflicts, explore alternatives
- Open-question tracking: maintain explicit list of unresolved questions with confidence levels
- Follow-up query generation based on gaps found
- Tests for iteration logic and decision-making
- **Status: PENDING**

### M7: Source Evaluation, Cross-Angle Exploration & Contradiction Handling (Budget: 6 cycles)
- Source evaluation: assess credibility, recency, consistency, directness of evidence
- Cross-angle exploration: technical, historical, empirical, comparative, skeptical, practical investigation frames
- Contradiction detection: identify conflicting sources, analyze reasons, trigger targeted resolution
- Uncertainty tracking with confidence levels in final output
- Tests for evaluation, contradiction detection, and multi-angle coverage
- **Status: PENDING**

### M8: Synthesis Enhancement, summary.md & Final Polish (Budget: 4 cycles)
- Enhanced synthesis: coherent answer + supporting evidence + remaining uncertainty + confidence assessment
- Create summary.md tracking each commit and new file (per spec requirement)
- UI updates to display research state, confidence levels, and evidence quality
- End-to-end integration testing
- **Status: PENDING**

## Lessons Learned
- Phase 1 (M1-M4) built solid scaffolding efficiently. Code is modular and well-tested.
- M3 had an SSE field mismatch bug caught by verification. Lesson: always regression-test frontend-backend contracts.
- Independent evaluation revealed the previous roadmap prematurely declared completion. The prototype works but lacks the core iterative, multi-agent intelligence described in the spec. Phase 2 addresses this gap.
- Budget estimates increased for Phase 2 milestones — these involve more complex logic than scaffolding.
