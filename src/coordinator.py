"""Coordinator Agent — orchestrates the Multi-Agent Research Pipeline.

The coordinator is the only component that holds global state. It:

  1. Receives the research question.
  2. Loads sources and *explicitly* assigns each to the right subagent.
  3. Launches subagents (sequentially or in parallel) with retry/recovery.
  4. Aggregates structured findings (recovering partial results on failure).
  5. Tracks provenance for every finding.
  6. Records coverage gaps for any agent that fails terminally.
  7. Delegates merging/conflict-resolution to the synthesis agent.
  8. Produces the final report + machine-readable outputs.

Design note — explicit context passing
---------------------------------------
The coordinator never assumes a subagent can "see" prior results. Each agent
receives a fully-populated `context` dict containing exactly what it needs.
This mirrors the Claude Code Task-tool model, where a subagent starts with a
fresh context window and only knows what its prompt tells it.
"""

from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

import web_research_agent
import document_analysis_agent
import synthesis_agent
from error_handler import (
    ErrorLog,
    FailureInjection,
    mark_recovered,
    run_with_recovery,
)
from latency_tracker import LatencyTracker, compare
from provenance import ProvenanceTracker
from report_generator import generate_report

# --- Paths ------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(_HERE)
SAMPLE_DATA = os.path.join(REPO_ROOT, "sample_data")
OUTPUT_DIR = os.path.join(REPO_ROOT, "output")

# Map each agent to its module and the default simulated work time.
AGENT_MODULES = {
    web_research_agent.AGENT_NAME: web_research_agent,
    document_analysis_agent.AGENT_NAME: document_analysis_agent,
}
DEFAULT_WORK_SECONDS = 0.5


# --- Loading ----------------------------------------------------------------
def load_research_question() -> str:
    with open(os.path.join(SAMPLE_DATA, "research_question.txt"), encoding="utf-8") as fh:
        return fh.read().strip()


def load_sources() -> List[Dict]:
    sources: List[Dict] = []
    for name in sorted(os.listdir(SAMPLE_DATA)):
        if name.endswith(".json"):
            with open(os.path.join(SAMPLE_DATA, name), encoding="utf-8") as fh:
                sources.append(json.load(fh))
    return sources


def assign_sources(sources: List[Dict]) -> Dict[str, List[Dict]]:
    """Group sources by the agent declared in each source's `assigned_agent`."""
    assignments: Dict[str, List[Dict]] = {name: [] for name in AGENT_MODULES}
    for src in sources:
        agent = src.get("assigned_agent")
        if agent in assignments:
            assignments[agent].append(src)
    return assignments


class Coordinator:
    def __init__(
        self,
        work_seconds: float = DEFAULT_WORK_SECONDS,
        failure: Optional[FailureInjection] = None,
    ) -> None:
        self.work_seconds = work_seconds
        self.failure = failure
        self.error_log = ErrorLog()
        self.provenance = ProvenanceTracker()
        self.coverage_gaps: List[str] = []

    # --- context construction (explicit passing) ---------------------------
    def build_context(self, agent_name: str, question: str, sources: List[Dict]) -> Dict:
        return {
            "research_question": question,
            "sources": sources,
            "work_seconds": self.work_seconds,
            "failure": self.failure,
        }

    # --- single subagent invocation with recovery --------------------------
    def _invoke_agent(self, agent_name: str, context: Dict) -> Dict:
        module = AGENT_MODULES[agent_name]

        def attempt_fn(attempt: int) -> Dict:
            return module.run(context, attempt=attempt)

        result = run_with_recovery(
            agent_name=agent_name,
            attempted_query=context["research_question"],
            fn=attempt_fn,
            error_log=self.error_log,
            max_retries=2,
        )

        if result.get("status") == "failed":
            # Terminal failure: record a transparent coverage gap, keep partial.
            self.coverage_gaps.append(
                f"{agent_name} unavailable due to {result['failure_type']}. "
                f"Findings from this agent are limited to {len(result.get('partial_results', []))} "
                f"partial result(s); overall confidence is reduced."
            )
            return {
                "agent": agent_name,
                "findings": result.get("partial_results", []),
                "error": result,
            }

        # Success (possibly after a recovered transient failure).
        mark_recovered(self.error_log, agent_name)
        return {"agent": agent_name, "findings": result["findings"], "error": None}

    # --- orchestration modes -----------------------------------------------
    def run_subagents(
        self,
        question: str,
        assignments: Dict[str, List[Dict]],
        mode: str,
        tracker: Optional[LatencyTracker] = None,
    ) -> List[Dict]:
        """Run all subagents in `mode` ('sequential' or 'parallel')."""
        agent_names = list(assignments.keys())

        def timed_call(agent_name: str) -> Dict:
            context = self.build_context(agent_name, question, assignments[agent_name])
            start = time.perf_counter()
            res = self._invoke_agent(agent_name, context)
            end = time.perf_counter()
            if tracker is not None:
                tracker.add(agent_name, start, end)
            return res

        results: List[Dict] = []
        if mode == "sequential":
            for name in agent_names:
                results.append(timed_call(name))
        elif mode == "parallel":
            # Emit all Task calls "within a single response": dispatch
            # concurrently and await completion.
            with ThreadPoolExecutor(max_workers=len(agent_names)) as pool:
                results = list(pool.map(timed_call, agent_names))
        else:
            raise ValueError(f"Unknown execution mode: {mode}")
        return results

    # --- full pipeline ------------------------------------------------------
    def run_pipeline(self, mode: str = "parallel") -> Dict:
        question = load_research_question()
        sources = load_sources()
        assignments = assign_sources(sources)

        tracker = LatencyTracker(mode)
        tracker.begin()
        agent_results = self.run_subagents(question, assignments, mode, tracker)
        tracker.finish()

        # Aggregate findings + provenance.
        all_findings: List[Dict] = []
        for res in agent_results:
            all_findings.extend(res["findings"])
        self.provenance.record_many(all_findings)

        # Delegate synthesis (merge + conflict resolution).
        synthesis = synthesis_agent.run(
            {
                "research_question": question,
                "findings": all_findings,
                "coverage_gaps": self.coverage_gaps,
            }
        )

        return {
            "question": question,
            "mode": mode,
            "findings": all_findings,
            "synthesis": synthesis,
            "latency": tracker.summary(),
            "provenance_report": self.provenance.report(),
            "provenance_validation": self.provenance.validate(all_findings),
            "error_log": self.error_log.to_list(),
            "coverage_gaps": self.coverage_gaps,
        }


# --- latency benchmark (separate, clean run) --------------------------------
def benchmark_latency(work_seconds: float = DEFAULT_WORK_SECONDS) -> Dict:
    question = load_research_question()
    sources = load_sources()
    assignments = assign_sources(sources)

    seq = LatencyTracker("sequential")
    seq_coord = Coordinator(work_seconds=work_seconds)
    seq.begin()
    seq_coord.run_subagents(question, assignments, "sequential", seq)
    seq.finish()

    par = LatencyTracker("parallel")
    par_coord = Coordinator(work_seconds=work_seconds)
    par.begin()
    par_coord.run_subagents(question, assignments, "parallel", par)
    par.finish()

    return compare(seq, par)


def _write_json(path: str, payload) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Main run: parallel mode, with a recoverable transient timeout injected
    # into the document analysis agent to exercise error propagation + retry
    # while still producing a complete report.
    failure = FailureInjection(
        agent=document_analysis_agent.AGENT_NAME,
        failure_type="timeout",
        attempts_until_success=1,  # fail once, recover on retry
    )
    coordinator = Coordinator(failure=failure)
    result = coordinator.run_pipeline(mode="parallel")

    # Separate, clean latency benchmark (no injected failures).
    latency = benchmark_latency()

    # --- write machine-readable outputs ---
    _write_json(os.path.join(OUTPUT_DIR, "findings.json"), result["findings"])
    _write_json(os.path.join(OUTPUT_DIR, "error_log.json"), result["error_log"])
    _write_json(os.path.join(OUTPUT_DIR, "latency_results.json"), latency)
    _write_json(
        os.path.join(OUTPUT_DIR, "provenance_report.json"),
        result["provenance_report"],
    )

    # --- write Markdown synthesis report ---
    report_md = generate_report(
        synthesis=result["synthesis"],
        provenance_report=result["provenance_report"],
        latency_comparison=latency,
    )
    with open(os.path.join(OUTPUT_DIR, "synthesis_report.md"), "w", encoding="utf-8") as fh:
        fh.write(report_md)

    # --- console deliverables ---
    comp = latency["comparison"]
    print("=" * 70)
    print("MULTI-AGENT RESEARCH PIPELINE — RUN COMPLETE")
    print("=" * 70)
    print(f"Research question: {result['question']}")
    print(f"Execution mode   : {result['mode']}")
    print(f"Total findings   : {len(result['findings'])}")
    print()
    stats = result["synthesis"]["stats"]
    print("Synthesis classification:")
    print(f"  well-established : {stats['well_established']}")
    print(f"  contested        : {stats['contested']}")
    print(f"  single-source    : {stats['single_source']}")
    print()
    print("Latency comparison:")
    print(f"  sequential : {comp['sequential_duration']} s")
    print(f"  parallel   : {comp['parallel_duration']} s")
    print(f"  time saved : {comp['time_saved']} s ({comp['percentage_improvement']}%)")
    print()
    print(f"Coverage gaps    : {len(result['coverage_gaps'])}")
    print(f"Error log events : {len(result['error_log'])}")
    val = result["provenance_validation"]
    print(f"Provenance valid : {val['all_attributed']} "
          f"({val['total_records']} records)")
    print(f"Outputs written  : {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
