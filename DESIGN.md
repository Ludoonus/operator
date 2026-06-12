# Operator — the operations console for AI coding agents

**The flagship.** A local, terminal-based operations console that gives anyone
running Claude Code real visibility and control over their agent fleet. The software
embodiment of *The Claude Code Operator's Handbook*.

## The need (proven, not guessed)
This machine alone: ~29,000 assistant turns, ~10B input tokens, 43 sessions, 5
models, across multiple projects in 30 days. The operator has ZERO unified view of:
- What did each session actually do? (audit / trust / security)
- Where is the money going? (cost per project/session/tool/file)
- Did the guardrails hold? What dangerous actions were attempted?
- Where is token waste? What CLAUDE.md fixes would help?
- Across ALL projects at once, not one transcript at a time.

No tool does this. Existing things are single-purpose (a cost counter, a log viewer).
Operator unifies observability + safety + efficiency into one console. That's the
standout: it's "mission control," not another dinky script.

## Why it stands out
- **Category-defining name + framing.** Pairs with the handbook ("Operator's
  Handbook" + "Operator console"). Coherent brand nobody else has.
- **Breadth no competitor matches.** Cost AND audit AND safety AND efficiency, unified.
- **Zero infra / zero ports / fully local.** Reads transcripts that already exist.
  No telemetry, no server, no signup. (Honors the no-exposed-ports rule absolutely —
  it's a terminal UI, nothing binds a socket.)
- **Real engineering, not markdown.** A proper data engine + TUI. Substantial.

## Architecture
```
operator/
  engine/            # the hard, valuable core (stdlib only)
    transcripts.py   # discover + parse all ~/.claude/projects transcripts
    model.py         # unified data model: Session, Turn, ToolCall, FileTouch
    cost.py          # token + cost analytics (per project/session/tool/file)
    audit.py         # action timeline, command stream, sensitive-path access
    safety.py        # detect dangerous actions attempted, guardrail hits
    efficiency.py    # re-read waste, cache hit rate, CLAUDE.md suggestions
  tui/               # curses-based console (stdlib curses = no deps, no ports)
    app.py           # dashboard, drill-downs, keyboard nav
  cli.py             # non-interactive reports (operator report --json) for CI
  tests/
```

## Product model
- **Free / open core:** the engine + `operator report` CLI (cost + basic audit).
  Open-source on GitHub — the funnel and the credibility.
- **Pro ($29/mo or $19 one-time-per-major):** the full TUI console, safety
  dashboard, efficiency recommendations, multi-project rollups, export. Sold on
  Gumroad. Bundles into the "everything" tier with handbook + powerpack.
- This is a higher-value product than $19/mo Powerpack — it's a daily-driver console
  for people spending real money on agents. Justifies $29/mo.

## Build plan (multi-session, this IS the large project)
1. engine/transcripts.py + model.py — discovery + parsing + unified model [DONE,
   TESTED: parses 43 sessions / 12,256 tool calls on this machine, cost+cache rollups
   work. Package is `opr` not `operator` (stdlib collision). sys.path or install to use.]
2. engine/cost.py — analytics [NEXT]
3. engine/audit.py — action timeline + command stream
4. engine/safety.py — dangerous-action detection
5. engine/efficiency.py — waste + CLAUDE.md suggestions
6. cli.py — `operator report` (free tier)
7. tui/app.py — the curses console (Pro tier)
8. tests throughout; ship free tier to GitHub; Gumroad Pro listing.

## Honest note
Bigger build, bigger payoff, same distribution truth: needs eyeballs. But a
category-defining tool is exactly what earns a Show HN front page and organic
GitHub stars — the kind of thing that breaks the traffic ceiling if anything does.
This is the swing worth taking.
