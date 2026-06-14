"""Web Research Agent (Agent A).

Responsibilities:
  - Search the web sources it has been *explicitly handed* by the coordinator.
  - Extract structured findings (content separated from metadata).
  - Return structured JSON output, or a structured error on failure.

This agent never reads global state. Everything it needs — the research
question and the sources to inspect — arrives in the `context` argument the
coordinator passes to `run()`. This is explicit context passing, not
automatic inheritance.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from error_handler import AgentFailure, FailureInjection

AGENT_NAME = "web_research_agent"


def _make_finding(source: Dict, claim: Dict, index: int) -> Dict:
    """Convert a raw source claim into a structured finding.

    Content (what was claimed + evidence) is kept strictly separate from
    metadata (where it came from + how confident we are).
    """
    return {
        "claim_id": f"{source['source_id']}_claim_{index}",
        "content": {
            "claim": claim["claim"],
            "evidence_excerpt": claim["evidence_excerpt"],
            "topic": claim.get("topic"),
            "value": claim.get("value"),
        },
        "metadata": {
            "agent": AGENT_NAME,
            "source": source.get("title") or source.get("url") or source["source_id"],
            "source_id": source["source_id"],
            "source_url": source.get("url"),
            "source_type": source.get("source_type"),
            "publication_date": source.get("publication_date"),
            "credibility": source.get("credibility"),
            "confidence": claim.get("confidence"),
        },
    }


def run(context: Dict, attempt: int = 1) -> Dict:
    """Run the web research agent against its assigned sources.

    `context` must contain:
        - "research_question": str
        - "sources": List[Dict]  (the web sources to inspect)
        - "work_seconds": float  (simulated work time)
        - optional "failure": FailureInjection
    """
    question: str = context["research_question"]
    sources: List[Dict] = context["sources"]
    work_seconds: float = context.get("work_seconds", 0.5)
    failure: Optional[FailureInjection] = context.get("failure")

    findings: List[Dict] = []

    # Extract findings source-by-source so a mid-stream failure can still
    # return the partial results gathered so far.
    for source in sources:
        for i, claim in enumerate(source.get("claims", []), start=1):
            findings.append(_make_finding(source, claim, i))

        # Simulate per-source latency.
        time.sleep(work_seconds / max(len(sources), 1))

        # Inject a failure if configured and this attempt should still fail.
        if failure and failure.should_fail(AGENT_NAME, attempt):
            partial = findings if failure.partial_on_failure else []
            raise AgentFailure(
                failure_type=failure.failure_type,
                attempted_query=question,
                message=f"{failure.failure_type} while querying {source['source_id']}",
                partial_results=partial,
            )

    return {
        "status": "ok",
        "agent": AGENT_NAME,
        "attempted_query": question,
        "findings": findings,
    }
