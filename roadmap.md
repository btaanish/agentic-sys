# Roadmap

## Project Goal
Build a multi-agent deep research system with FastAPI backend, SSE streaming, and a UI. Must be testable, modular, and clean. Includes API token input and progress tracking.

## Milestones

### M1: Project Scaffolding & Core Backend (Budget: 4 cycles)
- FastAPI project structure with proper packaging
- Basic agent framework (base agent class, agent registry)
- LLM integration layer with configurable API token
- Basic endpoint structure (health check, submit query)
- Unit test setup with pytest
- progress.md initialized
- **Status: COMPLETE** (1 cycle used, 10 tests)

### M2: Multi-Agent Research Pipeline (Budget: 6 cycles)
- Research orchestrator agent that decomposes queries into sub-tasks
- Specialized research agents (gather, synthesizer)
- Agent communication and result aggregation
- SSE streaming for real-time progress updates
- Integration tests
- **Status: COMPLETE** (PR #2 merged, 26 tests passing)

### M3: Frontend UI, End-to-End Testing & README (Budget: 5 cycles)
- Simple web UI (vanilla HTML/CSS/JS, no build step)
- API token input field
- SSE-powered live progress display
- Research results display with formatting
- End-to-end validation with test API token
- README with setup/run instructions
- progress.md updated
- **Status: COMPLETE** (PRs #3, #4 merged; SSE field mismatch found by Vera, fixed by Leo in PR #5 with regression tests; 33 tests passing. PR #5 still open — must be merged.)

### M4: Polish, Add-ons & Final Validation (Budget: 4 cycles)
- Merge PR #5 (SSE fix) to main
- Interesting add-ons per spec: query history, export/copy results, loading animations
- End-to-end validation with provided API token (sk-ant-oat01-...)
- Comprehensive test coverage for add-on features
- progress.md fully updated with M4 components
- Final code cleanup and quality pass
- **Status: NOT STARTED**

## Lessons Learned
- M1 completed efficiently in first cycle. Scaffolding is solid and clean.
- M2 completed in ~2 cycles. Code is modular with good test coverage.
- Combined README into M3 to avoid M4 becoming too thin. M4 now focuses on polish and add-ons per spec requirements.
- M3 had a high-severity SSE field mismatch bug (frontend used `event.type`/`event.content` but backend emits `event.event`/`event.data`). Caught by Vera during verification, fixed by Leo. Lesson: always add regression tests for frontend-backend contract mismatches.
- Quinn's blind audit confirmed all M3 acceptance criteria met. Independent verification is valuable.
