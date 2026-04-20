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
- **Status: COMPLETE** (branch `leo/project-scaffolding`, 10 tests passing, needs merge to main)

### M2: Multi-Agent Research Pipeline (Budget: 6 cycles)
- Research orchestrator agent that decomposes queries into sub-tasks
- Specialized research agents (web search, summarization, synthesis)
- Agent communication and result aggregation
- SSE streaming for real-time progress updates
- Integration tests
- **Status: IN PROGRESS**

### M3: Frontend UI & End-to-End Integration (Budget: 4 cycles)
- Simple web UI (HTML/JS or lightweight framework)
- API token input field
- SSE-powered live progress display
- Research results display with formatting
- End-to-end testing with sample queries
- **Status: NOT STARTED**

### M4: Polish, Testing & Documentation (Budget: 3 cycles)
- Comprehensive test coverage
- Error handling and edge cases
- README with setup and run instructions
- progress.md fully updated
- Final validation with provided API token
- **Status: NOT STARTED**

## Lessons Learned
- M1 completed efficiently in first cycle. Scaffolding is solid and clean.
