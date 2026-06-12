"""Safety analytics — dangerous actions the agent attempted.

Scans the command stream for the high-blast-radius patterns from the guardrail
hooks, so an operator can see what risky things their agents tried (whether or not
a gate stopped them). Stdlib only, read-only.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from .model import Session

# (label, severity, compiled pattern). Severity: "critical" | "high" | "medium".
PATTERNS = [
    ("recursive force-delete on risky path", "critical",
     re.compile(r"rm\s+(-[a-z]*f[a-z]*r|-[a-z]*r[a-z]*f)\b[^|;&]*?(\"?\$|/\s|/\*|~|\.\.)")),
    ("force-push to protected branch", "high",
     re.compile(r"git\s+push\s+[^|;&]*(--force|-f)\b[^|;&]*\b(main|master|develop|release)\b")),
    ("hard reset to remote ref", "high",
     re.compile(r"git\s+reset\s+--hard\s+(origin|upstream)/")),
    ("chmod 777", "medium", re.compile(r"chmod\s+(-R\s+)?777")),
    ("pipe remote script to shell", "critical",
     re.compile(r"(curl|wget)[^|;&]*\|\s*(sudo\s+)?(ba)?sh")),
    ("dd to device", "critical", re.compile(r"\bdd\b[^|;&]*\bof=/dev/")),
    ("git add -A / add .", "medium", re.compile(r"git\s+add\s+(-A|--all|\.)(\s|$)")),
    ("credential-shaped string in command", "high",
     re.compile(r"(AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{20,})")),
]

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2}


@dataclass
class SafetyHit:
    session_id: str
    project: str
    label: str
    severity: str
    command: str
    timestamp: object = None


@dataclass
class SafetyReport:
    hits: list[SafetyHit] = field(default_factory=list)
    by_label: Counter = field(default_factory=Counter)
    by_severity: Counter = field(default_factory=Counter)

    @property
    def critical(self) -> int:
        return self.by_severity.get("critical", 0)

    def sorted_hits(self) -> list[SafetyHit]:
        return sorted(self.hits, key=lambda h: SEVERITY_ORDER.get(h.severity, 9))


def analyze_safety(sessions: list[Session]) -> SafetyReport:
    rep = SafetyReport()
    for s in sessions:
        for tc in s.tool_calls:
            if tc.name != "Bash":
                continue
            cmd = tc.command
            if not cmd:
                continue
            for label, severity, pat in PATTERNS:
                if pat.search(cmd):
                    rep.hits.append(SafetyHit(
                        session_id=s.session_id, project=s.project,
                        label=label, severity=severity, command=cmd[:200],
                        timestamp=tc.timestamp,
                    ))
                    rep.by_label[label] += 1
                    rep.by_severity[severity] += 1
    return rep
