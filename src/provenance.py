"""Provenance tracking for the Multi-Agent Research Pipeline.

Every finding produced by any subagent is registered here so that the
final report can prove *where every claim came from*. No synthesized
finding is allowed to lose its attribution chain.

A ProvenanceRecord captures, for a single claim:

    - the originating agent
    - the source document and/or source URL
    - the publication date of the source
    - the timestamp at which the finding was recorded by the pipeline
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class ProvenanceRecord:
    """Immutable attribution record for a single claim."""

    agent: str
    claim_id: str
    source: str
    source_url: Optional[str]
    publication_date: Optional[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)


class ProvenanceTracker:
    """Collects ProvenanceRecords and produces a provenance report."""

    def __init__(self) -> None:
        self._records: List[ProvenanceRecord] = []

    def record(self, finding: Dict) -> ProvenanceRecord:
        """Register a structured finding and return its ProvenanceRecord.

        Expects a finding shaped as produced by the subagents:

            {
              "claim_id": "...",
              "content": {...},
              "metadata": {
                  "agent": "...",
                  "source": "...",
                  "source_url": "...",
                  "publication_date": "...",
                  ...
              }
            }
        """
        meta = finding.get("metadata", {})
        record = ProvenanceRecord(
            agent=meta.get("agent", "unknown"),
            claim_id=finding.get("claim_id", "unknown"),
            source=meta.get("source", "unknown"),
            source_url=meta.get("source_url"),
            publication_date=meta.get("publication_date"),
        )
        self._records.append(record)
        return record

    def record_many(self, findings: List[Dict]) -> List[ProvenanceRecord]:
        return [self.record(f) for f in findings]

    @property
    def records(self) -> List[ProvenanceRecord]:
        return list(self._records)

    def claim_ids(self) -> List[str]:
        return [r.claim_id for r in self._records]

    def validate(self, findings: List[Dict]) -> Dict:
        """Verify that every finding has a complete provenance chain.

        Returns a validation summary describing any findings that are
        missing attribution. A finding is considered fully attributed when
        it has an originating agent, a source, a publication date, and at
        least one of (source document, source URL).
        """
        tracked_ids = set(self.claim_ids())
        missing_attribution: List[str] = []
        untracked: List[str] = []

        for f in findings:
            cid = f.get("claim_id", "unknown")
            meta = f.get("metadata", {})
            if cid not in tracked_ids:
                untracked.append(cid)
            has_origin = bool(meta.get("agent"))
            has_locator = bool(meta.get("source") or meta.get("source_url"))
            has_date = bool(meta.get("publication_date"))
            if not (has_origin and has_locator and has_date):
                missing_attribution.append(cid)

        return {
            "total_findings": len(findings),
            "total_records": len(self._records),
            "untracked_claims": untracked,
            "claims_missing_attribution": missing_attribution,
            "all_attributed": not missing_attribution and not untracked,
        }

    def report(self) -> Dict:
        """Produce a structured provenance report."""
        by_agent: Dict[str, int] = {}
        for r in self._records:
            by_agent[r.agent] = by_agent.get(r.agent, 0) + 1
        return {
            "generated_at": datetime.now().isoformat(),
            "total_records": len(self._records),
            "records_by_agent": by_agent,
            "records": [r.to_dict() for r in self._records],
        }
