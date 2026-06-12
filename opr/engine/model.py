"""Unified data model for agent operations.

Everything Operator computes is derived from these structures, parsed once from the
raw transcripts. Stdlib only (dataclasses).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ToolCall:
    """A single tool invocation by the agent, with its result."""
    name: str
    tool_use_id: str
    input: dict
    result_chars: int = 0
    is_error: bool = False
    timestamp: Optional[datetime] = None

    @property
    def command(self) -> str:
        return str(self.input.get("command", ""))

    @property
    def file_path(self) -> str:
        return str(self.input.get("file_path", ""))

    @property
    def result_tokens(self) -> int:
        return self.result_chars // 4  # rough estimate


@dataclass
class Turn:
    """One assistant turn: model, billed usage, and the tool calls it made."""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    timestamp: Optional[datetime] = None
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def total_input(self) -> int:
        return self.input_tokens + self.cache_read_tokens + self.cache_creation_tokens


@dataclass
class Session:
    """One transcript file = one session, with its turns and derived rollups."""
    session_id: str
    project: str
    path: str
    turns: list[Turn] = field(default_factory=list)
    first_ts: Optional[datetime] = None
    last_ts: Optional[datetime] = None

    # ---- rollups (computed lazily from turns) ----
    @property
    def output_tokens(self) -> int:
        return sum(t.output_tokens for t in self.turns)

    @property
    def input_tokens(self) -> int:
        return sum(t.input_tokens for t in self.turns)

    @property
    def cache_read_tokens(self) -> int:
        return sum(t.cache_read_tokens for t in self.turns)

    @property
    def cache_creation_tokens(self) -> int:
        return sum(t.cache_creation_tokens for t in self.turns)

    @property
    def total_input(self) -> int:
        return self.input_tokens + self.cache_read_tokens + self.cache_creation_tokens

    @property
    def cache_hit_rate(self) -> float:
        ti = self.total_input
        return self.cache_read_tokens / ti if ti else 0.0

    @property
    def tool_calls(self) -> list[ToolCall]:
        return [tc for t in self.turns for tc in t.tool_calls]

    @property
    def models(self) -> set[str]:
        return {t.model for t in self.turns if t.model}

    def cost(self, rates: "Rates") -> float:
        return sum(rates.turn_cost(t) for t in self.turns)


@dataclass
class Rates:
    """Per-million-token prices. Defaults are illustrative; set yours.

    Cache read is typically ~0.1x base input; cache write ~1.25x base input.
    """
    input_per_m: float = 0.0
    output_per_m: float = 0.0
    cache_read_per_m: float = 0.0
    cache_write_per_m: float = 0.0

    def turn_cost(self, t: Turn) -> float:
        return (
            t.input_tokens * self.input_per_m
            + t.output_tokens * self.output_per_m
            + t.cache_read_tokens * self.cache_read_per_m
            + t.cache_creation_tokens * self.cache_write_per_m
        ) / 1_000_000
