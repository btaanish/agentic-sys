"""Tests for SourceEvaluator agent."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.base import BaseAgent
from src.agents.source_evaluator import SourceEvaluator
from src.core.llm_client import LLMClient
from src.core.source_metadata import SourceType


@pytest.fixture
def mock_llm():
    return AsyncMock(spec=LLMClient)


@pytest.mark.anyio
async def test_evaluate_parses_llm_json(mock_llm):
    mock_llm.generate.return_value = json.dumps({
        "source_type": "academic_paper",
        "credibility_score": 0.9,
        "bias_score": 0.1,
        "recency_score": 0.7,
        "domain": "machine learning",
    })
    evaluator = SourceEvaluator(mock_llm, api_token="tok")
    meta = await evaluator.evaluate("Some evidence text", "http://example.com")

    assert meta.source_type == SourceType.ACADEMIC_PAPER
    assert meta.credibility_score == 0.9
    assert meta.bias_score == 0.1
    assert meta.recency_score == 0.7
    assert meta.domain == "machine learning"
    assert meta.url == "http://example.com"
    assert meta.source_id  # non-empty UUID


@pytest.mark.anyio
async def test_evaluate_handles_invalid_json(mock_llm):
    mock_llm.generate.return_value = "not valid json at all"
    evaluator = SourceEvaluator(mock_llm)
    meta = await evaluator.evaluate("evidence", "source")

    assert meta.credibility_score == 0.4
    assert meta.bias_score == 0.5
    assert meta.recency_score == 0.3
    assert meta.source_type == SourceType.UNKNOWN
    assert meta.domain == ""


@pytest.mark.anyio
async def test_evaluate_invalid_source_type(mock_llm):
    mock_llm.generate.return_value = json.dumps({
        "source_type": "not_a_real_type",
        "credibility_score": 0.6,
        "bias_score": 0.3,
        "recency_score": 0.5,
        "domain": "science",
    })
    evaluator = SourceEvaluator(mock_llm)
    meta = await evaluator.evaluate("evidence", "source")

    assert meta.source_type == SourceType.UNKNOWN
    assert meta.credibility_score == 0.6


@pytest.mark.anyio
async def test_evaluate_non_http_source(mock_llm):
    mock_llm.generate.return_value = json.dumps({
        "source_type": "blog",
        "credibility_score": 0.5,
        "bias_score": 0.5,
        "recency_score": 0.5,
        "domain": "tech",
    })
    evaluator = SourceEvaluator(mock_llm)
    meta = await evaluator.evaluate("content", "some_local_source")

    assert meta.url == ""  # non-http sources get empty URL


@pytest.mark.anyio
async def test_execute_returns_json_string(mock_llm):
    mock_llm.generate.return_value = json.dumps({
        "source_type": "news_article",
        "credibility_score": 0.7,
        "bias_score": 0.4,
        "recency_score": 0.8,
        "domain": "politics",
    })
    evaluator = SourceEvaluator(mock_llm, api_token="tok")
    result = await evaluator.execute("query text")
    data = json.loads(result)

    assert "source_id" in data
    assert data["source_type"] == "news_article"
    assert data["credibility_score"] == 0.7
    assert data["bias_score"] == 0.4
    assert data["recency_score"] == 0.8
    assert data["domain"] == "politics"
    assert "overall_quality" in data


def test_inherits_from_base_agent():
    mock_llm = AsyncMock(spec=LLMClient)
    evaluator = SourceEvaluator(mock_llm)
    assert isinstance(evaluator, BaseAgent)
    assert evaluator.name == "source_evaluator"
    assert evaluator.description == "Evaluates source credibility, bias, and recency"
