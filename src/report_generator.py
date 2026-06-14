"""Render the final Markdown synthesis report from the synthesis output."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional


def _format_attribution(a: Dict) -> str:
    locator = a.get("source_url") or a.get("source") or "unknown source"
    date = a.get("publication_date") or "n/a"
    conf = a.get("confidence")
    conf_str = f", confidence {conf}" if conf is not None else ""
    agent = a.get("agent") or "unknown agent"
    return f"  - **{a.get('source')}** ({locator}, published {date}{conf_str}) — via `{agent}`"


def _well_established_section(items: List[Dict]) -> str:
    if not items:
        return "_No findings were corroborated by multiple sources._\n"
    lines: List[str] = []
    for item in items:
        lines.append(f"### {item['claim']}")
        lines.append(f"Supported by {item['source_count']} independent sources.\n")
        for a in item["supporting_sources"]:
            lines.append(f"  - _Evidence:_ \"{a.get('evidence_excerpt')}\"")
            lines.append(_format_attribution(a))
        lines.append("")
    return "\n".join(lines)


def _contested_section(items: List[Dict]) -> str:
    if not items:
        return "_No contested findings were detected._\n"
    lines: List[str] = []
    for item in items:
        lines.append(f"### {item['claim']}")
        lines.append(
            "Sources disagree. The synthesis agent **does not** select a single "
            "value; both credible positions are preserved below.\n"
        )
        for a in item["supporting_sources"]:
            value = a.get("value")
            value_str = f"**{value}**" if value is not None else "(no explicit value)"
            lines.append(f"  - {a.get('source')}: {value_str}")
            lines.append(f"    - _Evidence:_ \"{a.get('evidence_excerpt')}\"")
            lines.append(_format_attribution(a))
        lines.append("")
        lines.append("**Possible reasons for the discrepancy:**")
        for reason in item.get("possible_reasons", []):
            lines.append(f"  - {reason}")
        lines.append("")
    return "\n".join(lines)


def _single_source_section(items: List[Dict]) -> str:
    if not items:
        return "_No single-source findings._\n"
    lines: List[str] = []
    for item in items:
        lines.append(f"### {item['claim']}")
        lines.append("Supported by a single source (treat with caution).\n")
        for a in item["supporting_sources"]:
            lines.append(f"  - _Evidence:_ \"{a.get('evidence_excerpt')}\"")
            lines.append(_format_attribution(a))
        lines.append("")
    return "\n".join(lines)


def _coverage_gaps_section(gaps: List[str]) -> str:
    if not gaps:
        return (
            "_No coverage gaps — all subagents completed successfully._\n\n"
            "Any transient failures encountered during execution were recovered "
            "via retry (see `output/error_log.json`).\n"
        )
    lines = [
        "The following gaps in coverage were caused by subagent failures. "
        "They are reported transparently and were **not** silently hidden. "
        "Overall confidence in the report is reduced accordingly.\n"
    ]
    for gap in gaps:
        lines.append(f"  - {gap}")
    return "\n".join(lines)


def generate_report(
    synthesis: Dict,
    provenance_report: Dict,
    latency_comparison: Optional[Dict] = None,
) -> str:
    """Build the full synthesis_report.md content."""
    stats = synthesis["stats"]
    parts: List[str] = []

    parts.append("# Multi-Agent Research — Synthesis Report\n")
    parts.append(f"_Generated: {datetime.now().isoformat()}_\n")
    parts.append(f"**Research question:** {synthesis['research_question']}\n")

    parts.append("## Summary")
    parts.append(f"- Total findings: {stats['total_findings']}")
    parts.append(f"- Well-established: {stats['well_established']}")
    parts.append(f"- Contested: {stats['contested']}")
    parts.append(f"- Single-source: {stats['single_source']}\n")

    parts.append("## Well-Established Findings")
    parts.append(_well_established_section(synthesis["well_established_findings"]))

    parts.append("## Contested Findings")
    parts.append(_contested_section(synthesis["contested_findings"]))

    parts.append("## Single-Source Findings")
    parts.append(_single_source_section(synthesis["single_source_findings"]))

    parts.append("## Coverage Gaps")
    parts.append(_coverage_gaps_section(synthesis.get("coverage_gaps", [])))

    parts.append("## Provenance Summary")
    parts.append(
        f"- Total provenance records: {provenance_report['total_records']}"
    )
    for agent, count in provenance_report["records_by_agent"].items():
        parts.append(f"  - `{agent}`: {count} records")
    parts.append("")

    if latency_comparison:
        comp = latency_comparison["comparison"]
        parts.append("## Latency Comparison")
        parts.append("| Mode | Duration (s) |")
        parts.append("| ---------- | -------- |")
        parts.append(f"| Sequential | {comp['sequential_duration']} |")
        parts.append(f"| Parallel | {comp['parallel_duration']} |")
        parts.append("")
        parts.append(
            f"- Time saved: **{comp['time_saved']} s** "
            f"({comp['percentage_improvement']}% improvement)\n"
        )

    return "\n".join(parts)
