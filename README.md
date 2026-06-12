# Operator

**The operations console for AI coding agents.** Unified cost, audit, safety, and
efficiency for everyone running [Claude Code](https://claude.com/claude-code) — across
every project, from the transcripts you already have. Runs entirely locally. No
servers, no ports, no telemetry, nothing leaves your machine.

```
$ operator report

  OPERATOR — last 30 days — 43 sessions, 29,421 turns

  ── COST ────────────────────────────────────────
  output tokens              51,882,925
  input (cache read)      9,974,032,196
  cache hit rate                  96.3%
  est. list-price cost          $25,651

  ── AUDIT ───────────────────────────────────────
  6,072 commands · 2,135 file writes · 432 errors · 2 sensitive-path touches

  ── SAFETY ──────────────────────────────────────
  30 risky actions attempted (19 critical):
      13  recursive force-delete on risky path
       4  force-push to protected branch

  ── EFFICIENCY ──────────────────────────────────
  !! ~2,324,986 tokens wasted re-reading files
       Most re-read: UActorChannel.cs, UNetDriver.cs ... Add summaries to CLAUDE.md.
```

## Why this exists

If you run an AI coding agent seriously, you have no idea what it's actually costing
you, what it did across your projects, whether your guardrails held, or where your
tokens are leaking. The data is all there — Claude Code writes every session to
`~/.claude/projects/` — but nobody reads it. Operator does.

It answers, in one command, the four questions every agent operator should be asking:

- **Cost** — tokens and est. dollars, per project, model, and tool. Cache hit rate.
- **Audit** — every command run, every file written, every sensitive-path touch.
- **Safety** — the dangerous actions your agents *attempted* (force-pushes, `rm -rf`
  on risky paths, `curl | sh`), whether or not a hook stopped them.
- **Efficiency** — re-read waste, oversized output, and the exact CLAUDE.md fixes.

## Install & use

Requires Python 3.8+. No dependencies.

```bash
git clone https://github.com/Ludoonus/operator && cd operator
python3 -m opr.cli report                 # last 30 days, all projects
python3 -m opr.cli report --days 7 --project myrepo
python3 -m opr.cli report --json          # machine-readable, for CI
```

## Share your stats — `operator card`

A clean, screenshot-friendly summary of your Claude Code usage:

```bash
python3 -m opr.cli card                    # tidy terminal card
python3 -m opr.cli card --svg mycard.svg   # SVG for sharing
```

```
╭─────────────────────────────────────────────╮
│ OPERATOR · my Claude Code, last 30 days     │
├─────────────────────────────────────────────┤
│ sessions                                 43 │
│ output tokens                    52,264,441 │
│ cache hit rate                        96.4% │
│ est. list-price                     $25,908 │
├─────────────────────────────────────────────┤
│ measure yours: github.com/Ludoonus/operator │
╰─────────────────────────────────────────────╯
```

Post yours — curious what everyone's cache hit rate looks like.

## Free vs Pro

This open-source tier gives you the full **`operator report`** — the unified summary
above, plus `--json` for automation. The **Pro** tier adds the interactive **TUI
console**: live drill-down into any session's command timeline, per-file cost
attribution, the full safety log with the offending commands, multi-project rollups,
and exports. [Operator Pro →](https://ludoonus.github.io/cc-powerpack/)

## Companion projects

Operator is the console; these are the rest of the kit:
- [cc-powerpack](https://github.com/Ludoonus/cc-powerpack) — the guardrail hooks that
  *prevent* the risky actions Operator reports.
- The Claude Code Operator's Handbook — the operational practices, in depth.

## License

Engine + `operator report` CLI: MIT.

## Part of the agent-ops toolkit
- [Operator](https://github.com/Ludoonus/operator) — unified cost/audit/safety/efficiency console for Claude Code
- [cc-powerpack](https://github.com/Ludoonus/cc-powerpack) — guardrail hooks (secret scan, dangerous-command gate, worktree protection)
- [agent-ready-template](https://github.com/Ludoonus/agent-ready-template) — project skeleton with guardrails pre-wired
- [claude-token-report](https://github.com/Ludoonus/claude-token-report) — free local token-usage report
