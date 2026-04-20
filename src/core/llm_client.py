import os

import anthropic


class LLMClient:
    """Wrapper around the Anthropic SDK for LLM calls."""

    DEFAULT_MODEL = "claude-sonnet-4-6"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or self.DEFAULT_MODEL

    async def generate(self, prompt: str, api_token: str | None = None) -> str:
        """Generate a response from the LLM.

        Args:
            prompt: The user prompt to send.
            api_token: Optional API token. Falls back to ANTHROPIC_API_KEY env var.

        Returns:
            The text content of the LLM response.
        """
        token = api_token or os.environ.get("ANTHROPIC_API_KEY", "")
        client = anthropic.AsyncAnthropic(api_key=token)
        message = await client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
