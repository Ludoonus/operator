"""operator card — a clean, shareable summary of your Claude Code usage.

Devs screenshot terminals; this renders a tidy, screenshot-friendly card and can
also write an SVG for sharing on social. Subtle attribution drives discovery.
Stdlib only.
"""
from __future__ import annotations

from .engine.cost import analyze_cost, blended_dollars


def _fmt(n):
    return f"{n:,}"


def render_text(sessions, days):
    c = analyze_cost(sessions)
    dollars = blended_dollars(sessions)
    W = 45  # inner width

    rows = [
        ("sessions", _fmt(c.sessions)),
        ("assistant turns", _fmt(c.turns)),
        ("output tokens", _fmt(c.output_tokens)),
        ("cache hit rate", f"{c.cache_hit_rate*100:.1f}%"),
    ]
    if dollars:
        rows.append(("est. list-price", "$" + _fmt(round(dollars))))

    def row(label, val):
        gap = W - 2 - len(label) - len(val)
        return "│ " + label + " " * max(gap, 1) + val + " │"

    def line(text):
        return "│ " + text.ljust(W - 2) + " │"

    out = ["╭" + "─" * W + "╮",
           line(f"OPERATOR · my Claude Code, last {days} days"),
           "├" + "─" * W + "┤"]
    out += [row(l, v) for l, v in rows]
    out += ["├" + "─" * W + "┤",
            line("measure yours: github.com/Ludoonus/operator"),
            "╰" + "─" * W + "╯"]
    return "\n".join(out)


def render_svg(sessions, days):
    c = analyze_cost(sessions)
    dollars = blended_dollars(sessions)
    rows = [
        ("sessions", _fmt(c.sessions)),
        ("assistant turns", _fmt(c.turns)),
        ("output tokens", _fmt(c.output_tokens)),
        ("cache hit rate", f"{c.cache_hit_rate*100:.1f}%"),
    ]
    if dollars:
        rows.append(("est. list-price", "$" + _fmt(round(dollars))))
    h = 150 + len(rows) * 34
    body = []
    y = 116
    for label, val in rows:
        body.append(f'<text x="40" y="{y}" fill="#9aa7b4" font-size="17">{label}</text>')
        body.append(f'<text x="520" y="{y}" fill="#e6edf3" font-size="17" '
                    f'text-anchor="end" font-family="monospace">{val}</text>')
        y += 34
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="560" height="{h}" font-family="system-ui,sans-serif">
  <rect width="560" height="{h}" rx="14" fill="#0d1117"/>
  <rect x="0.5" y="0.5" width="559" height="{h-1}" rx="14" fill="none" stroke="#30363d"/>
  <text x="40" y="52" fill="#3fb950" font-size="22" font-weight="700">OPERATOR</text>
  <text x="40" y="76" fill="#9aa7b4" font-size="15">my Claude Code, last {days} days</text>
  <line x1="40" y1="90" x2="520" y2="90" stroke="#30363d"/>
  {''.join(body)}
  <line x1="40" y1="{h-40}" x2="520" y2="{h-40}" stroke="#30363d"/>
  <text x="40" y="{h-18}" fill="#58a6ff" font-size="14">measure yours: github.com/Ludoonus/operator</text>
</svg>'''
