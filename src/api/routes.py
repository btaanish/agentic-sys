from fastapi import APIRouter
from pydantic import BaseModel

from src.core.llm_client import LLMClient

router = APIRouter()


class ResearchRequest(BaseModel):
    query: str
    api_token: str | None = None


class ResearchResponse(BaseModel):
    result: str


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest) -> ResearchResponse:
    client = LLMClient()
    result = await client.generate(request.query, api_token=request.api_token)
    return ResearchResponse(result=result)
