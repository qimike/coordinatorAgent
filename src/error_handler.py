"""Structured error propagation and recovery for the pipeline.

Subagents never crash the coordinator. When a subagent fails it returns a
*structured error* describing the failure type, the query it attempted, and
any partial results it had already gathered. The coordinator logs the error,
records a coverage gap, and continues execution with the surviving results.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Callable, Dict, List, Optional


# --- Failure types we model -------------------------------------------------
TIMEOUT = "timeout"
API_UNAVAILABLE = "api_unavailable"
MALFORMED_RESPONSE = "malformed_response"


class AgentFailure(Exception):
    """Raised inside a subagent to signal a structured, recoverable failure."""

    def __init__(
        self,
        failure_type: str,
        attempted_query: str,
        message: str = "",
        partial_results: Optional[List[Dict]] = None,
    ) -> None:
        super().__init__(message or failure_type)
        self.failure_type = failure_type
        self.attempted_query = attempted_query
        self.partial_results = partial_results or []

    def to_structured(self, agent: str) -> Dict:
        return structured_error(
            agent=agent,
            failure_type=self.failure_type,
            attempted_query=self.attempted_query,
            message=str(self),
            partial_results=self.partial_results,
        )


def structured_error(
    agent: str,
    failure_type: str,
    attempted_query: str,
    message: str = "",
    partial_results: Optional[List[Dict]] = None,
) -> Dict:
    """Build the canonical structured-error payload returned by subagents."""
    return {
        "status": "failed",
        "agent": agent,
        "failure_type": failure_type,
        "attempted_query": attempted_query,
        "message": message,
        "partial_results": partial_results or [],
        "timestamp": datetime.now().isoformat(),
    }


@dataclass
class FailureInjection:
    """Configuration that tells an agent to simulate a failure.

    `attempts_until_success` controls recovery semantics:
      * 0  -> the agent fails on every attempt (terminal failure).
      * N  -> the agent fails on the first N attempts, then succeeds
              (transient failure recovered via retry).
    """

    agent: str
    failure_type: str = TIMEOUT
    attempts_until_success: int = 0
    partial_on_failure: bool = True

    def should_fail(self, agent: str, attempt: int) -> bool:
        """Whether `agent` should simulate a failure on this attempt.

        Terminal failure (attempts_until_success == 0) fails on every attempt.
        Transient failure (== N) fails while attempt <= N, then recovers.
        """
        if self.agent != agent:
            return False
        if self.attempts_until_success == 0:
            return True
        return attempt <= self.attempts_until_success


@dataclass
class ErrorEvent:
    agent: str
    failure_type: str
    attempted_query: str
    message: str
    attempt: int
    recovered: bool
    partial_results: List[Dict] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)


class ErrorLog:
    """Accumulates ErrorEvents and serialises them to error_log.json."""

    def __init__(self) -> None:
        self._events: List[ErrorEvent] = []

    def log(self, event: ErrorEvent) -> None:
        self._events.append(event)

    @property
    def events(self) -> List[ErrorEvent]:
        return list(self._events)

    def to_list(self) -> List[Dict]:
        return [e.to_dict() for e in self._events]

    def has_errors(self) -> bool:
        return bool(self._events)


def run_with_recovery(
    agent_name: str,
    attempted_query: str,
    fn: Callable[[int], Dict],
    error_log: ErrorLog,
    max_retries: int = 2,
) -> Dict:
    """Execute `fn(attempt)` with retry/recovery and structured error logging.

    Returns the agent's successful result dict, or — if every attempt fails —
    a structured error payload (so the coordinator can keep going with
    partial / no results from this agent).
    """
    last_error: Optional[AgentFailure] = None
    for attempt in range(1, max_retries + 1):
        try:
            return fn(attempt)
        except AgentFailure as exc:
            last_error = exc
            recovered = attempt < max_retries
            error_log.log(
                ErrorEvent(
                    agent=agent_name,
                    failure_type=exc.failure_type,
                    attempted_query=exc.attempted_query,
                    message=str(exc),
                    attempt=attempt,
                    recovered=False,  # set True below if a later attempt wins
                    partial_results=exc.partial_results,
                )
            )
            if not recovered:
                break
    # All attempts exhausted -> terminal failure for this agent.
    assert last_error is not None
    return last_error.to_structured(agent_name)


def mark_recovered(error_log: ErrorLog, agent_name: str) -> None:
    """Flag the logged failures for an agent as ultimately recovered."""
    for event in error_log.events:
        if event.agent == agent_name:
            event.recovered = True
