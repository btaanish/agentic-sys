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
- **Status: IN PROGRESS**

### M4: Polish, Add-ons & Final Validation (Budget: 3 cycles)
- Comprehensive test coverage
- Interesting add-ons (query history, export results, etc.)
- Final validation with provided API token
- progress.md fully updated
- **Status: NOT STARTED**

## Lessons Learned
- M1 completed efficiently in first cycle. Scaffolding is solid and clean.
- M2 completed in ~2 cycles. Code is modular with good test coverage.
- Combined README into M3 to avoid M4 becoming too thin. M4 now focuses on polish and add-ons per spec requirements.
