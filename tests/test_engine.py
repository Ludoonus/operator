"""Tests for the Operator engine. Run: python3 -m pytest tests/ (or python3 tests/test_engine.py)

Uses a synthetic transcript so tests don't depend on real session data.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from opr.engine.transcripts import parse_session, load_sessions  # noqa: E402
from opr.engine.cost import analyze_cost  # noqa: E402
from opr.engine.audit import analyze_audit  # noqa: E402
from opr.engine.safety import analyze_safety  # noqa: E402
from opr.engine.efficiency import analyze_efficiency  # noqa: E402


def _write_transcript(path: Path):
    rows = [
        {"type": "assistant", "message": {"model": "claude-opus-4-8", "usage": {
            "input_tokens": 10, "output_tokens": 100,
            "cache_read_input_tokens": 900, "cache_creation_input_tokens": 50},
            "content": [
                {"type": "tool_use", "id": "t1", "name": "Bash",
                 "input": {"command": "git push --force origin main"}},
                {"type": "tool_use", "id": "t2", "name": "Read",
                 "input": {"file_path": "/repo/big.py"}},
            ]}, "timestamp": "2026-06-12T10:00:00Z"},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": "blocked"},
            {"type": "tool_result", "tool_use_id": "t2", "content": "x" * 8000},
        ]}},
        {"type": "assistant", "message": {"model": "claude-opus-4-8", "usage": {
            "input_tokens": 5, "output_tokens": 50,
            "cache_read_input_tokens": 950, "cache_creation_input_tokens": 0},
            "content": [
                {"type": "tool_use", "id": "t3", "name": "Read",
                 "input": {"file_path": "/repo/big.py"}},  # re-read
                {"type": "tool_use", "id": "t4", "name": "Write",
                 "input": {"file_path": "/repo/.env"}},     # sensitive write
            ]}, "timestamp": "2026-06-12T10:01:00Z"},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t3", "content": "x" * 8000},
            {"type": "tool_result", "tool_use_id": "t4", "content": "ok"},
        ]}},
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows))


def run():
    tmp = Path(tempfile.mkdtemp())
    proj = tmp / "-myproj"
    proj.mkdir()
    _write_transcript(proj / "sess1.jsonl")

    sessions = load_sessions(root=tmp)
    assert len(sessions) == 1, f"expected 1 session, got {len(sessions)}"
    s = sessions[0]
    assert len(s.turns) == 2
    assert s.output_tokens == 150
    assert abs(s.cache_hit_rate - (1850 / (15 + 1850 + 50))) < 1e-6

    cost = analyze_cost(sessions)
    assert cost.turns == 2
    assert cost.by_tool_calls["Read"] == 2

    audit = analyze_audit(sessions)
    assert len(audit.commands) == 1
    assert any(".env" in e.detail for e in audit.sensitive_access), "should flag .env write"

    safety = analyze_safety(sessions)
    labels = {h.label for h in safety.hits}
    assert "force-push to protected branch" in labels, f"got {labels}"

    eff = analyze_efficiency(sessions)
    assert eff.reread_waste_tokens > 0, "should detect the re-read of big.py"
    assert eff.reread_files, "should name the re-read file"

    print("all engine tests passed")


if __name__ == "__main__":
    run()
