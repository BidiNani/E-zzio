"""Tests pour core/security/archive_validator.py (100% cible).

ArchiveLineageValidator : audit rétroactif de la chaîne d'archives.
Vérifie : existence, cohérence, previous_root, content_hash, root_hash.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from core.security import archive_validator as av_mod
from core.security.archive_validator import ArchiveLineageValidator

# ============================================================
# Helpers
# ============================================================

ZERO_HASH = "0" * 64


def _make_valid_archive(archive_dir: Path, idx: int, prev_root: str,
                        sequences: tuple[int, int] = (1, 3)) -> str:
    """Crée une archive cohérente (meta + jsonl). Retourne son root_hash."""
    # Lignes du jsonl
    lines = [
        json.dumps({"sequence": sequences[0], "action": "a"}),
        json.dumps({"sequence": sequences[0] + 1, "action": "b"}),
        json.dumps({"sequence": sequences[1], "action": "c"}),
    ]
    jsonl_content = "\n".join(lines) + "\n"
    jsonl_path = archive_dir / f"ledger_{idx:04d}.jsonl"
    jsonl_path.write_text(jsonl_content, encoding="utf-8")

    # content_hash = sha256(concat des lignes sans newline)
    hasher = hashlib.sha256()
    for line in lines:
        hasher.update(line.encode("utf-8"))
    content_hash = hasher.hexdigest()

    # root_hash
    root_payload = (
        f"{content_hash}:{prev_root}:{sequences[0]}:{sequences[1]}"
    ).encode()
    root_hash = hashlib.sha256(root_payload).hexdigest()

    meta = {
        "previous_archive_root_hash": prev_root,
        "content_hash": content_hash,
        "archive_root_hash": root_hash,
    }
    meta_path = archive_dir / f"ledger_{idx:04d}.meta.json"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    return root_hash


@pytest.fixture
def patched_archive_dir(tmp_path, monkeypatch):
    """Redirige ARCHIVE_DIR vers un dossier temporaire."""
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    monkeypatch.setattr(av_mod, "ARCHIVE_DIR", archive_dir)
    return archive_dir


# ============================================================
# 1. Cas sans archives
# ============================================================

class TestNoArchives:
    def test_missing_archive_dir_returns_valid(self, tmp_path, monkeypatch):
        """Dossier absent -> valid True, count 0."""
        nonexistent = tmp_path / "does_not_exist"
        monkeypatch.setattr(av_mod, "ARCHIVE_DIR", nonexistent)
        result = ArchiveLineageValidator.verify_archive_lineage()
        assert result["valid"] is True
        assert result["archives_count"] == 0
        assert result["error"] is None

    def test_empty_archive_dir_returns_valid(self, patched_archive_dir):
        """Dossier vide -> valid True, archives_verified 0."""
        result = ArchiveLineageValidator.verify_archive_lineage()
        assert result["valid"] is True
        assert result["archives_verified"] == 0
        assert result["error"] is None


# ============================================================
# 2. Cas nominal (1 archive valide)
# ============================================================

class TestSingleValidArchive:
    def test_one_valid_archive_passes(self, patched_archive_dir):
        _make_valid_archive(patched_archive_dir, 0, ZERO_HASH)
        result = ArchiveLineageValidator.verify_archive_lineage()
        assert result["valid"] is True
        assert result["archives_verified"] == 1
        assert result["error"] is None


# ============================================================
# 3. Chaîne de 3 archives valides
# ============================================================

class TestChainOfArchives:
    def test_three_valid_archives_chain(self, patched_archive_dir):
        r0 = _make_valid_archive(patched_archive_dir, 0, ZERO_HASH)
        r1 = _make_valid_archive(patched_archive_dir, 1, r0)
        _make_valid_archive(patched_archive_dir, 2, r1)
        result = ArchiveLineageValidator.verify_archive_lineage()
        assert result["valid"] is True
        assert result["archives_verified"] == 3


# ============================================================
# 4. Incohérence structurelle
# ============================================================

class TestStructuralMismatch:
    def test_more_meta_than_jsonl(self, patched_archive_dir):
        # 2 metas, 1 jsonl
        (patched_archive_dir / "ledger_0000.meta.json").write_text("{}", encoding="utf-8")
        (patched_archive_dir / "ledger_0001.meta.json").write_text("{}", encoding="utf-8")
        (patched_archive_dir / "ledger_0000.jsonl").write_text("x\n", encoding="utf-8")
        result = ArchiveLineageValidator.verify_archive_lineage()
        assert result["valid"] is False
        assert "Incohérence structurelle" in result["error"]

    def test_more_jsonl_than_meta(self, patched_archive_dir):
        (patched_archive_dir / "ledger_0000.jsonl").write_text("x\n", encoding="utf-8")
        (patched_archive_dir / "ledger_0001.jsonl").write_text("x\n", encoding="utf-8")
        (patched_archive_dir / "ledger_0000.meta.json").write_text("{}", encoding="utf-8")
        result = ArchiveLineageValidator.verify_archive_lineage()
        assert result["valid"] is False
        assert "Incohérence structurelle" in result["error"]


# ============================================================
# 5. Erreurs de lecture / corruption JSON
# ============================================================

class TestReadErrors:
    def test_invalid_meta_json(self, patched_archive_dir):
        (patched_archive_dir / "ledger_0000.meta.json").write_text(
            "{not valid json", encoding="utf-8"
        )
        (patched_archive_dir / "ledger_0000.jsonl").write_text("x\n", encoding="utf-8")
        result = ArchiveLineageValidator.verify_archive_lineage()
        assert result["valid"] is False
        assert "Erreur de lecture" in result["error"]

    def test_empty_jsonl(self, patched_archive_dir):
        (patched_archive_dir / "ledger_0000.meta.json").write_text("{}", encoding="utf-8")
        (patched_archive_dir / "ledger_0000.jsonl").write_text("", encoding="utf-8")
        result = ArchiveLineageValidator.verify_archive_lineage()
        assert result["valid"] is False
        assert "Archive vide" in result["error"]


# ============================================================
# 6. Rupture de lignée (previous_root_hash)
# ============================================================

class TestLineageBreak:
    def test_bad_previous_root_first_archive(self, patched_archive_dir):
        wrong_prev = "1" * 64
        _make_valid_archive(patched_archive_dir, 0, wrong_prev)
        result = ArchiveLineageValidator.verify_archive_lineage()
        assert result["valid"] is False
        assert "RUPTURE DE LIGNÉE" in result["error"]

    def test_bad_previous_root_second_archive(self, patched_archive_dir):
        r0 = _make_valid_archive(patched_archive_dir, 0, ZERO_HASH)
        # 2e archive avec mauvais prev
        _make_valid_archive(patched_archive_dir, 1, "9" * 64)
        result = ArchiveLineageValidator.verify_archive_lineage()
        assert result["valid"] is False
        assert "RUPTURE DE LIGNÉE" in result["error"]


# ============================================================
# 7. Altération content_hash
# ============================================================

class TestContentHashTampering:
    def test_content_hash_mismatch(self, patched_archive_dir):
        _make_valid_archive(patched_archive_dir, 0, ZERO_HASH)
        # Corrompre le jsonl
        jsonl = patched_archive_dir / "ledger_0000.jsonl"
        jsonl.write_text(jsonl.read_text() + '{"tampered": true}\n', encoding="utf-8")
        result = ArchiveLineageValidator.verify_archive_lineage()
        assert result["valid"] is False
        assert "ALTÉRATION HISTORIQUE" in result["error"]


# ============================================================
# 8. Altération archive_root_hash
# ============================================================

class TestRootHashTampering:
    def test_root_hash_mismatch(self, patched_archive_dir):
        _make_valid_archive(patched_archive_dir, 0, ZERO_HASH)
        # Modifier le meta pour un root_hash faux
        meta_path = patched_archive_dir / "ledger_0000.meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["archive_root_hash"] = "f" * 64
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        result = ArchiveLineageValidator.verify_archive_lineage()
        assert result["valid"] is False
        assert "ROOT HASH CORROMPU" in result["error"]


# ============================================================
# 9. Singleton
# ============================================================

class TestSingleton:
    def test_singleton_exists(self):
        assert av_mod.archive_validator is not None
        assert isinstance(av_mod.archive_validator, ArchiveLineageValidator)
