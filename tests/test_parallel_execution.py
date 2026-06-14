"""Reliability tests: parallel vs. sequential execution + orchestration."""

import coordinator


def test_parallel_is_faster_than_sequential():
    """Parallel execution must measurably beat sequential for the same work."""
    result = coordinator.benchmark_latency(work_seconds=0.4)
    comp = result["comparison"]
    assert comp["parallel_duration"] < comp["sequential_duration"]
    assert comp["time_saved"] > 0
    assert comp["percentage_improvement"] > 0


def test_both_modes_produce_same_findings():
    """Execution mode must not change *what* is found, only how fast."""
    seq = coordinator.Coordinator(work_seconds=0.01).run_pipeline(mode="sequential")
    par = coordinator.Coordinator(work_seconds=0.01).run_pipeline(mode="parallel")
    seq_ids = sorted(f["claim_id"] for f in seq["findings"])
    par_ids = sorted(f["claim_id"] for f in par["findings"])
    assert seq_ids == par_ids
    assert len(seq_ids) > 0


def test_coordinator_orchestration_produces_synthesis():
    """Coordinator must aggregate findings and produce a synthesis structure."""
    result = coordinator.Coordinator(work_seconds=0.01).run_pipeline(mode="parallel")
    synthesis = result["synthesis"]
    assert "well_established_findings" in synthesis
    assert "contested_findings" in synthesis
    assert synthesis["stats"]["total_findings"] == len(result["findings"])
