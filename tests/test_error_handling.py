"""Reliability tests: error propagation, recovery, and coverage gaps."""

import coordinator
from error_handler import (
    ErrorLog,
    FailureInjection,
    AgentFailure,
    run_with_recovery,
)
import document_analysis_agent


def test_transient_failure_is_recovered():
    """A failure that succeeds on retry must not produce a coverage gap."""
    failure = FailureInjection(
        agent="document_analysis_agent",
        failure_type="timeout",
        attempts_until_success=1,
    )
    coord = coordinator.Coordinator(work_seconds=0.01, failure=failure)
    result = coord.run_pipeline(mode="parallel")
    # Recovered -> no coverage gaps, but the error was still logged.
    assert result["coverage_gaps"] == []
    assert len(result["error_log"]) >= 1
    assert all(e["recovered"] for e in result["error_log"])


def test_terminal_failure_creates_coverage_gap():
    """A failure on every attempt must surface a coverage gap (not hidden)."""
    failure = FailureInjection(
        agent="document_analysis_agent",
        failure_type="timeout",
        attempts_until_success=0,  # terminal
    )
    coord = coordinator.Coordinator(work_seconds=0.01, failure=failure)
    result = coord.run_pipeline(mode="parallel")
    assert len(result["coverage_gaps"]) == 1
    assert "document_analysis_agent" in result["coverage_gaps"][0]
    assert "timeout" in result["coverage_gaps"][0]
    # Web agent findings must survive; pipeline continues.
    assert any(
        f["metadata"]["agent"] == "web_research_agent" for f in result["findings"]
    )


def test_structured_error_carries_partial_results():
    """On terminal failure, the structured error keeps partial results."""
    log = ErrorLog()

    def always_fail(attempt):
        raise AgentFailure(
            failure_type="api_unavailable",
            attempted_query="AI market growth",
            message="boom",
            partial_results=[{"claim_id": "p1"}],
        )

    result = run_with_recovery(
        agent_name="document_analysis_agent",
        attempted_query="AI market growth",
        fn=always_fail,
        error_log=log,
        max_retries=2,
    )
    assert result["status"] == "failed"
    assert result["failure_type"] == "api_unavailable"
    assert result["partial_results"] == [{"claim_id": "p1"}]
    assert len(log.events) == 2  # one event per attempt


def test_terminal_failure_recovers_partial_findings():
    """Partial results gathered before a terminal failure are retained."""
    failure = FailureInjection(
        agent="document_analysis_agent",
        failure_type="malformed_response",
        attempts_until_success=0,
        partial_on_failure=True,
    )
    coord = coordinator.Coordinator(work_seconds=0.01, failure=failure)
    result = coord.run_pipeline(mode="parallel")
    doc_findings = [
        f for f in result["findings"]
        if f["metadata"]["agent"] == "document_analysis_agent"
    ]
    # The document agent failed terminally but had extracted partial results
    # from the first source before failing.
    assert len(doc_findings) >= 1
