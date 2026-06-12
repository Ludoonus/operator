"""Efficiency analytics — where tokens are wasted and how to fix it.

Detects the waste patterns from the cost playbook: re-read files, oversized tool
output, and low cache hit rate — and emits concrete, actionable recommendations.
Stdlib only, read-only.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .model import Session

CHARS_PER_TOKEN = 4


@dataclass
class Recommendation:
    severity: str       # "high" | "medium" | "low"
    title: str
    detail: str


@dataclass
class EfficiencyReport:
    reread_waste_tokens: int = 0
    reread_files: Counter = field(default_factory=Counter)     # path -> extra reads
    big_results: list[tuple] = field(default_factory=list)     # (tokens, tool, hint)
    cache_hit_rate: float = 0.0
    recommendations: list[Recommendation] = field(default_factory=list)


def analyze_efficiency(sessions: list[Session]) -> EfficiencyReport:
    rep = EfficiencyReport()

    # re-read waste: per session, a file read more than once costs (n-1) * its size
    reads_size: dict[str, int] = {}
    for s in sessions:
        per_file: Counter = Counter()
        for tc in s.tool_calls:
            if tc.name == "Read" and tc.file_path:
                per_file[tc.file_path] += 1
                reads_size[tc.file_path] = max(reads_size.get(tc.file_path, 0), tc.result_tokens)
            if tc.result_tokens > 5000:
                rep.big_results.append((tc.result_tokens, tc.name, tc.file_path or tc.command[:60]))
        for fp, n in per_file.items():
            if n > 1:
                rep.reread_waste_tokens += (n - 1) * reads_size.get(fp, 0)
                rep.reread_files[fp] += n - 1

    rep.big_results.sort(reverse=True)
    rep.big_results = rep.big_results[:15]

    total_in = sum(s.total_input for s in sessions)
    cache_read = sum(s.cache_read_tokens for s in sessions)
    rep.cache_hit_rate = cache_read / total_in if total_in else 0.0

    rep.recommendations = _recommend(rep, sessions)
    return rep


def _recommend(rep: EfficiencyReport, sessions: list[Session]) -> list[Recommendation]:
    recs: list[Recommendation] = []

    if rep.reread_waste_tokens > 5000:
        top = ", ".join(p.rsplit("/", 1)[-1] for p, _ in rep.reread_files.most_common(3))
        recs.append(Recommendation(
            "high",
            f"~{rep.reread_waste_tokens:,} tokens wasted re-reading files",
            f"Most re-read: {top}. Add a summary + key line numbers for these to "
            f"CLAUDE.md so sessions stop re-discovering them; read line ranges with "
            f"offset/limit instead of whole files.",
        ))

    if sessions and rep.cache_hit_rate < 0.5:
        recs.append(Recommendation(
            "high",
            f"Cache hit rate is {rep.cache_hit_rate*100:.0f}% (healthy: 70%+)",
            "Long idle gaps (5-min cache TTL) or oversized tool results churning the "
            "context. Batch interactions; trim tool output.",
        ))

    # oversized tool output by tool
    by_tool: Counter = Counter()
    calls: Counter = Counter()
    for s in sessions:
        for tc in s.tool_calls:
            by_tool[tc.name] += tc.result_tokens
            calls[tc.name] += 1
    for name, tok in by_tool.most_common(3):
        if name == "Bash" and tok > 50000:
            recs.append(Recommendation(
                "medium", f"Bash output ~{tok:,} tokens",
                "Filter at the source: `rg pattern | head`, `--quiet` on builds, "
                "`tail -30` on test runs instead of full dumps.",
            ))
        elif name == "Read" and tok > 80000:
            recs.append(Recommendation(
                "medium", f"Read output ~{tok:,} tokens",
                "Use offset/limit on large files; grep -n first, then read the range.",
            ))

    if rep.big_results:
        tok, tool, hint = rep.big_results[0]
        recs.append(Recommendation(
            "medium", f"Largest single result ~{tok:,} tokens ({tool})",
            f"{hint[:70]} — one result this size can evict the whole prompt cache.",
        ))

    if not recs:
        recs.append(Recommendation("low", "No major waste detected", "Usage looks efficient."))
    return recs
