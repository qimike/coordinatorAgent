"""Latency measurement for sequential vs. parallel orchestration."""

from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass
class TaskTiming:
    agent: str
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start

    def to_dict(self) -> Dict:
        return {
            "agent": self.agent,
            "start": round(self.start, 6),
            "end": round(self.end, 6),
            "duration": round(self.duration, 6),
        }


class LatencyTracker:
    """Records per-task timings for a single execution mode."""

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self._timings: List[TaskTiming] = []
        self._mode_start: float = 0.0
        self._mode_end: float = 0.0

    def begin(self) -> None:
        self._mode_start = time.perf_counter()

    def finish(self) -> None:
        self._mode_end = time.perf_counter()

    def add(self, agent: str, start: float, end: float) -> None:
        self._timings.append(TaskTiming(agent=agent, start=start, end=end))

    @property
    def total_duration(self) -> float:
        return self._mode_end - self._mode_start

    def summary(self) -> Dict:
        return {
            "mode": self.mode,
            "total_duration": round(self.total_duration, 6),
            "tasks": [t.to_dict() for t in self._timings],
        }


def compare(sequential: LatencyTracker, parallel: LatencyTracker) -> Dict:
    """Build the sequential-vs-parallel comparison block."""
    seq = sequential.total_duration
    par = parallel.total_duration
    time_saved = seq - par
    pct = (time_saved / seq * 100.0) if seq > 0 else 0.0
    return {
        "sequential": sequential.summary(),
        "parallel": parallel.summary(),
        "comparison": {
            "sequential_duration": round(seq, 6),
            "parallel_duration": round(par, 6),
            "time_saved": round(time_saved, 6),
            "percentage_improvement": round(pct, 2),
        },
    }
