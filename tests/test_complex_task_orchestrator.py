"""
E-ZZIO Autonomous Coding Agent — Complex Task Orchestrator Acceptance Suite.

Certifie les capacités de traitement de bout en bout :
1. Analyse statique d'impact et résolution des tests associés (AST & File Finder)
2. Planification DAG déterministe (RESEARCH -> PLAN -> CODE -> TEST -> REVIEW -> VERIFY)
3. Exécution d'une mission complexe complète avec génération de preuves
4. Boucle d'auto-réparation bornée sur anomalie
5. Intégration transparente avec CodingAgentHarness
"""
import json
import os

import pytest

from core.agent.coding_agent_loop import CodingAgentHarness
from core.agent.complex_task_orchestrator import CodebaseImpactAnalyzer, ComplexTaskEngine, TaskStep


def test_impact_analyzer_finds_tests_and_ast_imports(tmp_path):
    workspace = str(tmp_path)
    os.makedirs(os.path.join(workspace, "src"), exist_ok=True)
    os.makedirs(os.path.join(workspace, "tests"), exist_ok=True)

    src_file = os.path.join(workspace, "src", "analytics.py")
    with open(src_file, "w", encoding="utf-8") as f:
        f.write("import math\nfrom os import path\ndef compute(x): return math.sqrt(x)\n")

    test_file = os.path.join(workspace, "tests", "test_analytics.py")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("from src.analytics import compute\ndef test_compute(): assert compute(4) == 2\n")

    analyzer = CodebaseImpactAnalyzer(workspace_root=workspace)
    impact = analyzer.analyze_impact(["src/analytics.py"], intent="Améliorer analytics")

    assert "src/analytics.py" in impact.target_files
    assert any("test_analytics.py" in t for t in impact.related_tests)
    assert "math" in impact.imported_modules
    assert "os" in impact.imported_modules or "path" in impact.imported_modules
    assert impact.risk_level == "LOW"


def test_plan_complex_task_dag_order(tmp_path):
    engine = ComplexTaskEngine(workspace_root=str(tmp_path))
    steps = engine.plan_complex_task(
        objective="Refactorer le module de calcul et ajouter les tests",
        target_files=["core/calc.py"]
    )
    assert len(steps) == 6
    roles = [s.role for s in steps]
    assert roles == ["RESEARCH", "PLAN", "CODE", "TEST", "REVIEW", "VERIFY"]
    assert steps[0].dependencies == []
    assert steps[1].dependencies == ["step_1_impact"]
    assert steps[2].dependencies == ["step_2_plan"]


def test_end_to_end_complex_task_execution(tmp_path):
    workspace = str(tmp_path)
    os.makedirs(os.path.join(workspace, "tests"), exist_ok=True)

    # Code initial
    mod_file = os.path.join(workspace, "math_service.py")
    with open(mod_file, "w", encoding="utf-8") as f:
        f.write("def multiply(a: int, b: int) -> int:\n    return a + b\n")

    test_file = os.path.join(workspace, "tests", "test_math_service.py")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("from math_service import multiply\ndef test_multiply(): assert multiply(3, 4) == 12\n")

    engine = ComplexTaskEngine(workspace_root=workspace)
    res = engine.execute_complex_task(
        objective="Corriger l'implémentation de multiply dans math_service",
        target_files=["math_service.py"],
        patch_actions=[{
            "path": "math_service.py",
            "search": "return a + b",
            "replace": "return a * b"
        }],
        auto_repair=True
    )

    assert res["success"] is True
    assert "task_id" in res
    assert len(res["steps_completed"]) == 6
    assert os.path.exists(res["evidence"]["json"])
    assert os.path.exists(res["evidence"]["markdown"])

    # Vérification que le fichier a été corrigé
    with open(mod_file, encoding="utf-8") as f:
        corrected = f.read()
    assert "return a * b" in corrected


def test_harness_integration_run_complex_mission(tmp_path):
    workspace = str(tmp_path)
    os.makedirs(os.path.join(workspace, "tests"), exist_ok=True)

    mod_file = os.path.join(workspace, "service.py")
    with open(mod_file, "w", encoding="utf-8") as f:
        f.write("def get_version() -> str:\n    return '1.0.0'\n")

    test_file = os.path.join(workspace, "tests", "test_service.py")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("from service import get_version\ndef test_ver(): assert get_version() == '2.0.0'\n")

    harness = CodingAgentHarness(workspace_root=workspace)
    res = harness.run_complex_mission(
        objective="Mise à jour de version vers 2.0.0",
        target_files=["service.py"],
        patch_actions=[{
            "path": "service.py",
            "search": "return '1.0.0'",
            "replace": "return '2.0.0'"
        }]
    )

    assert res["success"] is True
    assert "task_id" in res
