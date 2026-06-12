"""Cost analytics over parsed sessions.

Attributes token spend across projects, sessions, models, and tools. Token counts
are exact (from the API-reported usage); dollar figures appear only when you supply
Rates. Stdlib only.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from .model import Rates, Session


@dataclass
class CostReport:
    sessions: int = 0
    turns: int = 0
    output_tokens: int = 0
    input_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    by_project: Counter = field(default_factory=Counter)      # project -> output tokens
    by_model: Counter = field(default_factory=Counter)        # model -> turns
    by_tool_result: Counter = field(default_factory=Counter)  # tool -> result tokens
    by_tool_calls: Counter = field(default_factory=Counter)   # tool -> call count
    dollars: Optional[float] = None

    @property
    def total_input(self) -> int:
        return self.input_tokens + self.cache_read_tokens + self.cache_creation_tokens

    @property
    def cache_hit_rate(self) -> float:
        ti = self.total_input
        return self.cache_read_tokens / ti if ti else 0.0


def analyze_cost(sessions: list[Session], rates: Optional[Rates] = None) -> CostReport:
    r = CostReport(sessions=len(sessions))
    for s in sessions:
        r.turns += len(s.turns)
        r.output_tokens += s.output_tokens
        r.input_tokens += s.input_tokens
        r.cache_read_tokens += s.cache_read_tokens
        r.cache_creation_tokens += s.cache_creation_tokens
        r.by_project[s.project] += s.output_tokens
        for t in s.turns:
            if t.model:
                r.by_model[t.model] += 1
            for tc in t.tool_calls:
                r.by_tool_calls[tc.name] += 1
                r.by_tool_result[tc.name] += tc.result_tokens
    if rates:
        r.dollars = sum(s.cost(rates) for s in sessions)
    return r


# Published list-price rates per million tokens, for convenience. Users should
# confirm against their own plan; these are point-in-time reference values only.
KNOWN_RATES = {
    # model substring -> Rates(input, output, cache_read, cache_write)
    "opus": Rates(15.0, 75.0, 1.5, 18.75),
    "sonnet": Rates(3.0, 15.0, 0.3, 3.75),
    "haiku": Rates(0.8, 4.0, 0.08, 1.0),
}


def rates_for_model(model: str) -> Optional[Rates]:
    for key, rates in KNOWN_RATES.items():
        if key in model.lower():
            return rates
    return None


def by_day(sessions: list[Session]):
    """Output tokens and est. list-price dollars bucketed by calendar day (UTC).

    Returns a list of (date_str, output_tokens, dollars) sorted by date.
    """
    out = {}     # date -> output tokens
    dollars = {} # date -> dollars
    for s in sessions:
        for t in s.turns:
            if not t.timestamp:
                continue
            day = t.timestamp.date().isoformat()
            out[day] = out.get(day, 0) + t.output_tokens
            rates = rates_for_model(t.model)
            if rates:
                dollars[day] = dollars.get(day, 0.0) + rates.turn_cost(t)
    return [(d, out[d], dollars.get(d, 0.0)) for d in sorted(out)]


def blended_dollars(sessions: list[Session]) -> Optional[float]:
    """Estimate cost using per-model known rates, summed across turns.

    Returns None if no turn matches a known model. This is an upper-bound estimate
    against list prices and ignores plan discounts.
    """
    total = 0.0
    matched = False
    for s in sessions:
        for t in s.turns:
            rates = rates_for_model(t.model)
            if rates:
                matched = True
                total += rates.turn_cost(t)
    return total if matched else None
