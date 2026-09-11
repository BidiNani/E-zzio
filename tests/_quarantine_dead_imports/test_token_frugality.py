"""Frugalité : squelettes AST + schémas stricts."""
from core.agents.schemas import ADRRecord, AgentContribution
from core.agents.token_frugality import (
    enforce_unified_diff,
    prune_deliberation_context,
    skeletonize_code,
)


def test_skeleton_keeps_signatures_and_cuts_half():
    body = (
        "import os\n\n\n"
        "def alpha(a: int, b: str = 'x') -> int:\n"
        '    """Fait alpha."""\n'
        + "    x = compute(a) + len(b)\n    total = 0\n" * 30
        + "    return a\n\n\n"
        "class Beta:\n"
        '    """Conteneur."""\n'
        "    def run(self, n):\n"
        + "        y = [i * 2 for i in range(n)]\n        s = sum(y)\n" * 15
        + "        return y\n"
    )
    sk = skeletonize_code(body)
    assert "def alpha(a: int, b: str" in sk
    assert "Fait alpha." in sk
    assert "class Beta" in sk
    assert "def run(self, n)" in sk
    assert len(sk) <= len(body) * 0.5


def test_skeleton_invalid_python_fallback():
    sk = skeletonize_code("def broken(:\npass\n")
    assert isinstance(sk, str)


def test_prune_keeps_initial_skeleton_last_diff():
    h = [
        {"kind": "brief", "t": "goal"},
        {"kind": "skeleton", "t": "s1"},
        {"kind": "skeleton", "t": "s2"},
        {"kind": "diff", "t": "d1"},
        {"kind": "diff", "t": "d2"},
    ]
    out = prune_deliberation_context(h)
    assert [x["t"] for x in out] == ["goal", "s2", "d2"]
    assert prune_deliberation_context([]) == []


def test_unified_diff_gate():
    assert enforce_unified_diff("@@ -1,2 +1,2 @@\n-a\n+b")["is_unified_diff"] is True
    assert enforce_unified_diff("def f():\n    pass")["is_unified_diff"] is False


def test_contribution_rejects_garbage():
    ok = AgentContribution(agent_id="c", phase="PROPOSAL", confidence=0.8,
                           summary="s")
    assert ok.phase == "PROPOSAL"
    for bad in ({"agent_id": "c", "phase": "NOPE", "confidence": 0.5, "summary": "s"},
                {"agent_id": "c", "phase": "PROPOSAL", "confidence": 9.0, "summary": "s"},
                {"agent_id": "c", "phase": "PROPOSAL", "confidence": 0.5,
                 "summary": "s", "zzz": 1}):
        try:
            AgentContribution(**bad)
        except Exception:
            continue
        raise AssertionError(f"payload accepté à tort : {bad}")


def test_adr_defaults():
    a = ADRRecord(adr_id="ADR-9", title="t", decision="d", rationale="r")
    assert a.status == "PROPOSED" and a.decided_by == "ezzio-master"
