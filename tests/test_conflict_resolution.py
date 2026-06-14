"""Reliability tests: conflict handling + well-established classification."""

import coordinator
import synthesis_agent


def test_conflicting_values_are_contested_not_arbitrarily_chosen():
    result = coordinator.Coordinator(work_seconds=0.01).run_pipeline(mode="parallel")
    contested = result["synthesis"]["contested_findings"]
    # The market-growth topic (18% vs 23%) must be flagged as contested.
    growth = [c for c in contested if c.get("topic") == "market_growth_rate"]
    assert len(growth) == 1
    values = set(growth[0]["conflicting_values"])
    assert values == {"18%", "23%"}
    # Both sources must be preserved with attribution.
    assert len(growth[0]["supporting_sources"]) == 2
    assert growth[0].get("possible_reasons")


def test_well_established_requires_multiple_sources():
    result = coordinator.Coordinator(work_seconds=0.01).run_pipeline(mode="parallel")
    well = result["synthesis"]["well_established_findings"]
    # "Enterprise AI adoption is accelerating" appears in source_a and source_b.
    adoption = [w for w in well if w["topic"] == "enterprise_adoption"]
    assert len(adoption) == 1
    assert adoption[0]["source_count"] >= 2


def test_synthesis_preserves_all_attribution_in_contested():
    findings = [
        {
            "claim_id": "c1",
            "content": {"claim": "growth", "topic": "g", "value": "18%",
                        "evidence_excerpt": "e1"},
            "metadata": {"agent": "web_research_agent", "source": "A",
                         "source_url": "u1", "publication_date": "2025-01-01",
                         "confidence": 0.8},
        },
        {
            "claim_id": "c2",
            "content": {"claim": "growth", "topic": "g", "value": "23%",
                        "evidence_excerpt": "e2"},
            "metadata": {"agent": "document_analysis_agent", "source": "B",
                         "source_url": None, "publication_date": "2025-02-01",
                         "confidence": 0.8},
        },
    ]
    synthesis = synthesis_agent.run(
        {"research_question": "Q", "findings": findings, "coverage_gaps": []}
    )
    assert len(synthesis["contested_findings"]) == 1
    sources = {a["source"] for a in synthesis["contested_findings"][0]["supporting_sources"]}
    assert sources == {"A", "B"}
