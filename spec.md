# Project Specification

## What do you want to build?

You need to create a multi-agentic deep research system for iterative information discovery and analysis.
Given a user query, it formulates an initial research plan, breaks the problem into parallel investigative threads, and assigns specialized agents to tasks such as query generation, evidence retrieval, source evaluation, contradiction detection, and synthesis. Each agent updates the global research state with findings, uncertainties, and follow-up hypotheses. Based on this intermediate state, the system decides what to investigate next, which branches to deepen, which weak leads to abandon, and what evidence is still missing. The result is a structured, adaptive research process that moves from broad exploration to focused resolution of open questions.

What it must actually be doing under the hood:

Question decomposition
It must turn a broad user request into smaller researchable subquestions.
Example: not just “answer the question,” but identify definitions, assumptions, time scope, entities involved, competing interpretations, and evidence needed.
Parallel investigation
Multiple agents should pursue different threads at once.
For instance:
one agent explores background/context
one agent searches for direct evidence
one agent looks for counterexamples or contradictory sources
one agent identifies missing pieces or ambiguity
Iterative search chaining
Searches must build on previous findings.
This is the core of “agentic.” The system should not just issue many independent searches. It should:
read what was found
notice gaps/conflicts
generate better follow-up queries
decide which thread deserves deeper investigation
Dynamic next-step selection
It must determine exactly what to investigate next based on current evidence.
That means choosing between:
clarifying a term
validating a claim
expanding a partial answer
resolving conflicting evidence
exploring an alternative hypothesis
Open-question tracking
The system should maintain an explicit list of unresolved questions.
For example:
What is still unknown?
Which claim lacks strong evidence?
Which subproblem is blocking final synthesis?
Which branches are speculative vs verified?
Source evaluation
It must assess the quality and relevance of evidence, not just collect links.
This includes:
source credibility
recency
consistency across sources
whether evidence is direct or indirect
whether the source actually answers the subquestion
Cross-angle exploration
“Different angles” should mean genuinely different investigative frames, such as:
technical angle
historical angle
empirical/data angle
comparative angle
opposing or skeptical angle
implementation/practical angle
Contradiction and uncertainty handling
A strong system must notice when sources disagree and trigger targeted resolution.
It should be able to say:
these sources conflict
here is why they may differ
here is what further evidence is needed
here is the current confidence level
Research state / shared memory
Since it is multi-agentic, agents need a shared workspace or state.
This should store:
subquestions
evidence collected
confidence scores
unresolved issues
dead ends
next candidate actions
Synthesis into an answer
The final output should not just be a pile of search results.
It should combine findings into:
a coherent answer
supporting evidence
remaining uncertainty

## How do you consider the project is success?

The system should have an interactive UI where the research question can actually be input folowed by a space where claude API key or Claude OAuth key can be input. 

Also create a summary.md where each commit, new file created in every step is reciorded serial wise
