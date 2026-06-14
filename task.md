# Exercise 4 - Claude Code Automation Prompt

You are acting as a Principal AI Architect specializing in Agentic Systems, Multi-Agent Orchestration, Reliability Engineering, and Anthropic Claude Code.

Your task is to design, implement, test, and document a complete Multi-Agent Research Pipeline.

The final repository should be written as if it is being submitted for instructor evaluation.

The implementation must demonstrate:

- Agent orchestration
- Task tool delegation
- Context management
- Parallel execution
- Provenance tracking
- Error propagation
- Conflict resolution
- Reliability analysis

---

# Objective

Demonstrate the following concepts:

1. Coordinator Agent
2. Multiple Subagents
3. Explicit Context Passing
4. Parallel Task Execution
5. Structured Findings
6. Provenance Preservation
7. Error Propagation
8. Partial Result Recovery
9. Conflict Handling
10. Latency Analysis

---

# Repository Structure

Create the following project structure:

.
├── README.md
├── requirements.txt
├── architecture
│ ├── agent_design.md
│ ├── orchestration_flow.md
│ └── sequence_diagram.md
├── prompts
│ ├── coordinator_prompt.md
│ ├── web_research_agent.md
│ ├── document_analysis_agent.md
│ └── synthesis_agent.md
├── sample_data
│ ├── research_question.txt
│ ├── source_a.json
│ ├── source_b.json
│ ├── conflicting_source_1.json
│ └── conflicting_source_2.json
├── src
│ ├── coordinator.py
│ ├── web_research_agent.py
│ ├── document_analysis_agent.py
│ ├── synthesis_agent.py
│ ├── provenance.py
│ ├── error_handler.py
│ ├── latency_tracker.py
│ └── report_generator.py
├── output
│ ├── findings.json
│ ├── synthesis_report.md
│ ├── error_log.json
│ └── latency_results.json
└── tests
├── test_parallel_execution.py
├── test_provenance.py
├── test_error_handling.py
└── test_conflict_resolution.py

---

# Part 1 - Coordinator Agent

Create a Coordinator Agent.

Responsibilities:

- Receive research question
- Launch subagents
- Aggregate findings
- Handle failures
- Track provenance
- Produce final report

Coordinator must support:

allowedTools:

- Task

Do not rely on automatic context inheritance.

Every subagent must receive all required context explicitly.

Example:

BAD:

Assume subagent automatically sees previous results.

GOOD:

Pass findings directly in prompt.

---

# Part 2 - Subagents

Implement at least two subagents.

## Agent A

Web Research Agent

Responsibilities:

- Search sources
- Extract findings
- Return structured output

## Agent B

Document Analysis Agent

Responsibilities:

- Analyze documents
- Extract evidence
- Return structured output

Optional:

## Agent C

Synthesis Agent

Responsibilities:

- Merge findings
- Preserve attribution
- Generate report

---

# Part 3 - Structured Findings

Every subagent must return structured JSON.

Example:

{
"claim": "Company revenue increased by 15%",
"evidence_excerpt": "Revenue increased from $100M to $115M",
"source": "https://example.com/report",
"publication_date": "2025-05-01",
"confidence": 0.92
}

Requirements:

Separate:

- content
- metadata

Metadata must include:

- source
- publication date
- confidence
- agent name

No synthesized finding may lose attribution.

---

# Part 4 - Provenance Tracking

Implement provenance tracking.

Every finding must preserve:

- originating agent
- source document
- source URL
- publication date

Create provenance.py.

Implement:

ProvenanceRecord

Example:

{
"agent": "web_research_agent",
"claim_id": "claim_001",
"source": "...",
"publication_date": "...",
"timestamp": "..."
}

Generate provenance report.

---

# Part 5 - Parallel Task Execution

Implement two execution modes.

## Sequential

Coordinator calls:

Task A
wait

Task B
wait

Measure latency.

---

## Parallel

Coordinator emits:

Task A
Task B

within a single response.

Measure:

- start time
- end time
- total duration

Record:

latency_results.json

Compare:

| Mode       | Duration |
| ---------- | -------- |
| Sequential | X sec    |
| Parallel   | Y sec    |

Calculate:

- time saved
- percentage improvement

Document findings.

---

# Part 6 - Error Propagation

Simulate failures.

Examples:

- timeout
- API unavailable
- malformed response

Subagent must return structured error.

Example:

{
"status": "failed",
"failure_type": "timeout",
"attempted_query": "AI market growth",
"partial_results": [
...
]
}

Coordinator must:

- receive error context
- log error
- continue execution

Create:

error_log.json

---

# Coverage Gap Reporting

If a subagent fails:

Final report must include:

## Coverage Gaps

Example:

Document analysis unavailable due to timeout.

Findings are based only on web sources.

Confidence reduced.

Do not silently hide failures.

---

# Part 7 - Conflicting Source Test

Create a scenario where:

Source A:

"Market growth = 18%"

Source B:

"Market growth = 23%"

Both are credible.

Verify synthesis agent:

DOES NOT choose one value arbitrarily.

Expected output:

Contested Findings

Source A:
18%

Source B:
23%

Explain possible reasons for discrepancy.

Maintain attribution.

---

# Part 8 - Well Established vs Contested Findings

Synthesis report must contain sections:

## Well-Established Findings

Findings supported by multiple sources.

## Contested Findings

Findings with conflicting evidence.

Each section must contain:

- claim
- evidence
- source attribution

---

# Part 9 - Reliability Testing

Execute tests for:

1. Coordinator orchestration
2. Context passing
3. Provenance preservation
4. Parallel execution
5. Error propagation
6. Conflict handling

Record:

- passed tests
- failed tests
- execution time

---

# Part 10 - Architecture Documentation

Generate Mermaid diagrams.

Architecture Diagram:

Research Question
→ Coordinator
→ Web Agent
→ Document Agent
→ Synthesis Agent
→ Final Report

---

Sequence Diagram

Show:

Coordinator
→ Task Calls
→ Parallel Execution
→ Error Handling
→ Synthesis

---

# Validation

Run and record:

- unit tests
- orchestration tests
- provenance tests
- latency tests
- conflict tests

Capture:

commands executed
outputs
pass/fail status

Store results.

---

# README Requirements

README.md must contain:

## 1. Exercise Overview

Objectives and requirements.

## 2. Architecture

Explain all agents.

Include Mermaid diagrams.

## 3. Coordinator Design

Explain orchestration decisions.

## 4. Context Management

Explain explicit context passing.

Compare:

automatic inheritance vs explicit passing.

## 5. Structured Findings

Explain schema design.

## 6. Provenance Tracking

Explain attribution strategy.

## 7. Parallel Execution

Present latency measurements.

Include comparison table.

## 8. Error Propagation

Explain failure handling.

Show examples.

## 9. Conflict Resolution

Explain contested findings.

Show example output.

## 10. Reliability Analysis

Discuss:

- strengths
- weaknesses
- future improvements

## 11. Validation Results

Include:

commands
outputs
test summaries

## 12. Lessons Learned

Document key takeaways.

## 13. Final Conclusion

Summarize architecture and reliability findings.

---

# Deliverables

After implementation is complete display:

1. Final directory tree
2. Agent architecture summary
3. Latency comparison table
4. Error propagation summary
5. Conflict resolution summary
6. Provenance validation summary
7. Test results summary
8. Completion checklist

The repository should be complete enough that another engineer can review the README and understand the entire multi-agent system without rerunning the project.
