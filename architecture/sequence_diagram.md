# Sequence Diagram

Shows coordinator Task calls, parallel execution, error handling, and
synthesis.

```mermaid
sequenceDiagram
    participant U as User
    participant C as Coordinator
    participant A as Web Research Agent
    participant B as Document Analysis Agent
    participant S as Synthesis Agent

    U->>C: Research question
    Note over C: Load sources, assign by `assigned_agent`,<br/>build explicit context per agent

    par Parallel Task dispatch (single response)
        C->>A: Task(context = question + web sources)
        C->>B: Task(context = question + documents)
    end

    A-->>C: { status: ok, findings: [...] }

    Note over B: timeout on attempt 1
    B-->>C: AgentFailure(timeout, partial_results)
    C->>B: retry (attempt 2)
    B-->>C: { status: ok, findings: [...] }
    Note over C: log error event (recovered = true)

    Note over C: Aggregate findings,<br/>record provenance,<br/>collect coverage gaps

    C->>S: Task(context = all findings + coverage gaps)
    S-->>C: well-established / contested / single-source<br/>(attribution preserved)

    C->>U: synthesis_report.md + findings.json +<br/>error_log.json + latency_results.json
```

## Terminal-failure variant

If Agent B fails on *every* attempt, the coordinator:
1. Receives a structured error with `partial_results`.
2. Logs the error (`recovered = false`).
3. Adds a **Coverage Gap** entry to the report.
4. Continues synthesis using the surviving (web) findings + any partials.
