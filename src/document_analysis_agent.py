"""Document Analysis Agent (Agent B).

Responsibilities:
  - Analyze the documents the coordinator explicitly hands it.
  - Extract evidence as structured findings (content vs. metadata).
  - Return structured JSON output, or a structured error on failure.

Like the web research agent, this agent is stateless and reads everything it
needs from the `context` argument — no automatic context inheritance.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from error_handler import AgentFailure, FailureInjection

AGENT_NAME = "document_analysis_agent"


def _make_finding(source: Dict, claim: Dict, index: int) -> Dict:
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
            "source": source.get("document_name") or source.get("title") or source["source_id"],
            "source_id": source["source_id"],
            "source_url": source.get("url"),
            "source_type": source.get("source_type"),
            "document_name": source.get("document_name"),
            "publication_date": source.get("publication_date"),
            "credibility": source.get("credibility"),
            "confidence": claim.get("confidence"),
        },
    }


def run(context: Dict, attempt: int = 1) -> Dict:
    """Analyze assigned documents and return structured findings.

    `context` must contain "research_question", "sources", "work_seconds",
    and optionally "failure" (a FailureInjection).
    """
    question: str = context["research_question"]
    sources: List[Dict] = context["sources"]
    work_seconds: float = context.get("work_seconds", 0.5)
    failure: Optional[FailureInjection] = context.get("failure")

    findings: List[Dict] = []

    for source in sources:
        for i, claim in enumerate(source.get("claims", []), start=1):
            findings.append(_make_finding(source, claim, i))

        time.sleep(work_seconds / max(len(sources), 1))

        if failure and failure.should_fail(AGENT_NAME, attempt):
            partial = findings if failure.partial_on_failure else []
            raise AgentFailure(
                failure_type=failure.failure_type,
                attempted_query=question,
                message=f"{failure.failure_type} while analyzing {source['source_id']}",
                partial_results=partial,
            )

    return {
        "status": "ok",
        "agent": AGENT_NAME,
        "attempted_query": question,
        "findings": findings,
    }
