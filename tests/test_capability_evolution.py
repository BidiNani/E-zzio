"""Évolution des capacités : qualification externe, composition, bornes skills."""
import json

from core.capabilities.external_qualification import (
    ExternalCandidate,
    check_composition,
    qualify_external,
)
from core.capabilities.capability_qualification import QualificationStatus


def test_external_no_source_rejected():
    v = qualify_external(ExternalCandidate(name="x", source="", license="MIT"))
    assert v.status == QualificationStatus.REJECTED and v.escalation_level == 4


def test_external_bad_license_rejected():
    v = qualify_external(ExternalCandidate(name="x", source="github:o/r", license="GPL-3.0"))
    assert v.status == QualificationStatus.REJECTED
    v2 = qualify_external(ExternalCandidate(name="x", source="github:o/r", license=None))
    assert v2.status == QualificationStatus.REJECTED


def test_external_sensitive_permission_quarantined():
    v = qualify_external(ExternalCandidate(
        name="x", source="github:o/r", license="MIT",
        permissions=["read_web", "shell"], has_tests=True, sandbox_verified=True))
    assert v.status == QualificationStatus.QUARANTINED and v.escalation_level == 4


def test_external_many_dependencies_quarantined():
    v = qualify_external(ExternalCandidate(
        name="x", source="github:o/r", license="MIT",
        dependencies=[f"d{i}" for i in range(9)]))
    assert v.status == QualificationStatus.QUARANTINED


def test_external_no_sandbox_stays_candidate():
    v = qualify_external(ExternalCandidate(
        name="x", source="github:o/r", license="MIT", has_tests=True, sandbox_verified=False))
    assert v.status == QualificationStatus.CANDIDATE


def test_external_clean_qualified():
    v = qualify_external(ExternalCandidate(
        name="x", source="github:o/r", license="Apache-2.0",
        permissions=["read_web"], dependencies=["a"],
        has_tests=True, sandbox_verified=True))
    assert v.status == QualificationStatus.QUALIFIED and v.escalation_level == 2


def test_verdict_preserves_source_on_every_path():
    """Provenance (§XXV/9) : chaque verdict reste lié à son candidat,
    y compris les refus — un verdict orphelin est une dérive."""
    cases = [
        (ExternalCandidate(name="a", source="", license="MIT"),
         QualificationStatus.REJECTED),
        (ExternalCandidate(name="b", source="github:o/r", license="GPL-3.0"),
         QualificationStatus.REJECTED),
        (ExternalCandidate(name="c", source="github:o/r", license="MIT",
                           permissions=["shell"], has_tests=True, sandbox_verified=True),
         QualificationStatus.QUARANTINED),
        (ExternalCandidate(name="d", source="github:o/r", license="MIT",
                           dependencies=[f"d{i}" for i in range(9)]),
         QualificationStatus.QUARANTINED),
        (ExternalCandidate(name="e", source="github:o/r", license="MIT",
                           has_tests=True, sandbox_verified=False),
         QualificationStatus.CANDIDATE),
        (ExternalCandidate(name="f", source="github:o/r", license="MIT",
                           has_tests=True, sandbox_verified=True),
         QualificationStatus.QUALIFIED),
    ]
    for cand, expected in cases:
        v = qualify_external(cand)
        assert v.status == expected, cand.name
        assert v.source == cand.source, cand.name


def test_composition_cycle_and_depth():
    assert check_composition(["a", "b", "a"])["ok"] is False
    assert check_composition(["a", "b", "c", "d"])["ok"] is False
    ok = check_composition(["skillA", "toolB", "modelC"])
    assert ok == {"ok": True, "depth": 3}


def _make_skill(tmp_path, name, code):
    d = tmp_path / "core" / "agent" / "skills" / name
    d.mkdir(parents=True)
    (d / "manifest.json").write_text(
        json.dumps({"name": name, "implementation": "skill.py"}), encoding="utf-8")
    (d / "skill.py").write_text(code, encoding="utf-8")


def test_skill_timeout_bounded(tmp_path):
    import time
    from core.agent.tools_registry import ToolRegistry

    _make_skill(tmp_path, "slow", "import time\ndef run(args, root):\n    time.sleep(30)\n    return 'trop tard'\n")
    tr = ToolRegistry(str(tmp_path))
    tr.SKILL_TIMEOUT_SECONDS = 0.5
    t0 = time.perf_counter()
    out = tr.execute("slow", {})
    dt = time.perf_counter() - t0
    assert "interrompue" in out and dt < 15


def test_chain_depth_guard(tmp_path):
    from core.agent.tools_registry import ToolRegistry

    tr = ToolRegistry(str(tmp_path))
    tr._chain_depth = tr.MAX_CHAIN_DEPTH
    out = tr.execute("nimportequoi", {})
    assert "Profondeur" in out
    assert tr._chain_depth == tr.MAX_CHAIN_DEPTH  # compteur restauré


def test_factory_bridge_status_closed_set():
    """Pont lifecycle (§VI) : factory ne peut écrire dans le registre canonique
    que QUALIFIED/CANDIDATE/QUARANTINED — jamais ACTIVE/RETIRED/DISABLED.
    La vérité d'exécution reste QualificationStatus, pas CapabilityStatus."""
    import ast

    tree = ast.parse(open("core/capabilities/factory.py", encoding="utf-8").read())
    written = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
            if n.value.id == "QualificationStatus":
                written.add(n.attr)
    assert written, "le pont doit écrire au moins un statut"
    assert written <= {"QUALIFIED", "CANDIDATE", "QUARANTINED"}, written
