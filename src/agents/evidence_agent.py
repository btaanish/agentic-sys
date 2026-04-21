from __future__ import annotations

from typing import TYPE_CHECKING

from src.agents.base import BaseAgent
from src.core.llm_client import LLMClient

if TYPE_CHECKING:
    from src.core.research_state import ResearchState


class EvidenceAgent(BaseAgent):
    """Agent that searches for direct evidence related to a query."""

    def __init__(self, llm_client: LLMClient, api_token: str | None = None) -> None:
        super().__init__(
            name="evidence",
            description="Searches for specific evidence, facts, and data",
        )
        self.llm_client = llm_client
        self.api_token = api_token

    async def execute(self, query: str, state: ResearchState | None = None, sub_question_index: int = 0) -> str:
        """Find specific evidence related to the query."""
        existing_context = ""
        if state is not None and state.evidence:
            existing_context = "\n\nExisting findings to build upon:\n"
            for e in state.evidence:
                existing_context += f"- [{e.source}] {e.content}\n"

        prompt = f"""You are an evidence-gathering research specialist. Your job is to find what is actually true about the claim below — not to argue for it, not against it.

                    ## Claim Under Investigation
                    {query}{existing_context}

                    ## Method

                    **Decompose first.** Break the claim into its factual components. A claim like "X caused Y in 2023" has three parts: X existed, Y happened, causation links them. Investigate each separately.

                    **Seek disconfirming evidence with equal effort.** For every piece of supporting evidence, actively search for counter-evidence. A one-sided dossier is a failed investigation, even when the claim turns out to be true.

                    **Weigh sources by tier, not by convenience:**
                    - Tier 1: Primary sources (original data, official records, direct documents, peer-reviewed studies with replicated results)
                    - Tier 2: Reputable secondary sources (established journalism, domain experts writing in their field, meta-analyses)
                    - Tier 3: General reference, industry reports, single-study findings
                    - Tier 4: Opinion, commentary, anonymous claims — use only to note a position exists, never as evidence for truth

                    ## Output Format

                    ### Verdict
                    One of: Supported / Partially supported / Unsupported / Refuted / Insufficient evidence.

                    ### Key Findings
                    For each component of the claim, provide:
                    - **Finding:** what the evidence shows
                    - **Evidence:** specific facts, numbers, quotes, dates — not summaries
                    - **Source:** citation with enough detail to locate (author, publication, date, URL if available)
                    - **Strength:** Strong / Moderate / Weak, with one sentence explaining why

                    ### Counter-Evidence
                    Evidence that contradicts or complicates the claim. If you found none after genuine search, say so explicitly — don't leave the section empty.

                    ### Gaps and Caveats
                    - What you could not verify and why
                    - Where sources conflict
                    - Known limitations (sample sizes, dated information, jurisdictional scope, etc.)

                    ## Rules

                    - **Never fabricate citations.** If you cannot name a real source, say "no source located" rather than inventing one.
                    - **Quote exactly or paraphrase cleanly.** Do not blend the two. If quoting, mark it as a quote.
                    - **Distinguish the claim's components.** "Mostly true but" is not an answer — specify which parts hold and which don't.
                    - **Numbers need provenance.** Every statistic gets a source. Round numbers are suspect; prefer the original figure.
                    - **Correlation is not causation.** Flag causal claims that rest only on correlational evidence.
                    - **Date everything.** Evidence from 2015 about a 2024 claim is weaker than the same evidence from 2024.
                    - **Absence of evidence ≠ evidence of absence.** If something is unverifiable, say "insufficient evidence" — do not default to "false."
                    """
        result = await self.llm_client.generate(prompt, api_token=self.api_token)
        if state is not None:
            state.add_evidence(result, source=self.name, confidence=0.8, sub_question_index=sub_question_index)
        return result
