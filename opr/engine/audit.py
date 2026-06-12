"""Audit analytics — what the agent actually did.

Turns the raw tool-call stream into a security-and-trust review: the command
stream, files modified, sensitive-path access, and where sessions failed. Stdlib
only, read-only.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from .model import Session, ToolCall

SENSITIVE_PATH = re.compile(
    r"(^|/)(\.env(\..+)?|.*\.pem|.*\.p12|id_rsa|id_ed25519|credentials\.json|\.aws/|\.ssh/)",
    re.IGNORECASE,
)
WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}
READ_TOOLS = {"Read"}


@dataclass
class AuditEvent:
    session_id: str
    project: str
    kind: str          # "command" | "write" | "read" | "error"
    detail: str
    is_error: bool = False
    timestamp: object = None


@dataclass
class AuditReport:
    commands: list[AuditEvent] = field(default_factory=list)
    writes: list[AuditEvent] = field(default_factory=list)
    sensitive_access: list[AuditEvent] = field(default_factory=list)
    errors: list[AuditEvent] = field(default_factory=list)
    command_verbs: Counter = field(default_factory=Counter)   # first word of each command
    files_written: Counter = field(default_factory=Counter)   # path -> write count


def _first_verb(command: str) -> str:
    command = command.strip()
    # strip leading env assignments like FOO=bar
    parts = command.split()
    for p in parts:
        if "=" in p and not p.startswith("-"):
            continue
        return p
    return parts[0] if parts else ""


def analyze_audit(sessions: list[Session]) -> AuditReport:
    rep = AuditReport()
    for s in sessions:
        for tc in s.tool_calls:
            _classify(tc, s, rep)
    return rep


def _classify(tc: ToolCall, s: Session, rep: AuditReport) -> None:
    ev_base = dict(session_id=s.session_id, project=s.project, timestamp=tc.timestamp)

    if tc.name == "Bash" and tc.command:
        ev = AuditEvent(kind="command", detail=tc.command, is_error=tc.is_error, **ev_base)
        rep.commands.append(ev)
        rep.command_verbs[_first_verb(tc.command)] += 1
        if SENSITIVE_PATH.search(tc.command):
            rep.sensitive_access.append(
                AuditEvent(kind="command", detail=tc.command, is_error=tc.is_error, **ev_base)
            )

    elif tc.name in WRITE_TOOLS and tc.file_path:
        ev = AuditEvent(kind="write", detail=tc.file_path, is_error=tc.is_error, **ev_base)
        rep.writes.append(ev)
        rep.files_written[tc.file_path] += 1
        if SENSITIVE_PATH.search(tc.file_path):
            rep.sensitive_access.append(ev)

    elif tc.name in READ_TOOLS and tc.file_path:
        if SENSITIVE_PATH.search(tc.file_path):
            rep.sensitive_access.append(
                AuditEvent(kind="read", detail=tc.file_path, **ev_base)
            )

    if tc.is_error:
        detail = tc.command or tc.file_path or tc.name
        rep.errors.append(AuditEvent(kind="error", detail=detail, is_error=True, **ev_base))
