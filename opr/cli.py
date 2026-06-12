"""operator — operations console for AI coding agents (CLI / free tier).

`operator report` prints a unified cost + audit + safety + efficiency summary across
all your Claude Code projects. The full interactive TUI console is the Pro tier.

  python3 -m opr.cli report
  python3 -m opr.cli report --days 7 --project myrepo
  python3 -m opr.cli report --json

Read-only. Nothing leaves your machine.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta

from .card import render_svg, render_text
from .engine.audit import analyze_audit
from .engine.cost import analyze_cost, blended_dollars, by_day
from .engine.efficiency import analyze_efficiency
from .engine.safety import analyze_safety
from .engine.transcripts import load_sessions, now_utc


def cmd_report(args) -> int:
    since = now_utc() - timedelta(days=args.days)
    sessions = load_sessions(project_filter=args.project, since=since)
    if not sessions:
        print("no sessions found in window", file=sys.stderr)
        return 1

    cost = analyze_cost(sessions)
    audit = analyze_audit(sessions)
    safety = analyze_safety(sessions)
    eff = analyze_efficiency(sessions)
    dollars = blended_dollars(sessions)

    if args.json:
        out = {
            "window_days": args.days,
            "sessions": cost.sessions,
            "turns": cost.turns,
            "tokens": {
                "output": cost.output_tokens,
                "input_uncached": cost.input_tokens,
                "cache_read": cost.cache_read_tokens,
                "cache_write": cost.cache_creation_tokens,
                "cache_hit_rate": round(cost.cache_hit_rate, 4),
            },
            "est_list_price_usd": round(dollars, 2) if dollars else None,
            "audit": {
                "commands": len(audit.commands),
                "writes": len(audit.writes),
                "errors": len(audit.errors),
                "sensitive_access": len(audit.sensitive_access),
            },
            "safety": {
                "risky_attempts": len(safety.hits),
                "critical": safety.critical,
                "by_label": dict(safety.by_label),
            },
            "efficiency": {
                "reread_waste_tokens": eff.reread_waste_tokens,
                "recommendations": [
                    {"severity": r.severity, "title": r.title, "detail": r.detail}
                    for r in eff.recommendations
                ],
            },
        }
        print(json.dumps(out, indent=2))
        return 0

    _print_human(args, sessions, cost, audit, safety, eff, dollars)
    return 0


def _bar(label, value, width=24):
    return f"  {label:<22} {value:>14,}"


def _print_human(args, sessions, cost, audit, safety, eff, dollars):
    print(f"\n  OPERATOR — last {args.days} days — {cost.sessions} sessions, {cost.turns} turns\n")
    print("  ── COST " + "─" * 40)
    print(_bar("output tokens", cost.output_tokens))
    print(_bar("input (uncached)", cost.input_tokens))
    print(_bar("input (cache read)", cost.cache_read_tokens))
    print(_bar("input (cache write)", cost.cache_creation_tokens))
    print(f"  {'cache hit rate':<22} {cost.cache_hit_rate*100:>13.1f}%")
    if dollars:
        print(f"  {'est. list-price cost':<22} {'$'+format(dollars, ',.0f'):>14}")
    print("\n  top projects (by output tokens):")
    for proj, tok in cost.by_project.most_common(5):
        print(f"    {tok:>12,}  {proj[:48]}")

    if getattr(args, "by_day", False):
        days = by_day(sessions)[-14:]  # last 14 active days
        if days:
            peak = max(d[1] for d in days) or 1
            print("\n  ── COST BY DAY (output tokens, last 14 active days) " + "─" * 5)
            for date, tok, dol in days:
                bar = "█" * max(1, round(28 * tok / peak))
                amt = f" ${dol:,.0f}" if dol else ""
                print(f"  {date}  {bar} {tok:,}{amt}")

    print("\n  ── AUDIT " + "─" * 39)
    print(f"  {len(audit.commands):,} commands · {len(audit.writes):,} file writes · "
          f"{len(audit.errors):,} errors · {len(audit.sensitive_access)} sensitive-path touches")
    if audit.command_verbs:
        verbs = ", ".join(f"{v}({n})" for v, n in audit.command_verbs.most_common(6))
        print(f"  top commands: {verbs}")

    print("\n  ── SAFETY " + "─" * 38)
    if safety.hits:
        print(f"  {len(safety.hits)} risky actions attempted ({safety.critical} critical):")
        for label, n in safety.by_label.most_common():
            print(f"    {n:>4}  {label}")
    else:
        print("  no risky actions detected")

    print("\n  ── EFFICIENCY " + "─" * 34)
    for r in eff.recommendations:
        tag = {"high": "!!", "medium": "! ", "low": "  "}.get(r.severity, "  ")
        print(f"  {tag} {r.title}")
        print(f"       {r.detail}")
    print()


def cmd_card(args) -> int:
    since = now_utc() - timedelta(days=args.days)
    sessions = load_sessions(project_filter=args.project, since=since)
    if not sessions:
        print("no sessions found in window", file=sys.stderr)
        return 1
    if args.svg:
        with open(args.svg, "w") as f:
            f.write(render_svg(sessions, args.days))
        print(f"wrote {args.svg}")
    else:
        print(render_text(sessions, args.days))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="operator", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    rep = sub.add_parser("report", help="unified ops report across all projects")
    rep.add_argument("--days", type=int, default=30)
    rep.add_argument("--project", help="filter by project dir substring")
    rep.add_argument("--json", action="store_true")
    rep.add_argument("--by-day", action="store_true", help="show a per-day cost breakdown")
    rep.set_defaults(func=cmd_report)
    card = sub.add_parser("card", help="a clean, shareable summary card (text or --svg)")
    card.add_argument("--days", type=int, default=30)
    card.add_argument("--project")
    card.add_argument("--svg", help="write an SVG to this path instead of text")
    card.set_defaults(func=cmd_card)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
