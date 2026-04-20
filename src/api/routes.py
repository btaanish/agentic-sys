import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agents.orchestrator import ResearchOrchestrator
from src.core.llm_client import LLMClient

router = APIRouter()


class ResearchRequest(BaseModel):
    query: str
    api_token: str | None = None


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/research")
async def research(request: ResearchRequest) -> StreamingResponse:
    event_queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    async def callback(event: dict[str, Any]) -> None:
        await event_queue.put(event)

    async def run_pipeline() -> None:
        orchestrator = ResearchOrchestrator(
            llm_client=LLMClient(),
            api_token=request.api_token,
            callback=callback,
        )
        await orchestrator.run(request.query)
        await event_queue.put(None)  # Signal end of stream

    async def event_generator() -> AsyncGenerator[str, None]:
        task = asyncio.create_task(run_pipeline())
        try:
            while True:
                event = await event_queue.get()
                if event is None:
                    break
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
