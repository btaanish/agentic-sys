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

## Phase 2 Milestones (Core Agentic Intelligence — NEAR COMPLETE)

### M5: Shared Research State & Parallel Agent Execution (Budget: 6 cycles)
- ResearchState data structure with subquestions, evidence, confidence scores, unresolved issues, dead ends, next actions
- Orchestrator refactored to use shared state, parallel agent execution via asyncio.gather
- 4 specialized agents (Context, Evidence, Counterexample, GapDetection) that read/write state directly
- SSE events enriched with state data
- **Status: COMPLETE** (branch leo/agents-state-aware verified by Apollo, 73 tests passing, 4 cycles used)

### M6: Source Credibility & Trust Scoring Module (Budget: 6 cycles) — URGENT per human
- **Reprioritized from M7 per human request (Issue #5)**
- Source evaluation module: assess credibility, recency, consistency, bias, corroboration
- SourceMetadata model with credibility_score, bias_score, recency_score, source_type, independently_verified
- Integrate with ResearchState: Evidence objects enriched with source metadata
- Orchestrator uses credibility to rank evidence, suppress weak sources, request corroboration
- Synthesis agent weighs evidence by credibility scores
- Tests for source evaluation, scoring, and orchestrator integration
- **Status: COMPLETE** (branch maya/source-credibility, 98 tests passing, 2 cycles used)
- Verified: SourceMetadata model, SourceEvaluator agent, orchestrator integration, synthesis weighting all confirmed working
- Minor gaps: SSE event after credibility eval missing, corroboration detection-only (not executed). Both deferred to M7.

### M7: Iterative Research Loop & Dynamic Decision-Making (Budget: 5 cycles)
- Replace single-pass pipeline with iterative loop (configurable max iterations)
- After each gather round, evaluate shared state to decide next steps
- Open-question tracking with confidence levels
- Follow-up query generation based on gaps found
- Corroboration execution (M6 gap fixed)
- SSE iteration progress events (M6 gap fixed)
- Tests for iteration logic and decision-making
- **Status: COMPLETE** (PR #8 merged, 113 tests passing, 2 cycles used)
- Verified: All 3 Apollo verifiers PASSED (structural, logic, tests)

### M8: Cross-Angle Exploration & Contradiction Handling (Budget: 4 cycles)
- Cross-angle exploration: technical, historical, empirical, comparative, skeptical, practical frames
- Contradiction detection: identify conflicting sources, analyze reasons, trigger resolution
- Uncertainty tracking with confidence levels in final output
- Tests for multi-angle coverage and contradiction detection
- **Status: COMPLETE** (PR #9 merged, 128 tests passing, 2 cycles used)
- Verified: All 3 Apollo verifiers PASSED — data models, orchestrator logic, and tests all confirmed

### M9: Synthesis Enhancement, summary.md & Final Polish (Budget: 4 cycles)
- Enhanced synthesis output: structured JSON with sections (findings, evidence, contradictions, uncertainty, confidence)
- Create summary.md tracking each commit and new file (per spec requirement)
- UI updates: display sub-questions, evidence with credibility scores, contradictions, confidence levels during research
- Parse and render structured result sections in the frontend (not just plain text)
- End-to-end integration testing (10+ new tests)
- **Status: IN PROGRESS**

## Lessons Learned
- Phase 1 (M1-M4) built solid scaffolding efficiently. Code is modular and well-tested.
- M3 had an SSE field mismatch bug caught by verification. Lesson: always regression-test frontend-backend contracts.
- Independent evaluation revealed the previous roadmap prematurely declared completion. The prototype works but lacks the core iterative, multi-agent intelligence described in the spec. Phase 2 addresses this gap.
- M5 verification caught that agents weren't truly state-aware (orchestrator proxied writes). Fix round required. Lesson: verify agent autonomy, not just orchestrator behavior.
- Budget estimates increased for Phase 2 milestones — these involve more complex logic than scaffolding.
- Human urgency on source credibility (Issue #5) — reprioritized M6 to address this before iterative loop.
- M6 completed efficiently in 2 cycles. Verification found SSE gap and corroboration is detection-only — both acceptable scope boundaries, deferred to M7 where iterative loop enables re-research naturally.
- Budget accuracy improving: M6 estimated 6 cycles, used 2. Can tighten Phase 2 estimates.
- M7 also completed in 2 cycles (budgeted 5). Verification clean — all 3 verifiers PASS on first attempt. Team is executing efficiently.
- Reducing M8 budget to 4 cycles (from 6) based on consistent over-budgeting pattern.
- M8 completed in 2 cycles (budgeted 4). Team continues to execute efficiently. M9 is the final milestone — keeping budget at 4 cycles for polish work which tends to be broader in scope.
