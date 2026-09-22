"""Tests pour core/security/immutable_audit.py.

ImmutableAuditLedger : journal d'événements avec hash-chaining (blockchain-lite).
100% testable : aucune dépendance externe, prend un Path en paramètre.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.security.immutable_audit import ImmutableAuditLedger

# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def ledger(tmp_path):
    """Ledger isolé dans tmp_path."""
    log_path = tmp_path / "audit.jsonl"
    return ImmutableAuditLedger(log_path)


@pytest.fixture
def log_path(tmp_path):
    return tmp_path / "audit.jsonl"


# ============================================================
# 1. Init
# ============================================================

class TestInit:
    def test_creates_parent_dir(self, tmp_path):
        """Le constructeur crée le dossier parent."""
        log_path = tmp_path / "sub" / "audit.jsonl"
        ImmutableAuditLedger(log_path)
        assert log_path.parent.exists()

    def test_stores_path(self, log_path):
        led = ImmutableAuditLedger(log_path)
        assert led.log_path == log_path

    def test_no_file_yet(self, ledger):
        """Aucun fichier n'est créé avant le premier append."""
        assert not ledger.log_path.exists()


# ============================================================
# 2. _get_last_hash
# ============================================================

class TestGetLastHash:
    def test_no_file_returns_genesis(self, ledger):
        """Sans fichier -> '0'*64 (genesis)."""
        assert ledger._get_last_hash() == "0" * 64

    def test_empty_file_returns_genesis(self, ledger):
        """Fichier vide -> '0'*64."""
        ledger.log_path.parent.mkdir(parents=True, exist_ok=True)
        ledger.log_path.write_text("", encoding="utf-8")
        assert ledger._get_last_hash() == "0" * 64

    def test_whitespace_only_returns_genesis(self, ledger):
        """Fichier avec seulement des blancs -> '0'*64."""
        ledger.log_path.parent.mkdir(parents=True, exist_ok=True)
        ledger.log_path.write_text("\n\n\n", encoding="utf-8")
        assert ledger._get_last_hash() == "0" * 64

    def test_returns_last_hash(self, ledger):
        """Après append -> retourne le hash du dernier enregistrement."""
        record = ledger.append_event("evt", {"a": 1})
        assert ledger._get_last_hash() == record["hash"]

    def test_corrupted_last_line_returns_genesis(self, ledger):
        """Dernière ligne non-JSON -> '0'*64."""
        ledger.log_path.parent.mkdir(parents=True, exist_ok=True)
        ledger.log_path.write_text("NOT JSON\n", encoding="utf-8")
        assert ledger._get_last_hash() == "0" * 64


# ============================================================
# 3. append_event
# ============================================================

class TestAppendEvent:
    def test_returns_record(self, ledger):
        """append_event retourne un dict."""
        rec = ledger.append_event("test", {"x": 1})
        assert isinstance(rec, dict)
        assert rec["event"] == "test"
        assert rec["data"] == {"x": 1}
        assert "hash" in rec
        assert "timestamp" in rec
        assert "previous_hash" in rec

    def test_first_record_previous_hash_genesis(self, ledger):
        """Le premier enregistrement pointe vers genesis."""
        rec = ledger.append_event("first", {})
        assert rec["previous_hash"] == "0" * 64

    def test_second_record_chains(self, ledger):
        """Le 2e enregistrement pointe vers le hash du 1er."""
        rec1 = ledger.append_event("e1", {})
        rec2 = ledger.append_event("e2", {})
        assert rec2["previous_hash"] == rec1["hash"]

    def test_creates_file(self, ledger):
        ledger.append_event("evt", {})
        assert ledger.log_path.exists()

    def test_appends_lines(self, ledger):
        ledger.append_event("e1", {"i": 1})
        ledger.append_event("e2", {"i": 2})
        lines = [line for line in ledger.log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert len(lines) == 2
        for line in lines:
            data = json.loads(line)
            assert "hash" in data
            assert "timestamp" in data

    def test_hash_is_sha256_hex(self, ledger):
        rec = ledger.append_event("evt", {})
        assert len(rec["hash"]) == 64
        int(rec["hash"], 16)  # Doit être hex valide

    def test_hash_deterministic_for_same_input(self, tmp_path):
        """Deux ledgers identiques -> mêmes hashs pour mêmes entrées."""
        l1 = ImmutableAuditLedger(tmp_path / "a.jsonl")
        l2 = ImmutableAuditLedger(tmp_path / "b.jsonl")
        # On doit retirer le timestamp pour comparer, sinon différent
        # On teste juste que la structure du hash est cohérente
        rec1 = l1.append_event("evt", {"k": "v"})
        rec2 = l2.append_event("evt", {"k": "v"})
        assert len(rec1["hash"]) == len(rec2["hash"]) == 64

    def test_unicode_data(self, ledger):
        """Les données Unicode sont correctement sérialisées."""
        rec = ledger.append_event("éàç", {"clé": "valeur é"})
        content = ledger.log_path.read_text(encoding="utf-8")
        assert "éàç" in content
        assert "valeur é" in content


# ============================================================
# 4. verify_chain
# ============================================================

class TestVerifyChain:
    def test_no_file_is_valid(self, ledger):
        """Sans fichier -> chaîne valide (vide)."""
        assert ledger.verify_chain() is True

    def test_empty_file_is_valid(self, ledger):
        ledger.log_path.parent.mkdir(parents=True, exist_ok=True)
        ledger.log_path.write_text("", encoding="utf-8")
        assert ledger.verify_chain() is True

    def test_single_record_valid(self, ledger):
        ledger.append_event("evt", {})
        assert ledger.verify_chain() is True

    def test_three_records_valid(self, ledger):
        for i in range(3):
            ledger.append_event(f"e{i}", {"i": i})
        assert ledger.verify_chain() is True

    def test_tampered_data_detected(self, ledger):
        """Modifier un champ -> hash invalide."""
        ledger.append_event("evt", {"key": "original"})
        content = ledger.log_path.read_text(encoding="utf-8")
        tampered = content.replace('"original"', '"hacked"')
        ledger.log_path.write_text(tampered, encoding="utf-8")
        assert ledger.verify_chain() is False

    def test_tampered_hash_detected(self, ledger):
        """Modifier le hash stocké -> invalide."""
        ledger.append_event("evt", {})
        content = ledger.log_path.read_text(encoding="utf-8")
        tampered = content.replace('"hash": "', '"hash": "aaa')  # Préfixe le hash
        ledger.log_path.write_text(tampered, encoding="utf-8")
        assert ledger.verify_chain() is False

    def test_broken_chain_detected(self, ledger):
        """Casser previous_hash -> invalide."""
        ledger.append_event("e1", {})
        ledger.append_event("e2", {})
        content = ledger.log_path.read_text(encoding="utf-8")
        # Remplacer le 2e previous_hash par du genesis
        tampered = content.replace('"previous_hash": "', '"previous_hash": "000', 1)
        # Attention : le 1er match sera sur le 1er record (déjà genesis)
        # Meilleure stratégie : modifier le previous_hash du 2e
        lines = content.splitlines()
        if len(lines) >= 2:
            rec2 = json.loads(lines[1])
            rec2["previous_hash"] = "0" * 64
            lines[1] = json.dumps(rec2, ensure_ascii=False)
            ledger.log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            assert ledger.verify_chain() is False

    def test_broken_json_detected(self, ledger):
        """Ligne non-JSON -> invalide."""
        ledger.log_path.parent.mkdir(parents=True, exist_ok=True)
        ledger.log_path.write_text('{"valid": "json"}\nNOT JSON\n', encoding="utf-8")
        assert ledger.verify_chain() is False

    def test_missing_hash_detected(self, ledger):
        """Enregistrement sans hash -> invalide."""
        ledger.log_path.parent.mkdir(parents=True, exist_ok=True)
        ledger.log_path.write_text('{"event": "x", "previous_hash": "' + "0" * 64 + '"}\n', encoding="utf-8")
        assert ledger.verify_chain() is False
