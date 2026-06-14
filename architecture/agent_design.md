# Agent Design

This document describes the four agents in the pipeline, their
responsibilities, inputs, outputs, and failure behaviour.

## Roles at a glance

| Agent | Type | Reads | Produces |
| --- | --- | --- | --- |
| Coordinator | Orchestrator | Research question, all sources | Aggregated findings, final report, logs |
| Web Research Agent (A) | Subagent | Web sources assigned to it | Structured findings |
| Document Analysis Agent (B) | Subagent | Document sources assigned to it | Structured findings |
| Synthesis Agent (C) | Subagent | Findings handed to it by the coordinator | Classified, attributed report data |

## 1. Coordinator Agent

The coordinator is the only stateful component. It owns the provenance
tracker, the error log, and the list of coverage gaps.

Responsibilities:
- Receive the research question.
- Load sources and **explicitly** assign each to the correct subagent
  (`assigned_agent` field in each source file).
- Launch subagents either sequentially or in parallel.
- Wrap every subagent call with retry/recovery (`run_with_recovery`).
- Aggregate findings, recovering partial results when an agent fails.
- Record provenance for every finding.
- Record a transparent **coverage gap** for any agent that fails terminally.
- Delegate merge + conflict resolution to the synthesis agent.
- Write all machine-readable outputs and the Markdown report.

`allowedTools: [Task]` — in the Claude Code mapping (see
`prompts/coordinator_prompt.md`) the coordinator may only delegate via the
Task tool; it does not do research itself.

## 2. Web Research Agent (Agent A)

- **Input context:** `research_question`, `sources` (web), `work_seconds`,
  optional `failure` injection.
- **Output:** `{ "status": "ok", "findings": [...] }` or a structured error.
- Extracts each source claim into a finding with **content** (claim,
  evidence, topic, value) cleanly separated from **metadata** (agent,
  source, URL, date, confidence, credibility).
- Stateless: it knows nothing the coordinator did not put in `context`.

## 3. Document Analysis Agent (Agent B)

Same contract as Agent A but oriented at documents (uses `document_name` as
the primary source locator). Demonstrates that heterogeneous agents share one
structured-finding schema.

## 4. Synthesis Agent (Agent C)

- **Input context:** `research_question`, `findings`, `coverage_gaps`.
- Groups findings by `topic` (falling back to normalized claim text).
- Classifies each group:
  - **Contested** — two or more distinct `value`s for the same topic. The
    agent preserves *all* positions and never picks a winner.
  - **Well-established** — supported by two or more distinct sources with no
    value conflict.
  - **Single-source** — exactly one supporting source.
- Preserves full attribution on every finding in every bucket.

## Shared structured-finding schema

```json
{
  "claim_id": "source_a_claim_1",
  "content": {
    "claim": "Enterprise AI adoption is accelerating",
    "evidence_excerpt": "72% of enterprises increased AI spending in 2025 ...",
    "topic": "enterprise_adoption",
    "value": null
  },
  "metadata": {
    "agent": "web_research_agent",
    "source": "Global AI Market Trends 2025",
    "source_id": "source_a",
    "source_url": "https://techinsights.example.com/ai-market-2025",
    "source_type": "web",
    "publication_date": "2025-04-15",
    "credibility": 0.88,
    "confidence": 0.9
  }
}
```

Content and metadata are deliberately separated so that provenance can be
validated independently of the claim itself.
