# Show HN package — Operator

Post at news.ycombinator.com/submit, weekday 8-10am ET. Reply to every comment in
the first 2 hours (drives ranking). Don't ask for upvotes.

## Title
Show HN: Operator – see where your AI coding agent's tokens and actions went

## URL
https://github.com/Ludoonus/operator

## First comment (post immediately after submitting, as the maker)
I run Claude Code heavily and realized I had no idea what it was actually doing —
what it cost, what commands it ran across projects, whether my guardrails held, or
where tokens leaked. The data is all sitting in the transcripts it writes to
~/.claude/projects/, but nothing reads it.

Operator is a local, read-only console over those transcripts. One command gives you:
- cost (tokens + est. dollars, per project/model/tool, cache hit rate)
- audit (every command run, file written, sensitive-path access)
- safety (the dangerous actions the agent *attempted* — force-pushes, rm -rf on
  risky paths, curl|sh)
- efficiency (re-read waste + the exact CLAUDE.md fixes)

On my own 30 days it found ~$25k of list-price token usage, 30 risky actions
attempted, and 2.3M tokens wasted re-reading the same files. Stdlib only, nothing
leaves your machine, no telemetry. The interactive TUI is a paid tier; the report
CLI is free/MIT.

Happy to answer questions about transcript parsing or what agents actually do at scale.
