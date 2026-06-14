"""Reliability tests: provenance preservation + explicit context passing."""

import coordinator
from provenance import ProvenanceTracker


def test_every_finding_has_full_attribution():
    result = coordinator.Coordinator(work_seconds=0.01).run_pipeline(mode="parallel")
    validation = result["provenance_validation"]
    assert validation["all_attributed"] is True
    assert validation["claims_missing_attribution"] == []
    assert validation["untracked_claims"] == []


def test_provenance_record_fields():
    tracker = ProvenanceTracker()
    finding = {
        "claim_id": "claim_001",
        "content": {"claim": "x"},
        "metadata": {
            "agent": "web_research_agent",
            "source": "Report",
            "source_url": "https://example.com",
            "publication_date": "2025-05-01",
        },
    }
    record = tracker.record(finding)
    assert record.agent == "web_research_agent"
    assert record.claim_id == "claim_001"
    assert record.source_url == "https://example.com"
    assert record.timestamp  # auto-populated


def test_context_is_passed_explicitly_not_inherited():
    """Each agent must receive the question + sources in its context dict."""
    coord = coordinator.Coordinator(work_seconds=0.01)
    ctx = coord.build_context("web_research_agent", "Q?", [{"source_id": "s"}])
    assert ctx["research_question"] == "Q?"
    assert ctx["sources"] == [{"source_id": "s"}]


def test_no_synthesized_finding_loses_attribution():
    result = coordinator.Coordinator(work_seconds=0.01).run_pipeline(mode="parallel")
    synthesis = result["synthesis"]
    for bucket in ("well_established_findings", "contested_findings", "single_source_findings"):
        for item in synthesis[bucket]:
            assert item["supporting_sources"]
            for a in item["supporting_sources"]:
                assert a["source"]
                assert a["agent"]
