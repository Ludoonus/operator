"""Operator Pro — interactive terminal console.

A curses TUI over the engine: overview, cost, safety log, efficiency, and a
scrollable session list with per-session command-timeline drill-down. Stdlib only
(curses), read-only, no network. Run: python3 -m opr.tui.app

This is the Pro tier. The free tier is `operator report` (opr.cli).
"""
from __future__ import annotations

import curses
from datetime import timedelta

from ..engine.audit import analyze_audit
from ..engine.cost import analyze_cost, blended_dollars
from ..engine.efficiency import analyze_efficiency
from ..engine.safety import analyze_safety
from ..engine.transcripts import load_sessions, now_utc

VIEWS = ["Overview", "Cost", "Safety", "Efficiency", "Sessions"]


class Console:
    def __init__(self, sessions):
        self.sessions = sorted(sessions, key=lambda s: s.last_ts or now_utc(), reverse=True)
        self.cost = analyze_cost(sessions)
        self.audit = analyze_audit(sessions)
        self.safety = analyze_safety(sessions)
        self.eff = analyze_efficiency(sessions)
        self.dollars = blended_dollars(sessions)
        self.view = 0
        self.scroll = 0
        self.sel = 0
        self.drill = None  # a Session when drilled in

    # ---------- rendering ----------
    def render(self, scr):
        scr.erase()
        h, w = scr.getmaxyx()
        self._header(scr, w)
        body = self._lines(h, w)
        view_h = h - 4
        self.scroll = max(0, min(self.scroll, max(0, len(body) - view_h)))
        for i, (text, attr) in enumerate(body[self.scroll:self.scroll + view_h]):
            try:
                scr.addnstr(2 + i, 2, text, w - 4, attr)
            except curses.error:
                pass
        self._footer(scr, h, w)
        scr.refresh()

    def _header(self, scr, w):
        if self.drill:
            title = f" OPERATOR — session {self.drill.session_id[:8]} — {self.drill.project[:40]}"
        else:
            tabs = "  ".join(
                f"[{i+1}]{v}" for i, v in enumerate(VIEWS)
            )
            title = f" OPERATOR Pro    {tabs}"
        scr.addnstr(0, 0, title.ljust(w), w, curses.A_REVERSE)

    def _footer(self, scr, h, w):
        if self.drill:
            msg = " ↑/↓ scroll · [esc] back to sessions · [q] quit "
        elif self.view == 4:
            msg = " ↑/↓ select · [enter] drill in · [1-5] views · [q] quit "
        else:
            msg = " ↑/↓ scroll · [1-5] switch view · [q] quit "
        try:
            scr.addnstr(h - 1, 0, msg.ljust(w), w, curses.A_REVERSE)
        except curses.error:
            pass

    def _lines(self, h, w):
        if self.drill:
            return self._drill_lines()
        return [self._overview, self._cost, self._safety, self._efficiency, self._sessions][self.view]()

    def _row(self, label, value):
        return (f"  {label:<26}{value:>16}", curses.A_NORMAL)

    def _overview(self):
        c, a, s, e = self.cost, self.audit, self.safety, self.eff
        L = [(f"  {c.sessions} sessions · {c.turns:,} turns", curses.A_BOLD), ("", 0)]
        L.append(self._row("output tokens", f"{c.output_tokens:,}"))
        L.append(self._row("input (cache read)", f"{c.cache_read_tokens:,}"))
        L.append(self._row("cache hit rate", f"{c.cache_hit_rate*100:.1f}%"))
        if self.dollars:
            L.append(self._row("est. list-price cost", f"${self.dollars:,.0f}"))
        L += [("", 0), (f"  AUDIT  {len(a.commands):,} commands · {len(a.writes):,} writes · "
                        f"{len(a.errors):,} errors", curses.A_NORMAL)]
        sev = curses.A_BOLD if s.critical else curses.A_NORMAL
        L.append((f"  SAFETY  {len(s.hits)} risky actions attempted ({s.critical} critical)", sev))
        top = e.recommendations[0] if e.recommendations else None
        if top:
            L.append((f"  EFFICIENCY  {top.title}", curses.A_NORMAL))
        return L

    def _cost(self):
        c = self.cost
        L = [("  COST BREAKDOWN", curses.A_BOLD), ("", 0)]
        L.append(self._row("output tokens", f"{c.output_tokens:,}"))
        L.append(self._row("input (uncached)", f"{c.input_tokens:,}"))
        L.append(self._row("input (cache read)", f"{c.cache_read_tokens:,}"))
        L.append(self._row("input (cache write)", f"{c.cache_creation_tokens:,}"))
        L.append(self._row("cache hit rate", f"{c.cache_hit_rate*100:.1f}%"))
        if self.dollars:
            L.append(self._row("est. list-price cost", f"${self.dollars:,.0f}"))
        L += [("", 0), ("  By project (output tokens):", curses.A_BOLD)]
        for proj, tok in c.by_project.most_common(12):
            L.append((f"    {tok:>13,}  {proj[:46]}", curses.A_NORMAL))
        L += [("", 0), ("  By tool (result tokens):", curses.A_BOLD)]
        for name, tok in c.by_tool_result.most_common(10):
            L.append((f"    {tok:>13,}  {name}  ({c.by_tool_calls[name]} calls)", curses.A_NORMAL))
        return L

    def _safety(self):
        s = self.safety
        L = [(f"  SAFETY — {len(s.hits)} risky actions ({s.critical} critical)", curses.A_BOLD), ("", 0)]
        for label, n in s.by_label.most_common():
            L.append((f"    {n:>4}  {label}", curses.A_NORMAL))
        L += [("", 0), ("  Recent attempts:", curses.A_BOLD)]
        for h in s.sorted_hits()[:40]:
            mark = "!!" if h.severity == "critical" else ("! " if h.severity == "high" else "  ")
            L.append((f"  {mark} [{h.project[:18]}] {h.command[:70]}", curses.A_NORMAL))
        return L

    def _efficiency(self):
        e = self.eff
        L = [("  EFFICIENCY", curses.A_BOLD), ("", 0)]
        for r in e.recommendations:
            mark = {"high": "!!", "medium": "! ", "low": "  "}.get(r.severity, "  ")
            L.append((f"  {mark} {r.title}", curses.A_BOLD))
            for chunk in _wrap(r.detail, 80):
                L.append((f"       {chunk}", curses.A_NORMAL))
        if e.reread_files:
            L += [("", 0), ("  Most re-read files:", curses.A_BOLD)]
            for fp, n in e.reread_files.most_common(12):
                L.append((f"    {n:>3}x  {fp[-58:]}", curses.A_NORMAL))
        return L

    def _sessions(self):
        L = []
        for i, s in enumerate(self.sessions):
            attr = curses.A_REVERSE if i == self.sel else curses.A_NORMAL
            when = s.last_ts.strftime("%m-%d %H:%M") if s.last_ts else "  ?  "
            L.append((f"  {when}  {len(s.turns):>4} turns  {len(s.tool_calls):>4} tools  "
                      f"{s.project[:40]}", attr))
        return L or [("  no sessions", curses.A_NORMAL)]

    def _drill_lines(self):
        s = self.drill
        L = [(f"  {len(s.turns)} turns · {len(s.tool_calls)} tool calls · "
              f"cache {s.cache_hit_rate*100:.0f}%", curses.A_BOLD), ("", 0),
             ("  Command / action timeline:", curses.A_BOLD)]
        for tc in s.tool_calls:
            if tc.name == "Bash" and tc.command:
                detail = tc.command[:74]
            elif tc.file_path:
                detail = f"{tc.name}: {tc.file_path[-66:]}"
            else:
                detail = tc.name
            mark = "✗" if tc.is_error else " "
            L.append((f"  {mark} {detail}", curses.A_NORMAL))
        return L

    # ---------- input ----------
    def handle(self, key):
        if key in (ord("q"), 27) and self.drill:
            self.drill = None
            self.scroll = 0
            return True
        if key == ord("q"):
            return False
        if self.drill:
            if key in (curses.KEY_DOWN, ord("j")):
                self.scroll += 1
            elif key in (curses.KEY_UP, ord("k")):
                self.scroll = max(0, self.scroll - 1)
            return True
        if ord("1") <= key <= ord("5"):
            self.view = key - ord("1")
            self.scroll = 0
            return True
        if self.view == 4:  # sessions
            if key in (curses.KEY_DOWN, ord("j")):
                self.sel = min(len(self.sessions) - 1, self.sel + 1)
                self.scroll = max(self.scroll, self.sel - 10)
            elif key in (curses.KEY_UP, ord("k")):
                self.sel = max(0, self.sel - 1)
                self.scroll = min(self.scroll, self.sel)
            elif key in (curses.KEY_ENTER, 10, 13) and self.sessions:
                self.drill = self.sessions[self.sel]
                self.scroll = 0
        else:
            if key in (curses.KEY_DOWN, ord("j")):
                self.scroll += 1
            elif key in (curses.KEY_UP, ord("k")):
                self.scroll = max(0, self.scroll - 1)
        return True


def _wrap(text, width):
    words, line, out = text.split(), "", []
    for word in words:
        if len(line) + len(word) + 1 > width:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        out.append(line)
    return out


def _loop(scr, console):
    curses.curs_set(0)
    scr.keypad(True)
    while True:
        console.render(scr)
        key = scr.getch()
        if not console.handle(key):
            break


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="operator-console")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--project")
    args = ap.parse_args(argv)
    sessions = load_sessions(project_filter=args.project, since=now_utc() - timedelta(days=args.days))
    if not sessions:
        print("no sessions found in window")
        return 1
    curses.wrapper(_loop, Console(sessions))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
