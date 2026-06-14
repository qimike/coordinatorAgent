"""Synthesis Agent (Agent C).

Responsibilities:
  - Merge findings handed to it by the coordinator.
  - Preserve attribution for every claim (no finding loses its source).
  - Classify findings into:
        * Well-Established  -> supported by multiple sources, no conflict.
        * Contested         -> sources disagree on a value for the same topic.
        * Single-Source     -> supported by exactly one source.
  - Never arbitrarily pick a winner between conflicting credible sources.

The synthesis agent receives findings *explicitly* in its context; it does
not reach back into the coordinator or the other agents.
"""

from __future__ import annotations

from typing import Dict, List

AGENT_NAME = "synthesis_agent"


def _group_key(finding: Dict) -> str:
    """Group findings by topic when available, else by normalized claim text."""
    content = finding.get("content", {})
    topic = content.get("topic")
    if topic:
        return f"topic::{topic}"
    return f"claim::{content.get('claim', '').strip().lower()}"


def _attribution(finding: Dict) -> Dict:
    meta = finding.get("metadata", {})
    return {
        "claim_id": finding.get("claim_id"),
        "agent": meta.get("agent"),
        "source": meta.get("source"),
        "source_url": meta.get("source_url"),
        "publication_date": meta.get("publication_date"),
        "confidence": meta.get("confidence"),
        "credibility": meta.get("credibility"),
        "value": finding.get("content", {}).get("value"),
        "evidence_excerpt": finding.get("content", {}).get("evidence_excerpt"),
    }


def _discrepancy_reasons() -> List[str]:
    return [
        "Different forecasting methodologies or models.",
        "Different time horizons or base years for the projection.",
        "Different definitions of market scope (segments included/excluded).",
        "Different underlying data samples and survey populations.",
    ]


def run(context: Dict) -> Dict:
    """Synthesize findings.

    `context` must contain:
        - "research_question": str
        - "findings": List[Dict]
        - "coverage_gaps": List[str]  (failures reported by the coordinator)
    """
    question: str = context["research_question"]
    findings: List[Dict] = context["findings"]
    coverage_gaps: List[str] = context.get("coverage_gaps", [])

    groups: Dict[str, List[Dict]] = {}
    for f in findings:
        groups.setdefault(_group_key(f), []).append(f)

    well_established: List[Dict] = []
    contested: List[Dict] = []
    single_source: List[Dict] = []

    for key, members in groups.items():
        attributions = [_attribution(m) for m in members]
        distinct_sources = {a["source"] for a in attributions}
        distinct_values = {a["value"] for a in attributions if a["value"] is not None}
        claim_text = members[0]["content"].get("claim", "")

        entry = {
            "claim": claim_text,
            "topic": members[0]["content"].get("topic"),
            "supporting_sources": attributions,
            "source_count": len(distinct_sources),
        }

        if len(distinct_values) > 1:
            # Conflicting credible values -> contested. Do NOT pick one.
            entry["conflicting_values"] = sorted(distinct_values)
            entry["possible_reasons"] = _discrepancy_reasons()
            contested.append(entry)
        elif len(distinct_sources) > 1:
            well_established.append(entry)
        else:
            single_source.append(entry)

    return {
        "agent": AGENT_NAME,
        "research_question": question,
        "well_established_findings": well_established,
        "contested_findings": contested,
        "single_source_findings": single_source,
        "coverage_gaps": coverage_gaps,
        "stats": {
            "total_findings": len(findings),
            "well_established": len(well_established),
            "contested": len(contested),
            "single_source": len(single_source),
        },
    }
