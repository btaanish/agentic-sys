# src/core/llm_client.py
import asyncio
import os
import anthropic


class LLMClient:
    DEFAULT_MODEL = "claude-sonnet-4-6"
    DEFAULT_CONCURRENCY = 4
    DEFAULT_MAX_TOKENS = 1024

    def __init__(
        self,
        model: str | None = None,
        api_token: str | None = None,
        max_concurrency: int = DEFAULT_CONCURRENCY,
    ) -> None:
        self.model = model or self.DEFAULT_MODEL
        token = api_token or os.environ.get("ANTHROPIC_API_KEY", "")
        self._client = anthropic.AsyncAnthropic(
            api_key=token,
            max_retries=5,
            timeout=120.0,
        )
        self._sem = asyncio.Semaphore(max_concurrency)

    async def generate(
        self,
        prompt: str,
        api_token: str | None = None,
        system: str | None = None,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
    ) -> str:
        async with self._sem:
            kwargs: dict = {
                "model": self.model,
                "max_tokens": max_tokens or self.DEFAULT_MAX_TOKENS,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                kwargs["system"] = system
            if tools:
                kwargs["tools"] = tools
            message = await self._client.messages.create(**kwargs)
        # The response may contain multiple content blocks (text interleaved
        # with server-side tool_use / tool_result blocks when tools are enabled).
        # Concatenate every text block so callers get the full assistant output.
        parts = [b.text for b in message.content if getattr(b, "type", None) == "text"]
        return "\n".join(p for p in parts if p)

    async def aclose(self) -> None:
        await self._client.close()
