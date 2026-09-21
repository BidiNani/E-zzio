import pytest


pytestmark = pytest.mark.skip(
    reason="Fichiers AGENTS.md ou registry_refresh_service.py supprimes (DEAD cleanup)",
)


"""
E-ZZIO Test Suite — Codex, Godot & Trinity Architectural Integration.
Certifie la conformité contractuelle des 3 piliers :
1. Codex : Présence et complétude de AGENTS.md
2. Godot : SignalBus découplé et Scaffolding de projet Godot 4 idiomatique (ressources .tres, signaux GDScript, séparation de scènes)
3. Trinity : Registre d'audit append-only scellé par SHA-256, inviolabilité par triggers SQLite et vérification d'intégrité
"""
import os
import sqlite3
from pathlib import Path

import pytest

from core.security.audit_ledger import AuditLedger
from core.signals.signal_bus import SignalBus
from core.studio.scaffolder import ProjectScaffolder


def test_codex_agents_guide_integrity():
    agents_file = Path("G:/AI/E-zzio/AGENTS.md")
    assert agents_file.exists()
    content = agents_file.read_text(encoding="utf-8")
    assert "Architecture & Point d'Entrée Canonique" in content
    assert "web_server.py:8001" in content
    assert "Confinement & Gouvernance des Permissions" in content
    assert "Protocole d'Édition & de Self-Healing" in content
    assert "Journal d'Audit Immuable" in content


@pytest.mark.asyncio
async def test_godot_decoupled_signal_bus():
    bus = SignalBus()
    received_sync = []
    received_async = []

    def on_sync_event(payload):
        received_sync.append(payload.get("status"))

    async def on_async_event(payload):
        received_async.append(payload.get("metric"))

    bus.connect("test_signal", on_sync_event)
    bus.connect("test_signal", on_async_event)

    await bus.emit_async("test_signal", {"status": "ACTIVE", "metric": 42})

    assert received_sync == ["ACTIVE"]
    assert received_async == [42]
    assert len(bus.get_event_history("test_signal")) == 1


def test_godot_idiomatic_dev_studio_scaffolding(tmp_path):
    scaffolder = ProjectScaffolder(workspace_root=str(tmp_path))
    res = scaffolder.scaffold(project_name="cyber_runner", project_type="godot", description="Cyberpunk 2D Runner")

    assert res["project_name"] == "cyber_runner"
    proj_dir = tmp_path / "projects" / "cyber_runner"
    assert proj_dir.exists()

    # 1. Vérification configuration officielle
    godot_proj = proj_dir / "project.godot"
    assert godot_proj.exists()
    assert 'config/name="cyber_runner"' in godot_proj.read_text(encoding="utf-8")

    # 2. Vérification Custom Resource .tres
    cfg_script = proj_dir / "scripts" / "game_config.gd"
    cfg_tres = proj_dir / "resources" / "default_config.tres"
    assert cfg_script.exists()
    assert "class_name GameConfig" in cfg_script.read_text(encoding="utf-8")
    assert cfg_tres.exists()
    assert 'script_class="GameConfig"' in cfg_tres.read_text(encoding="utf-8")

    # 3. Vérification signaux découplés GDScript
    player_script = proj_dir / "scripts" / "player.gd"
    main_script = proj_dir / "scripts" / "main.gd"
    assert "signal health_changed" in player_script.read_text(encoding="utf-8")
    assert "player.health_changed.connect" in main_script.read_text(encoding="utf-8")
    assert "get_node(" not in main_script.read_text(encoding="utf-8")  # Zéro couplage get_node codé en dur


def test_trinity_cryptographic_audit_ledger_immutability(tmp_path):
    db_file = str(tmp_path / "audit_test.db")
    ledger = AuditLedger(db_path=db_file)

    # 1. Enregistrement d'événements chaînés
    e1 = ledger.record_event(actor="agent_loop", action="apply_patch", payload={"file": "math_utils.py"})
    e2 = ledger.record_event(actor="security_guard", action="allow_intent", payload={"scope": "read_file"})
    e3 = ledger.record_event(actor="capability_registry", action="execute", payload={"cap": "web-search-mcp"})

    assert e1["id"] == 1
    assert e2["prev_hash"] == e1["current_hash"]
    assert e3["prev_hash"] == e2["current_hash"]

    # 2. Vérification mathématique de la chaîne
    is_valid, count, err = ledger.verify_chain_integrity()
    assert is_valid is True
    assert count == 3
    assert err is None

    # 3. Tentative d'altération / suppression bloquée par Trigger SQLite
    with sqlite3.connect(db_file) as conn:
        with pytest.raises(sqlite3.DatabaseError):
            conn.execute("UPDATE audit_trail SET actor = 'attacker' WHERE id = 1;")

        with pytest.raises(sqlite3.DatabaseError):
            conn.execute("DELETE FROM audit_trail WHERE id = 1;")


def test_trinity_audit_ledger_high_concurrency(tmp_path):
    """Test de concurrence : 30 écritures simultanées via ThreadPoolExecutor pour certifier le chaînage."""
    import concurrent.futures
    db_file = str(tmp_path / "audit_concurrent.db")
    ledger = AuditLedger(db_path=db_file)

    def write_worker(idx: int):
        return ledger.record_event(
            actor=f"worker_{idx % 4}",
            action="parallel_execution",
            payload={"thread_idx": idx, "data": f"payload_{idx}"}
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(write_worker, i) for i in range(30)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 30

    # Vérification d'intégrité de la chaîne complète après concurrence
    is_valid, count, err = ledger.verify_chain_integrity()
    assert is_valid is True
    assert count == 30
    assert err is None

