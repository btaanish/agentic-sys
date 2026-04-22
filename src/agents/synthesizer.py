from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from src.agents.base import BaseAgent
from src.core.llm_client import LLMClient

if TYPE_CHECKING:
    from src.core.research_state import ResearchState


_SYSTEM_PROMPT = (Path(__file__).parent / "synthesizer.md").read_text(encoding="utf-8")

# Sections the synthesizer must never emit. Some LLM outputs slip them in
# despite the system prompt, so we strip them post-hoc as a guarantee.
_FORBIDDEN_SECTION_PATTERNS = [
    r"remaining\s+uncertainty",
    r"overall\s+confidence",
]


def _is_heading(line: str) -> tuple[bool, int | None, str]:
    """Return (is_heading, level, text). Level is # count (1-6) for ATX,
    or 0 for bolded standalone lines (treated as top-level-ish). text is
    the heading text stripped of markers and leading numbers/punctuation.
    """
    stripped = line.strip()
    # ATX heading: `#`, `##`, etc.
    m = re.match(r"^(#{1,6})\s+(.+?)\s*$", stripped)
    if m:
        return True, len(m.group(1)), _normalize_heading_text(m.group(2))
    # Bolded standalone line, optionally numbered: **1. Foo** or **Foo**
    m = re.match(r"^\*\*(.+?)\*\*\s*:?\s*$", stripped)
    if m:
        return True, 0, _normalize_heading_text(m.group(1))
    return False, None, ""


def _normalize_heading_text(text: str) -> str:
    # Drop leading numbering like "3." or "3) "
    return re.sub(r"^\s*\d+[.)]\s*", "", text).strip().lower()


def _strip_forbidden_sections(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        is_h, level, heading_text = _is_heading(lines[i])
        if is_h and any(re.fullmatch(p, heading_text) for p in _FORBIDDEN_SECTION_PATTERNS):
            # Skip this heading and every following line until the next heading
            # at the same-or-higher level (lower numeric level = higher rank;
            # bolded pseudo-heading level 0 is treated as top-rank).
            j = i + 1
            while j < len(lines):
                next_is_h, next_level, _ = _is_heading(lines[j])
                if next_is_h:
                    # Treat bolded level (0) as equal-rank to any heading.
                    if level == 0 or next_level == 0 or next_level <= level:
                        break
                j += 1
            i = j
            continue
        out.append(lines[i])
        i += 1
    # Trim trailing blank lines left behind.
    while out and not out[-1].strip():
        out.pop()
    return "\n".join(out)


class SynthesizerAgent(BaseAgent):
    """Agent that synthesizes multiple research findings into a coherent answer."""

    def __init__(self, llm_client: LLMClient, api_token: str | None = None) -> None:
        super().__init__(name="synthesizer", description="Synthesizes multiple findings into a coherent answer")
        self.llm_client = llm_client
        self.api_token = api_token

    async def execute(self, query: str, state: ResearchState | None = None, sub_question_index: int = 0) -> str:
        """Synthesize findings into a coherent answer.

        Args:
            query: A string containing the original query and all gathered findings.
            state: Optional ResearchState (not used by synthesizer but accepted for interface consistency).
            sub_question_index: Optional sub-question index (not used by synthesizer).
        """
        raw = await self.llm_client.generate(
            query,
            api_token=self.api_token,
            system=_SYSTEM_PROMPT,
            max_tokens=4096,
        )
        return _strip_forbidden_sections(raw)
