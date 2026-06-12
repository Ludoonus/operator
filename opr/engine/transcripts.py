"""Discover and parse Claude Code transcripts into the unified model.

Reads JSONL files under ~/.claude/projects/. Stdlib only. Read-only — never writes
or transmits anything.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from .model import Session, ToolCall, Turn


def default_root() -> Path:
    return Path.home() / ".claude" / "projects"


def _parse_ts(entry: dict) -> Optional[datetime]:
    ts = entry.get("timestamp") or (entry.get("snapshot") or {}).get("timestamp")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _iter_json(path: Path) -> Iterator[dict]:
    with open(path, errors="replace") as f:
        for line in f:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def parse_session(path: Path, project: str) -> Session:
    """Parse one transcript JSONL into a Session with turns and tool calls."""
    session = Session(session_id=path.stem, project=project, path=str(path))
    pending: dict[str, ToolCall] = {}

    for entry in _iter_json(path):
        ts = _parse_ts(entry)
        if ts:
            session.first_ts = min(session.first_ts, ts) if session.first_ts else ts
            session.last_ts = max(session.last_ts, ts) if session.last_ts else ts

        etype = entry.get("type")
        msg = entry.get("message")
        if not isinstance(msg, dict):
            continue

        if etype == "assistant":
            usage = msg.get("usage") or {}
            if not usage and not (msg.get("content")):
                continue
            turn = Turn(
                model=msg.get("model", ""),
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                cache_read_tokens=usage.get("cache_read_input_tokens", 0),
                cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),
                timestamp=ts,
            )
            for c in msg.get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    tc = ToolCall(
                        name=c.get("name", "?"),
                        tool_use_id=c.get("id", ""),
                        input=c.get("input") or {},
                        timestamp=ts,
                    )
                    turn.tool_calls.append(tc)
                    pending[tc.tool_use_id] = tc
            # only keep turns that carry usage or tool calls (skip noise)
            if usage or turn.tool_calls:
                session.turns.append(turn)

        elif etype == "user":
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for c in content:
                if isinstance(c, dict) and c.get("type") == "tool_result":
                    tc = pending.get(c.get("tool_use_id"))
                    if tc is None:
                        continue
                    body = c.get("content")
                    tc.result_chars = len(json.dumps(body, default=str)) if body else 0
                    tc.is_error = bool(c.get("is_error"))

    return session


def load_sessions(
    root: Optional[Path] = None,
    project_filter: Optional[str] = None,
    since: Optional[datetime] = None,
) -> list[Session]:
    """Load all sessions, optionally filtered by project substring and recency."""
    root = root or default_root()
    if not root.is_dir():
        return []
    sessions: list[Session] = []
    for proj_dir in sorted(root.iterdir()):
        if not proj_dir.is_dir():
            continue
        if project_filter and project_filter not in proj_dir.name:
            continue
        for jl in proj_dir.glob("*.jsonl"):
            session = parse_session(jl, proj_dir.name)
            if not session.turns:
                continue
            if since and session.last_ts and session.last_ts < since:
                continue
            sessions.append(session)
    return sessions


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
